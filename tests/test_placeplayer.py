"""The place cursor has to keep the whole cannon on the field

A big cannon covers 3x3 blocks where a small one covers 2x2, so a cursor that
was flush with an edge is one block over once the type changes. draw_cursor()
then indexes past field.array, and because Phase.handle() is called straight
from stateLoop() the IndexError escapes the main loop and the game stops
repainting instead of raising anything a player could report.
"""

import pytest

from castle_combat import common
from castle_combat.cannon import Cannon
from castle_combat.map import ConquerMap


@pytest.fixture
def place_player(make_game):
    """A place cursor with enough cannons to afford the big one"""
    game, _map = make_game(ConquerMap, 2)
    player = game.players[0].place_player
    player.selected_type = 0
    player.new_cannons = Cannon.price[1]
    return player


def test_switching_to_a_big_cannon_at_the_edge_keeps_it_on_the_field(place_player):
    # as far right as a small cannon may sit
    place_player.pos = [int(common.field_size[0]) - 2, 5]

    place_player.change_type()

    assert place_player.selected_type == 1
    assert place_player.pos == [int(common.field_size[0]) - 3, 5]
    # the crash was here, not in the assertion above
    place_player.draw_cursor()


def test_switching_at_the_bottom_edge_keeps_it_on_the_field(place_player):
    place_player.pos = [5, int(common.field_size[1]) - 2]

    place_player.change_type()

    assert place_player.pos == [5, int(common.field_size[1]) - 3]
    place_player.draw_cursor()


def test_a_big_cannon_cannot_be_walked_off_the_field(place_player):
    place_player.selected_type = 1
    place_player.pos = [int(common.field_size[0]) - 3, 5]

    with pytest.raises(common.ActionNotPossible):
        place_player.local_move((1, 0))

    assert place_player.pos == [int(common.field_size[0]) - 3, 5]


def test_a_small_cannon_still_reaches_the_edge(place_player):
    """The bound depends on the type, so it must not tighten for both"""
    place_player.pos = [int(common.field_size[0]) - 3, 5]

    place_player.local_move((1, 0))

    assert place_player.pos == [int(common.field_size[0]) - 2, 5]
