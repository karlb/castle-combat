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
