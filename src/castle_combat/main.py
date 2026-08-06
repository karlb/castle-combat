import pygame
from pygame.locals import *
from . import common


def init():
    pygame.init()
    common.init()


def main():
    from . import config

    config.load()
    init()

    from .state import MainState, runStateLoop

    MainState()

    from .menu import MenuState

    MenuState()

    runStateLoop()

    config.save()


if __name__ == "__main__":
    main()
