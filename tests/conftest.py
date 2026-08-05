import os

# must happen before pygame initialises a video or audio device
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

import pygame
import pytest
from twisted.internet import reactor
from twisted.python import log

from castle_combat import common, config

# how much game time one simulated frame is worth
FRAME_MS = 200


# Modules like widget and field load and convert images while they are being
# imported, which needs a display. Test modules are imported during collection,
# before any fixture runs, so this cannot wait for one.
#
# config.load() is deliberately not used: it reads, and on the way out writes,
# the player's real ~/.castle-combat.config.
config.conf = config.Config()
config.PlayerConfig.instances = []
for _player_id in range(4):
    config.PlayerConfig(_player_id)

pygame.init()
common.init()


@pytest.fixture(scope="session", autouse=True)
def shut_down_pygame():
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def clean_state():
    """Reset the game's global state between tests"""
    from castle_combat.field import Grunt
    from castle_combat.server import Server
    from castle_combat.state import State

    def reset():
        for call in reactor.getDelayedCalls():
            call.cancel()
        # Game is a Borg, so every instance shares this one dict
        common.Borg._shared_state.clear()
        del State.stack[:]
        Server.clients = []
        Grunt.instances = []
        common.screen_updates = []
        common.screen_undraws = []
        common.backbuffer = None

    reset()
    common.set_fullscreen(False)
    random.seed(1)
    yield
    reset()


@pytest.fixture
def twisted_errors():
    """Collect errors twisted logs instead of raising, e.g. from callLater"""
    errors = []

    def observer(event):
        if event.get("isError"):
            errors.append(log.textFromEventDict(event))

    log.addObserver(observer)
    yield errors
    log.removeObserver(observer)


@pytest.fixture
def fake_time(monkeypatch):
    """Advance game time a fixed step per frame instead of using wall time

    Phases end after a number of seconds measured with pygame.time.Clock, and
    AnnouncePhase waits for pygame.time.get_ticks() to move on. Faking both
    keeps a full playthrough fast and reproducible. pygame.time.Clock is an
    immutable type, so the module attribute is replaced rather than patched.
    """
    ticks = [0]

    class FakeClock:
        def tick(self, *args):
            return FRAME_MS

    monkeypatch.setattr(pygame.time, "Clock", FakeClock)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks[0])

    def advance():
        ticks[0] += FRAME_MS

    return advance


@pytest.fixture
def make_game():
    """Set up a game and its field without starting a server

    Server would bind a TCP port, which the tests that only need a playable
    field can do without.
    """

    def _make_game(map_class, player_count, options=None):
        from castle_combat import game as game_module
        from castle_combat.player import PlayerCacheable

        players = [PlayerCacheable(i) for i in range(player_count)]
        game = game_module.Game(players=players, server=None)
        map = map_class(options or dict(difficulty="medium"))
        map.setup()
        game.set_map(map)
        game.field.init()
        # Map.apply() defers adding the houses
        for _ in range(5):
            reactor.iterate(0)
        return game, map

    return _make_game
