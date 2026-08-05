"""numpy 2 changed how a python int combines with a small integer dtype"""

import numpy as np
import pygame
import pytest

from castle_combat import common


def reference_colorize(pixels, color):
    """What the original per-pixel loop computed before numpy 2

    Kept as plain python arithmetic so it cannot share a bug with the
    implementation under test.
    """
    result = np.empty_like(pixels)
    for x in range(pixels.shape[0]):
        for y in range(pixels.shape[1]):
            for channel in (0, 1, 2):
                result[x, y, channel] = (
                    int(pixels[x, y, channel]) * int(color[channel]) // 255
                )
    return result


@pytest.mark.parametrize(
    "color",
    [
        (255, 0, 0),
        (100, 120, 20),
        (1, 2, 3),
        # players carry an alpha component, which pixels3d() does not cover
        (100, 120, 20, 255),
        pygame.Color(128, 64, 255, 200),
    ],
)
def test_colorize_matches_reference(color):
    pixels = np.random.default_rng(0).integers(0, 256, (16, 16, 3), dtype=np.uint8)
    surface = pygame.Surface((16, 16))
    view = pygame.surfarray.pixels3d(surface)
    view[:] = pixels
    del view

    result = pygame.surfarray.pixels3d(common.colorize(surface, color)).copy()

    assert np.array_equal(result, reference_colorize(pixels, color))


def test_colorize_does_not_wrap_around():
    """A bright pixel times a bright colour must stay bright"""
    surface = pygame.Surface((1, 1))
    view = pygame.surfarray.pixels3d(surface)
    view[:] = 200
    del view

    result = pygame.surfarray.pixels3d(common.colorize(surface, (255, 255, 255)))

    assert tuple(result[0][0]) == (200, 200, 200)


@pytest.mark.parametrize(
    "value, expected", [(np.int64(500), 39), (np.int64(-5), 1), (np.int64(7), 7)]
)
def test_bound_clamps_numpy_scalars(value, expected):
    """numpy's min/max would read the second argument as an axis"""
    assert common.bound(value, 1, common.field_size[0] - 1) == expected


def test_in_bounds_keeps_positions_on_the_field():
    assert common.in_bounds(np.subtract((0, 0), 3)) == [1, 1]
    assert common.in_bounds(np.add(common.field_size, 3)) == [
        common.field_size[0] - 1,
        common.field_size[1] - 1,
    ]
    assert common.is_in_bounds((5, 5))
    assert not common.is_in_bounds((0, 0))
