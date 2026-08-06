import pygame
import numpy as np
from numpy import array, indices
import os

debug = False

screen_updates = []
screen_undraws = []
backbuffer = None
block_size = 20
field_size = array((40, 30))
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

###### Exceptions ######


class ActionNotPossible(Exception):
    pass


class ActionIrrelevant(ActionNotPossible):
    pass


class AreaNotSecured(ActionNotPossible):
    pass


class FieldNotEmpty(ActionNotPossible):
    pass


class NoBlockAvailable(ActionNotPossible):
    pass


###### Events #####

MUSICEVENT = pygame.USEREVENT + 2

###### Graphics functions ######


def load_image(name, colorkey=None, alpha=False):
    fullname = os.path.join(data_path, "gfx", name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print("Cannot load image:", name)
        raise SystemExit(message)
    if alpha:
        image = image.convert_alpha()
    else:
        image = image.convert()
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, pygame.RLEACCEL)
    return image


def blit(source, pos=(0, 0), source_rect=None, centered=False):
    if centered:
        pos = (pos[0] - source.get_width() / 2, pos[1] - source.get_height() / 2)
    if source_rect:
        screen_updates.append(screen.blit(source, pos, source_rect))
    else:
        screen_updates.append(screen.blit(source, pos))


def backbuffer_blit(source, pos=(0, 0), source_rect=None):
    blit(source, pos, source_rect)
    if source_rect:
        backbuffer.blit(source, pos, source_rect)
    else:
        backbuffer.blit(source, pos)


def update():
    global screen_updates
    global screen_undraws
    pygame.display.update(screen_updates + screen_undraws)
    # This is what the user sees, now begin undrawing
    for x in screen_updates:
        screen.blit(backbuffer, x, x)
    screen_undraws = screen_updates
    screen_updates = []


def colorize(surface, color):
    """Returns a new colored surface"""
    if surface.get_flags() & pygame.SRCALPHA:
        surface = surface.convert_alpha()
    else:
        surface = surface.convert()

    pixel_array = pygame.surfarray.pixels3d(surface)
    # uint16 keeps the intermediate product below 255 * 255 from overflowing.
    # Colors may carry an alpha component, which pixels3d() does not cover.
    col = array(color, np.uint16)[:3]
    pixel_array[:] = pixel_array * col // 255
    return surface


###### Misc ######


class Borg:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class Signal:
    def __init__(self):
        self.callbacks_by_priority = {}

    def connect(self, callback, priority=0):
        try:
            self.callbacks_by_priority[priority]
        except KeyError:
            self.callbacks_by_priority[priority] = []
        self.callbacks_by_priority[priority].append(callback)

    def disconnect(self, callback):
        for prio in list(self.callbacks_by_priority.keys()):
            try:
                self.callbacks_by_priority[prio].remove(callback)
            except ValueError:
                # not connected at this priority
                pass

    def emit(self, *args, **kwargs):
        keys = list(self.callbacks_by_priority.keys())
        keys.sort()
        keys.reverse()
        for key in keys:
            for callback in self.callbacks_by_priority[key]:
                callback(*args, **kwargs)


def display_flags():
    from . import config

    # SCALED draws the game at its fixed 800x600 layout and lets SDL scale that
    # up to the display. Without it, fullscreen switches the screen to a 800x600
    # video mode, or leaves the game sitting in a corner of a larger surface
    # with all edge-anchored widgets placed off the background.
    flags = pygame.SCALED
    if config.conf.fullscreen:
        flags |= pygame.FULLSCREEN
    return flags


def set_fullscreen(fullscreen):
    """Switch between fullscreen and windowed mode without restarting

    pygame.display.toggle_fullscreen() is not supported everywhere, so go
    through set_mode(), which is the same call that set up the display.
    """
    global screen
    from . import config

    fullscreen = bool(fullscreen)
    if fullscreen == bool(config.conf.fullscreen):
        return
    config.conf.fullscreen = fullscreen
    screen = pygame.display.set_mode((800, 600), display_flags())
    redraw()


def toggle_fullscreen():
    from . import config

    set_fullscreen(not config.conf.fullscreen)


def redraw():
    """Repaint the whole screen, e.g. after the display mode changed"""
    global screen_updates
    global screen_undraws
    if backbuffer is None:
        return
    screen.blit(backbuffer, (0, 0))
    pygame.display.update()
    screen_updates = []
    screen_undraws = []


def init():
    global screen
    screen = pygame.display.set_mode((800, 600), display_flags())
    global font
    font = pygame.font.Font(os.path.join(data_path, "DefaultFancy.ttf"), 34)
    global small_font
    small_font = pygame.font.Font(os.path.join(data_path, "DefaultFancy.ttf"), 20)


def info(string):
    from .widget import WidgetState

    class InfoState(WidgetState):
        pass

    state = InfoState()
    from .widget import Label

    Label(string, (None, None)).draw()
    update()
    state.quit()


def coords(stop):
    i = indices(stop)
    return list(zip(i[0].ravel(), i[1].ravel()))


def bound(var, lower, upper):
    return max(min(var, upper), lower)


def is_in_bounds(pos):
    return list(pos) == [bound(pos[i], 1, field_size[i] - 1) for i in (0, 1)]


def in_bounds(pos):
    return [bound(pos[i], 1, field_size[i] - 1) for i in (0, 1)]


def flood_fill(fill_map, pos, source, destination):
    """Simple flood fill algorithm"""

    # stop recursion, if this field is already filled
    if fill_map[pos] != source or pos[1] < 0 or pos[1] >= fill_map.shape[1] - 1:
        return

    y = pos[1]
    # expand horizontally
    left = pos[0]
    while left > 0 and fill_map[left - 1][y] == source:
        left -= 1
    right = pos[0]
    while right < fill_map.shape[0] - 1 and fill_map[right + 1][y] == source:
        right += 1
    fill_map[left : right + 1, y] = destination
    assert source != destination
    assert fill_map[pos] != source, str(pos) + " " + str((left, right + 1, y))

    # recurse
    for x in range(left, right + 1):
        flood_fill(fill_map, (x, y - 1), source, destination)
        flood_fill(fill_map, (x, y + 1), source, destination)


def flood_fill2(fill_map, pos, source, destination):
    """Special flood fill algorithm

    Optimized for enclosed territory calculation.
    - Fills diagonally
    - Works only if the algorithm doesn't reach the edges"""

    # stop recursion, if this field is already filled
    if fill_map[pos] != source:
        return

    y = pos[1]
    # expand horizontally
    left = pos[0]
    while fill_map[left - 1, y] == source:
        left -= 1
    right = pos[0]
    while fill_map[right + 1, y] == source:
        right += 1
    fill_map[left : right + 1, y] = destination
    # assert source != destination
    # assert fill_map[pos] != source, str(pos) + " " + str((left, right+1, y))

    # recurse
    for x in range(left - 1, right + 2):
        flood_fill2(fill_map, (x, y - 1), source, destination)
        flood_fill2(fill_map, (x, y + 1), source, destination)
