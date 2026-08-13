"""Phases end on the host's clock, not on each machine's own

Every peer runs its own Phase with its own pygame.time.Clock, started when the
phase began there. Only the host may act on that clock running out: a client
that decides for itself takes the branch that asks for the next phase, which on
a client does nothing at all, and so skips the drawing in the other branch for
as long as the disagreement lasts.
"""

import pytest

from castle_combat import menu
from castle_combat.config import PlayerConfig
from castle_combat.gamephases import BuildPhase
from castle_combat.map import ConquerMap
from castle_combat.state import MainState


class RecordingServer:
    """Stands in for the Server, which would bind a port"""

    def __init__(self):
        self.commands = []

    def call(self, command, *args):
        self.commands.append(command)


@pytest.fixture
def build_phase(make_game):
    """A build phase mid-play, with both players holding some ground"""
    game, _map = make_game(ConquerMap, 2)
    MainState()
    # the menu leaves a backbuffer behind, which the phase draws on
    menu.MenuState()
    for index, player in enumerate(game.players):
        for x in range(5 + 10 * index, 8 + 10 * index):
            for y in range(5, 8):
                player.secured[x][y] = 1
    PlayerConfig.assign()
    phase = BuildPhase()
    game.phase = phase
    return game, phase


def drawing_recorder(game):
    drawn = []
    for player in game.players:
        player.draw_cursor = lambda *args: drawn.append(1)
    return drawn


def test_a_client_keeps_drawing_after_its_own_timer_runs_out(build_phase):
    game, phase = build_phase
    game.server = None  # this peer joined, it does not host
    drawn = drawing_recorder(game)
    phase.time_left = 0

    phase.handle()

    assert drawn


def test_the_host_ends_the_phase_when_its_timer_runs_out(build_phase):
    game, phase = build_phase
    game.server = RecordingServer()
    drawn = drawing_recorder(game)
    phase.time_left = 0

    phase.handle()

    assert game.server.commands == ["next_phase"]
    assert not drawn


def test_the_host_keeps_drawing_while_the_timer_runs(build_phase):
    game, phase = build_phase
    game.server = RecordingServer()
    drawn = drawing_recorder(game)
    phase.time_left = 5

    phase.handle()

    assert game.server.commands == []
    assert drawn


@pytest.fixture
def announcement(build_phase):
    """The 'build phase begins' screen, waiting to be acknowledged"""
    from castle_combat.gamephases import AnnouncePhase, BuildPhase

    game, phase = build_phase
    phase.quit()
    announce = AnnouncePhase(BuildPhase)
    game.phase = announce
    return game, announce


def test_the_host_moves_on_from_an_announcement_nobody_acknowledges(announcement):
    game, announce = announcement
    game.server = RecordingServer()
    announce.start_time -= announce.give_up_waiting + 1

    announce.handle()

    assert game.server.commands == ["next_phase"]


def test_the_host_waits_a_while_first(announcement):
    game, announce = announcement
    game.server = RecordingServer()

    announce.handle()

    assert game.server.commands == []


def test_a_client_never_moves_on_by_itself(announcement):
    from castle_combat.state import State

    game, announce = announcement
    game.server = None
    announce.start_time -= announce.give_up_waiting * 10

    announce.handle()

    # however long it has been, a client waits for the host to say so
    assert announce in State.stack


def test_a_client_does_not_confirm_the_castles_the_host_confirms(build_phase):
    """SelectPhase.cleanup() used to crash on every client that had a straggler

    networkify() installs the remote_ names on the server classes only, so a
    client's copy has no remote_confirm_select at all. The host broadcasts its
    confirmations before next_phase, which normally leaves the clients with
    nobody left to confirm -- but SelectPlayer.init() resets finished to False
    when the phase starts there, so a confirmation that arrives before the
    client has built its SelectPhase is wiped and never sent again. That client
    then reaches this and dies.
    """
    from castle_combat.gamephases import SelectPhase
    from castle_combat.selectplayer import SelectPlayerClient

    game, phase = build_phase
    phase.quit()
    game.server = None
    select_phase = SelectPhase()
    for player in game.players:
        player.select_player = SelectPlayerClient()
        player.select_player.finished = False

    select_phase.cleanup()  # the host will say who confirmed

    assert not any(player.select_player.finished for player in game.players)
