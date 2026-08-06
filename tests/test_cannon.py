"""Cannons belong to whoever's walls enclose them, not to whoever built them"""

import pygame

from castle_combat import common
from castle_combat.cannon import Cannon
from castle_combat.field import Field
from castle_combat.map import RiverMap2p


def start_game(make_game):
    game, _ = make_game(RiverMap2p, 2)
    # this map brings its own background, so nothing has created a backbuffer
    common.backbuffer = pygame.Surface(common.screen.get_size())
    return game


def enclose(field, player, left, top, size):
    """Give the player an empty, fully walled in size x size area"""
    for x in range(left - 1, left + size + 1):
        for y in range(top - 1, top + size + 1):
            on_wall = x in (left - 1, left + size) or y in (top - 1, top + size)
            field.array[x, y] = player.player_id if on_wall else Field.EMPTY
    field.look_for_secured_areas(player)


def hand_out_cannons(game):
    """The part of the build phase that decides who owns which cannon"""
    for player in game.players:
        game.field.look_for_secured_areas(player)
    for cannon in game.cannons:
        cannon.update_owner()


def test_a_cannon_outside_its_owners_walls_goes_idle(make_game):
    game = start_game(make_game)
    enclose(game.field, game.players[0], 4, 4, 4)
    cannon = Cannon((4, 4), game.players[0])
    assert cannon.is_active

    game.field.array[3, 4] = Field.EMPTY  # tear a hole into the wall
    hand_out_cannons(game)

    assert cannon.player is None
    assert not cannon.is_active


def test_an_enemy_walling_a_cannon_in_takes_it_over(make_game):
    game = start_game(make_game)
    red, green = game.players
    enclose(game.field, red, 4, 4, 4)
    cannon = Cannon((4, 4), red)

    enclose(game.field, green, 4, 4, 4)
    hand_out_cannons(game)

    assert cannon.player is green
    assert cannon.is_active
