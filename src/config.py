from pygame.locals import *

conf = None


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

    def assign():
        i = 0
        from game import game

        for player in game.players:
            if player.local:
                print("assign config", i, "to player", player.player_id)
                config = PlayerConfig.instances[i]
                i += 1
            else:
                config = PlayerConfig(-1)
            player.set_config(config)

    assign = staticmethod(assign)


class Config:
    server = "localhost"
    total_players = 2
    local_players = 2
    ai_players = 1
    fullscreen = False
    sound = False


def open_config_file(mode):
    import os

    if os.name == "posix":
        file = open(os.path.join(os.getenv("HOME"), ".castle-combat.config"), mode)
    else:
        file = open("castle-combat.config", mode)
    return file


def save():
    conf.player_configs = PlayerConfig.instances
    conf.version = 1
    file = open_config_file("wb")
    import pickle

    pickle.dump(conf, file)


def load():
    global conf
    try:
        file = open_config_file("rb")
        import pickle

        conf = pickle.load(file)
        try:
            if conf.version != 1:
                raise "Unknown config file version."
        except AttributeError:
            print("Updating config file from alpha version")
        PlayerConfig.instances = conf.player_configs
    except IOError:
        print("Could not load user's config file, loading defaults.")
        for i in range(4):
            PlayerConfig(i)
        conf = Config()
