"""The game has to keep working when installed, not just from a checkout"""

import importlib
import os

import pytest

from castle_combat import common

MODULES = [
    "ai",
    "battleplayer",
    "buildplayer",
    "cannon",
    "client",
    "common",
    "config",
    "field",
    "game",
    "gamephases",
    "main",
    "map",
    "menu",
    "network",
    "placeplayer",
    "player",
    "selectplayer",
    "server",
    "sound",
    "state",
    "widget",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module("castle_combat." + name)


def test_data_files_are_found_next_to_the_code():
    """The data path must not depend on the current working directory"""
    package_dir = os.path.dirname(os.path.abspath(common.__file__))
    assert common.data_path == os.path.join(package_dir, "data")

    for name in ["DefaultFancy.ttf", "gfx", "sound", os.path.join("doc", "rules.html")]:
        assert os.path.exists(os.path.join(common.data_path, name)), name


def test_images_load():
    assert common.load_image("castle.png").get_size() > (0, 0)


def test_colorkey_is_taken_from_the_top_left_pixel():
    """The cannon sprites ask for this by passing -1 positionally"""
    image = common.load_image("cannon0001.png", -1)

    assert image.get_colorkey()[:3] == tuple(image.get_at((0, 0)))[:3]
