"""Repainting a newly secured area has to leave the same picture as a redraw"""

import numpy as np
import pygame

from castle_combat import common
from castle_combat.map import GruntAssault


def wall_around_castle(field, castle, player):
    """Enclose the 2x2 castle in a ring of the player's walls"""
    left, top = castle.pos
    for x in range(left - 1, left + 3):
        for y in range(top - 1, top + 3):
            if x in (left - 1, left + 2) or y in (top - 1, top + 2):
                field.array[x, y] = player.player_id


def backbuffer_pixels():
    return pygame.surfarray.array3d(common.backbuffer)


def test_securing_an_area_keeps_the_whole_castle_visible(make_game):
    """The castle sprite covers four blocks, but is drawn from the first one"""
    game, map = make_game(GruntAssault, 1)
    field, player = game.field, game.players[0]
    castle = map.castles[0]
    wall_around_castle(field, castle, player)

    common.backbuffer = pygame.Surface(common.screen.get_size())
    field.draw_backbuffer()
    field.look_for_secured_areas(player)
    secured = backbuffer_pixels()

    field.draw_backbuffer()
    assert np.array_equal(secured, backbuffer_pixels())
