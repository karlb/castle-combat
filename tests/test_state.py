"""The state stack has to react to events aimed at the application itself"""

import pygame
from pygame.locals import QUIT
from twisted.internet import reactor

from castle_combat import menu
from castle_combat.state import MainState, State


def test_closing_the_window_quits(monkeypatch):
    stopped = []
    monkeypatch.setattr(reactor, "stop", lambda: stopped.append(True))
    MainState()
    menu.MenuState()  # the close button also has to work mid-game

    State.on_event(pygame.event.Event(QUIT))

    assert stopped
