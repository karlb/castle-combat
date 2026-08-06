"""Settings survive a restart, and a bad file does not stop the game starting"""

import pytest

from castle_combat import config


@pytest.fixture
def config_home(tmp_path, monkeypatch):
    """Put the config file somewhere disposable and restore the globals after"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    saved = (config.conf, config.PlayerConfig.instances)
    yield tmp_path
    (config.conf, config.PlayerConfig.instances) = saved


def test_settings_and_keys_survive_a_round_trip(config_home):
    config.load_defaults()
    config.conf.server = "example.com"
    config.conf.fullscreen = True
    config.PlayerConfig.instances[0].keys.up = 42

    config.save()
    config.load()

    assert config.conf.server == "example.com"
    assert config.conf.fullscreen
    assert config.PlayerConfig.instances[0].keys.up == 42


def test_a_missing_file_gives_the_defaults(config_home):
    config.load()

    assert config.conf.server == config.Config.server
    assert len(config.PlayerConfig.instances) == 4


def test_an_unusable_file_gives_the_defaults(config_home):
    config.config_file().parent.mkdir(parents=True)
    config.config_file().write_text("{ this is not json")

    config.load()

    assert config.conf.server == config.Config.server
