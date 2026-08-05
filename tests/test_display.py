"""Fullscreen has to be switchable while the game runs, not only at startup"""

import pygame
from pygame.locals import KEYDOWN, KMOD_LALT, K_RETURN

from castle_combat import common, config, menu
from castle_combat.state import MainState

ALT_ENTER = pygame.event.Event(KEYDOWN, key=K_RETURN, mod=KMOD_LALT, unicode="")


def test_fullscreen_keeps_the_games_resolution():
    common.set_fullscreen(True)

    assert pygame.display.is_fullscreen()
    assert common.screen.get_size() == (800, 600)


def test_options_toggle_applies_without_a_restart():
    MainState()
    menu.MenuState()
    state = menu.ConfigState()
    assert not pygame.display.is_fullscreen()

    state.fullscreen.change(-1)  # choices run On, Off

    assert state.fullscreen.value == "On"
    assert pygame.display.is_fullscreen()
    assert config.conf.fullscreen

    state.fullscreen.change(1)

    assert not pygame.display.is_fullscreen()
    assert not config.conf.fullscreen


def test_leaving_the_options_syncs_the_display():
    """alt+enter inside the options menu leaves the spin box out of date"""
    MainState()
    menu.MenuState()
    state = menu.ConfigState()
    state.fullscreen.change(-1)
    assert pygame.display.is_fullscreen()

    common.toggle_fullscreen()  # as if alt+enter was pressed
    assert not pygame.display.is_fullscreen()

    state.quit()

    assert pygame.display.is_fullscreen(), "the spin box still said On"


def test_alt_enter_toggles_both_ways():
    main = MainState()
    menu.MenuState()

    main.handle_keypress(ALT_ENTER)

    assert pygame.display.is_fullscreen()
    assert config.conf.fullscreen

    main.handle_keypress(ALT_ENTER)

    assert not pygame.display.is_fullscreen()
    assert not config.conf.fullscreen


def test_redraw_restores_the_screen_from_the_backbuffer():
    MainState()
    menu.MenuState()  # draws the menu background into the backbuffer
    common.screen.fill((255, 0, 255))

    common.redraw()

    assert common.screen.get_at((10, 10)) == common.backbuffer.get_at((10, 10))
    assert common.screen_updates == []
