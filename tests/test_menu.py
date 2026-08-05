import pytest

from castle_combat import common, menu
from castle_combat.state import MainState


@pytest.fixture
def main_menu():
    MainState()
    return menu.MenuState()


def test_new_game_state_opens(main_menu):
    """Opening this menu used to raise numpy's AxisError from min(a, b)"""
    state = menu.NewGameState()

    assert state.total_players.value >= 1
    assert state.local_players.value <= state.total_players.value
    assert state.map.choices


def test_lowering_the_player_count_lowers_the_local_players(main_menu):
    state = menu.NewGameState()
    while state.total_players.value < 4:
        state.total_players.change(-1)  # choices run 4, 3, 2, 1
    state.local_players.value = 4

    state.total_players.change(1)

    assert state.total_players.value == 3
    assert state.local_players.value == 3


def test_widgets_stay_on_the_background_in_fullscreen():
    """Widget positions come from screen.get_size() at construction time

    Without a scaled display, fullscreen hands back a desktop sized surface and
    the edge anchored buttons end up far outside the 800x600 artwork.
    """
    common.set_fullscreen(True)
    MainState()
    state = menu.MenuState()

    assert common.screen.get_size() == (800, 600)
    assert state.widgets
    for widget in state.widgets:
        width, height = widget.normal_surface.get_size()
        assert 0 <= widget.pos[0] <= 800 - width
        assert 0 <= widget.pos[1] <= 600 - height
