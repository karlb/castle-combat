"""Every map has to build a playable field for every player count it allows"""

import pytest

from castle_combat.field import Field, Grunt
from castle_combat.map import GruntAssault, RiverMap, maps

COMBINATIONS = [(map_class, n) for map_class in maps for n in map_class.allowed_players]
IDS = ["%s-%dp" % (map_class.__name__, n) for map_class, n in COMBINATIONS]


@pytest.mark.parametrize("map_class, player_count", COMBINATIONS, ids=IDS)
def test_map_sets_up(make_game, map_class, player_count):
    game, map = make_game(map_class, player_count)
    field = game.field

    assert map.castles, "no castles were placed"
    # a castle covers 2x2 fields
    assert (field.array == Field.CASTLE).sum() == 4 * len(map.castles)

    for castle in map.castles:
        for i in (0, 1):
            assert 0 <= castle.pos[i] < common_field_size(i)


@pytest.mark.parametrize("map_class, player_count", COMBINATIONS, ids=IDS)
def test_field_keeps_its_negative_markers(make_game, map_class, player_count):
    """EMPTY is -1, so an unsigned field would silently store it as 255"""
    game, _ = make_game(map_class, player_count)

    assert game.field.array.dtype.kind == "i"
    assert (game.field.array == Field.EMPTY).sum() > 0
    assert game.field.array.min() < 0


@pytest.mark.parametrize(
    "map_class, player_count",
    [c for c in COMBINATIONS if issubclass(c[0], RiverMap)],
    ids=[i for i, c in zip(IDS, COMBINATIONS) if issubclass(c[0], RiverMap)],
)
def test_river_maps_have_a_river(make_game, map_class, player_count):
    game, _ = make_game(map_class, player_count)

    assert (game.field.array == Field.RIVER).sum() > 0


def test_grunt_assault_places_grunts(make_game):
    game, map = make_game(GruntAssault, 1)

    assert Grunt.instances
    assert (game.field.array == Field.GRUNT).sum() == len(Grunt.instances)


def common_field_size(i):
    from castle_combat import common

    return common.field_size[i]
