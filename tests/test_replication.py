"""What the host replicates has to match what it changed

Server.call() swallows ActionNotPossible so illegal moves stay off the wire,
which makes it a contract for every remote_ method: raise only if nothing
changed. A method that mutates and then rejects leaves the clients behind for
good, because nothing resends the state it altered on the way out.
"""

import pytest
from twisted.spread import jelly

from castle_combat import common
from castle_combat.cannon import Cannon
from castle_combat.field import Field, Grunt
from castle_combat.map import ConquerMap, RiverMap2p


def empty_block(game):
    """A field position with nothing on it"""
    for x in range(common.field_size[0]):
        for y in range(common.field_size[1]):
            if game.field[(x, y)] == Field.EMPTY:
                return (x, y)
    raise AssertionError("the map left no empty block")


def build_cannon(game, player):
    """A cannon on secured, empty ground, as the place phase would leave it"""
    for x in range(common.field_size[0] - 2):
        for y in range(common.field_size[1] - 2):
            blocks = [game.field[x + i][y + j] for i in (0, 1) for j in (0, 1)]
            if all(block == Field.EMPTY for block in blocks):
                for i in (0, 1):
                    for j in (0, 1):
                        player.secured[x + i][y + j] = 1
                # Cannon.__init__ puts itself in game.cannons
                return Cannon((x, y), player, 0)
    raise AssertionError("the map left no room for a cannon")


def test_a_missed_shot_still_reports_that_it_freed_the_cannon(make_game):
    """remote_hit used to clear in_use and then raise ActionIrrelevant

    Server.call() would swallow that and send nothing, so the client kept the
    cannon busy for the rest of the game. Misses far outnumber hits, so a
    client soon believed a player had no cannon left to fire.
    """
    game, _map = make_game(ConquerMap, 2)
    cannon = build_cannon(game, game.players[0])
    cannon.in_use = True

    game.remote_hit(empty_block(game), cannon.id)

    assert cannon.in_use is False


def test_a_grunt_that_hits_nothing_changes_nothing(make_game):
    game, _map = make_game(ConquerMap, 2)

    with pytest.raises(common.ActionIrrelevant):
        game.remote_hit(empty_block(game))


def test_a_rejected_diagonal_leaves_the_place_cursor_alone(make_game):
    """One legal component used to be written before the other was checked

    local_move is the unwrapped implementation; the networkified move() would
    catch the rejection, which is the swallow this test is about.
    """
    game, _map = make_game(ConquerMap, 2)
    place_player = game.players[0].place_player
    # up against the top edge, so moving right is fine but up is not, and the
    # legal component is the one the loop reaches first
    place_player.pos = [5, 0]

    with pytest.raises(common.ActionNotPossible):
        place_player.local_move((1, -1))

    assert place_player.pos == [5, 0]


def replicated_state(game):
    """Everything a client mirrors from the host's broadcasts

    Plain ints rather than repr(), because numpy changed how its scalars
    repr() in 2.0 and pyproject.toml deliberately allows both majors.
    """
    return (
        game.field.array.tobytes(),
        tuple(player.secured.tobytes() for player in game.players),
        tuple(player.alive for player in game.players),
        tuple(
            (cannon.id, tuple(int(c) for c in cannon.pos), cannon.in_use)
            for cannon in sorted(game.cannons, key=lambda cannon: cannon.id)
        ),
        tuple(
            (grunt.id, tuple(int(c) for c in grunt.pos), int(grunt.direction))
            for grunt in sorted(Grunt.instances, key=lambda grunt: grunt.id)
        ),
        tuple(
            tuple(int(c) for c in getattr(player.phase_player, "pos", ()))
            for player in game.players
            if getattr(player, "phase_player", None)
        ),
    )


class Audit:
    """Watches every command a running game replicates"""

    def __init__(self):
        self.mutated_but_silent = []
        self.mangled_on_the_wire = []


@pytest.fixture
def audit(monkeypatch):
    """Check both halves of the contract on every Server.call() of a game"""
    from castle_combat.server import Server

    report = Audit()
    original = Server.call

    def audited(self, command, *args):
        before = replicated_state(self.game)
        result = original(self, command, *args)
        if result is None:
            # rejected, so nothing went out: the game must be as it was
            if replicated_state(self.game) != before:
                report.mutated_but_silent.append(command)
        elif jelly.unjelly(jelly.jelly(args)) != args:
            # pb turns a numpy scalar into a plain zero rather than refusing it
            report.mangled_on_the_wire.append((command, args))
        return result

    monkeypatch.setattr(Server, "call", audited)
    return report


@pytest.mark.parametrize("map_class", [ConquerMap, RiverMap2p])
def test_a_whole_game_replicates_everything_it_changes(fake_time, audit, map_class):
    """The generic version of the two regressions above

    test_playthrough.py drives whole games but never connects a client, and
    test_network.py connects a client but never plays a phase. Both faults
    lived in that gap, so this walks a real game and checks each command
    against the contract as it goes.
    """
    from test_playthrough import play

    play(map_class, 1200, fake_time)

    assert audit.mutated_but_silent == []
    assert audit.mangled_on_the_wire == []
