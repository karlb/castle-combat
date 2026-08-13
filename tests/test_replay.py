"""Replay a host's broadcasts and check the client lands where the host is

Nothing else in the suite runs the receiving half. test_playthrough.py plays
whole games with no client attached, so no broadcast is ever acted on, and
test_network.py attaches a client that never plays a phase. Every fault found
in this code so far has been in that gap.

A client is a Game with no server whose objects apply the raw implementation of
each command rather than forwarding it, which is exactly what observe_ is bound
to. Game is a Borg, so the two games cannot exist at once: the host plays first,
its broadcasts are recorded, and the replay runs afterwards from a clean slate.
"""

import random

import pytest
from twisted.internet import defer, reactor
from twisted.spread import jelly

from castle_combat import common
from castle_combat.map import ConquerMap, RiverMap2p
from test_playthrough import play
from test_replication import replicated_state

PHASES = ("build", "place", "battle", "select")


def key_of(owner):
    """Name the object a broadcast came from, so the replay can find its twin"""
    name = type(owner).__name__
    for phase in PHASES:
        if name.lower().startswith(phase):
            return (phase, owner.player.player_id)
    raise AssertionError("unexpected broadcaster %s" % name)


class Recorder:
    """Stands in for a connected client's reference to one server object"""

    def __init__(self, owner, wire):
        self.owner = owner
        self.wire = wire

    def callRemote(self, name, *args, **kwargs):
        # delegate_and_call() forwards keywords, so dropping them here would
        # quietly replay something other than what a client would receive
        assert not kwargs, "%s was sent keywords this does not replay" % name
        # a real client is reached through pb, so anything that would not
        # survive the trip has to fail here rather than be replayed intact.
        # This is the half of the wire test_replication.py cannot see: it
        # watches Server.call, and these go out through the observers.
        assert jelly.unjelly(jelly.jelly(args)) == args, (
            "%s%r does not survive serialisation" % (name, args)
        )
        self.wire.append((key_of(self.owner), name, args))
        return defer.succeed(None)


@pytest.fixture
def wire(monkeypatch):
    """Every command the host would put on the wire, in the order it sends it"""
    from castle_combat.network import ServerObject
    from castle_combat.server import Server

    sent = []

    original_init = ServerObject.__init__

    def observed_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.observers.append(Recorder(self, sent))

    original_call = Server.call

    def recorded_call(self, command, *args):
        result = original_call(self, command, *args)
        # None means it was rejected and nothing went out
        if result is not None:
            sent.append((("game", None), command, args))
        return result

    monkeypatch.setattr(ServerObject, "__init__", observed_init)
    monkeypatch.setattr(Server, "call", recorded_call)
    return sent


def reset_the_world():
    """What conftest's clean_state does, between the two games of one test"""
    from castle_combat.field import Grunt
    from castle_combat.server import Server
    from castle_combat.state import State

    for call in reactor.getDelayedCalls():
        call.cancel()
    common.Borg._shared_state.clear()
    del State.stack[:]
    Server.clients = []
    Grunt.instances = []
    common.screen_updates = []
    common.screen_undraws = []


def apply_to(game, key, name, args):
    kind, player_id = key
    if kind == "game":
        target, method = game, "remote_" + name
    else:
        target = getattr(game.players[player_id], kind + "_player")
        # local_ is the untouched implementation, which is what a client's
        # observe_ is bound to; the bare name would forward instead of apply
        method = "local_" + name
    try:
        getattr(target, method)(*args)
    except common.ActionNotPossible:
        # the host sent it, so the client must not be the one refusing it
        raise AssertionError("the client refused %s%r" % (name, args))


@pytest.mark.parametrize("map_class", [ConquerMap, RiverMap2p])
def test_a_client_replaying_the_broadcasts_matches_the_host(fake_time, wire, map_class):
    from castle_combat import menu
    from castle_combat.game import Game
    from castle_combat.player import PlayerCacheable
    from castle_combat.state import MainState, State

    random.seed(1)
    play(map_class, 900, fake_time)
    host = replicated_state(Game(players=None))
    broadcasts = list(wire)
    assert broadcasts, "the host sent nothing, so this proves nothing"

    reset_the_world()

    # the same seed, so setup() puts the castles where the host had them
    random.seed(1)
    MainState()
    menu.MenuState()
    players = [PlayerCacheable(i) for i in range(2)]
    client = Game(players=players, server=None)
    map = map_class(dict(difficulty="medium"))
    map.setup()
    client.set_map(map)
    client.run_callback = lambda: None
    for key, name, args in broadcasts:
        apply_to(client, key, name, args)
        # Map.apply() defers its houses, and the host's ran between commands
        reactor.iterate(0)
        # next_phase only pops the phase; GameState.handle() is what builds the
        # next one, and on the host that happens in the main loop
        State.stack[-1].handle()
        fake_time()

    assert replicated_state(client) == host
