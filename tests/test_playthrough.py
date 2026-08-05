"""Play whole games headlessly

This is the catch all: it drives a real two player game through its phases with
randomised input and fails on anything that raises, including the errors twisted
only writes to its log.
"""

import random

import pygame
import pytest
from pygame.locals import (
    KEYDOWN,
    KEYUP,
    KMOD_LALT,
    NOEVENT,
    K_a,
    K_d,
    K_DOWN,
    K_e,
    K_f,
    K_LEFT,
    K_q,
    K_RETURN,
    K_RIGHT,
    K_RSHIFT,
    K_s,
    K_UP,
)
from twisted.internet import reactor

from castle_combat import menu
from castle_combat.map import ConquerMap, RiverMap2p
from castle_combat.state import MainState, State

# the movement and action keys of the two local players
KEYS = [
    K_UP,
    K_DOWN,
    K_LEFT,
    K_RIGHT,
    K_RETURN,
    K_RSHIFT,
    K_e,
    K_d,
    K_s,
    K_f,
    K_a,
    K_q,
]


def play(map_class, frames, advance, toggle_fullscreen_every=None):
    """Run a two player game for a number of frames, return the phases seen"""
    from castle_combat.game import game
    from castle_combat.server import Server

    MainState()
    menu.MenuState()
    server = Server(map_class(dict(difficulty="medium")), 2)
    server.run(2, 0)

    keyboard = random.Random(7)
    phases = []
    try:
        for frame in range(frames):
            for _ in range(3):
                key = keyboard.choice(KEYS)
                pygame.event.post(
                    pygame.event.Event(KEYDOWN, key=key, mod=0, unicode="")
                )
                pygame.event.post(pygame.event.Event(KEYUP, key=key, mod=0))
            if (
                toggle_fullscreen_every
                and frame % toggle_fullscreen_every == toggle_fullscreen_every - 1
            ):
                pygame.event.post(
                    pygame.event.Event(KEYDOWN, key=K_RETURN, mod=KMOD_LALT, unicode="")
                )

            event = pygame.event.poll()
            while event.type != NOEVENT:
                State.stack[-1].on_event(event)
                event = pygame.event.poll()
            State.stack[-1].handle()
            # the game leans on callLater, which needs the reactor serviced
            reactor.iterate(0)
            advance()

            name = getattr(game.phase, "phase_name", None)
            if name and (not phases or phases[-1] != name):
                phases.append(name)
    finally:
        server.listening_port.stopListening()
        for _ in range(5):
            reactor.iterate(0)
    return phases


@pytest.mark.parametrize("map_class", [ConquerMap, RiverMap2p])
def test_a_game_runs_through_several_rounds(fake_time, twisted_errors, map_class):
    phases = play(map_class, 1200, fake_time)

    assert twisted_errors == []
    assert "select" in phases
    assert phases.count("build") >= 2
    assert phases.count("place") >= 3
    assert phases.count("battle") >= 3


def test_fullscreen_can_be_toggled_during_a_game(fake_time, twisted_errors):
    phases = play(ConquerMap, 600, fake_time, toggle_fullscreen_every=150)

    assert twisted_errors == []
    assert "battle" in phases
