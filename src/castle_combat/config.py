import json
import os
from pathlib import Path

from pygame.locals import *

conf = None

CONFIG_VERSION = 2

# the Config attributes that are worth remembering between runs
SETTINGS = (
    "server",
    "total_players",
    "local_players",
    "ai_players",
    "fullscreen",
    "sound",
)


class Keys:
    def __init__(self):
        self.up = self.down = self.left = self.right = None
        self.button = (None, None)


class PlayerConfig:

    instances = []

    def __init__(self, player_id):
        self.keys = Keys()
        if player_id == -1:
            # dummy config
            return
        PlayerConfig.instances.append(self)
        if player_id == 0:
            self.keys.up = K_UP
            self.keys.down = K_DOWN
            self.keys.left = K_LEFT
            self.keys.right = K_RIGHT
            self.keys.button = [K_RETURN, K_RSHIFT]
        elif player_id == 1:
            self.keys.up = K_e
            self.keys.down = K_d
            self.keys.left = K_s
            self.keys.right = K_f
            self.keys.button = [K_a, K_q]
        elif player_id == 2:
            self.keys.up = K_KP8
            self.keys.down = K_KP5
            self.keys.left = K_KP4
            self.keys.right = K_KP6
            self.keys.button = [K_KP1, K_KP2]
        elif player_id == 3:
            self.keys.up = K_i
            self.keys.down = K_k
            self.keys.left = K_j
            self.keys.right = K_l
            self.keys.button = [K_h, K_y]

    @staticmethod
    def assign():
        i = 0
        from .game import game

        for player in game.players:
            if player.local:
                config = PlayerConfig.instances[i]
                i += 1
            else:
                config = PlayerConfig(-1)
            player.set_config(config)


class Config:
    server = "localhost"
    total_players = 2
    local_players = 2
    ai_players = 1
    fullscreen = False
    sound = False


def config_file():
    """Where the settings live, per the XDG base directory spec"""
    base = os.environ.get("XDG_CONFIG_HOME")
    directory = Path(base) if base else Path.home() / ".config"
    return directory / "castle-combat" / "config.json"


def load_defaults():
    global conf
    PlayerConfig.instances = []
    for player_id in range(4):
        PlayerConfig(player_id)
    conf = Config()


def save():
    data = {
        "version": CONFIG_VERSION,
        "settings": {name: getattr(conf, name) for name in SETTINGS},
        "keys": [
            {
                "up": player_config.keys.up,
                "down": player_config.keys.down,
                "left": player_config.keys.left,
                "right": player_config.keys.right,
                "button": list(player_config.keys.button),
            }
            for player_config in PlayerConfig.instances
        ],
    }
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load():
    load_defaults()
    try:
        data = json.loads(config_file().read_text())
        if data["version"] != CONFIG_VERSION:
            raise ValueError("unknown version %r" % (data["version"],))
        for name, value in data["settings"].items():
            # ignore settings this version has dropped
            if name in SETTINGS:
                setattr(conf, name, value)
        for player_config, keys in zip(PlayerConfig.instances, data["keys"]):
            player_config.keys.up = keys["up"]
            player_config.keys.down = keys["down"]
            player_config.keys.left = keys["left"]
            player_config.keys.right = keys["right"]
            # a list, because the options menu assigns to its elements
            player_config.keys.button = list(keys["button"])
    except FileNotFoundError:
        pass
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Ignoring unusable config file %s: %s" % (config_file(), error))
        load_defaults()
