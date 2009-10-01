## Automatically adapted for numpy.oldnumeric Sep 27, 2009 by 

import pygame
from pygame.locals import *
from numpy.oldnumeric import *
import os

debug = True

screen_updates = []
screen_undraws = []
block_size = 20
field_size = array((40, 30))
#data_path = "../data"
data_path = "data"

###### Exceptions ######

class ActionNotPossible(Exception): pass

class ActionIrrelevant(ActionNotPossible): pass
class AreaNotSecured(ActionNotPossible): pass
class FieldNotEmpty(ActionNotPossible): pass
class NoBlockAvailable(ActionNotPossible): pass

###### Events #####

MUSICEVENT = USEREVENT + 2

###### Graphics functions ######

def load_image(name, colorkey=None, alpha=False):
	fullname = os.path.join(data_path, 'gfx', name)
	try:
		image = pygame.image.load(fullname)
	except pygame.error, message:
		print 'Cannot load image:', name
		raise SystemExit, message
	if alpha:
		image = image.convert_alpha()
	else:
		image = image.convert()
	if colorkey is not None:
		if colorkey is -1:
			colorkey = image.get_at((0,0))
		image.set_colorkey(colorkey, RLEACCEL)
	return image

def blit(source, pos=(0,0), source_rect=None, centered=False):
	if centered:
		pos = (pos[0] - source.get_width()/2, pos[1] - source.get_height()/2)
	if source_rect:
		screen_updates.append( screen.blit(source, pos, source_rect) )
	else:
		screen_updates.append( screen.blit(source, pos) )

def backbuffer_blit(source, pos=(0,0), source_rect=None):
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
	'''Returns a new colored surface'''
	if surface.get_flags() & SRCALPHA:
		surface = surface.convert_alpha()
	else:
		surface = surface.convert()
	
	pixel_array = pygame.surfarray.pixels3d(surface)
	#pixel_array = pixel_array * color
	#pixel_array /= 255
	#pygame.surfarray.blit_array(surface, pixel_array)
	col = array(color, UInt8)
	for line in pixel_array:
		for pixel in line:
			for i in (0,1,2):
				if pixel[i]:
					pixel[i] = (int(pixel[i]) * col[i]) / 255
	return surface
	
# TODO
def multiply_alpha(surface, factor):
	'''Returns a new surface, with all alpha values multiplied by factor'''
	if surface.get_flags() & SRCALPHA:
		surface = surface.convert_alpha()
	else:
		surface = surface.convert()

	alpha = pygame.surfarray.pixels_alpha(surface)
	divide(alpha, array(factor).astype(UInt8), alpha)
	#multiply(alpha, array(factor), alpha)
	return surface

###### Auto-Reloder ######
import weakref, inspect

class MetaInstanceTracker(type):
    def __new__(cls, name, bases, ns):
        t = super(MetaInstanceTracker, cls).__new__(cls, name, bases, ns)
        t.__instance_refs__ = []
        return t
    def __instances__(self):
        instances = [(r, r()) for r in self.__instance_refs__]
        instances = filter(lambda (x,y): y is not None, instances)
        self.__instance_refs__ = [r for (r, o) in instances]
        return [o for (r, o) in instances]
    def __call__(self, *args, **kw):
        instance = super(MetaInstanceTracker, self).__call__(*args, **kw)
        self.__instance_refs__.append(weakref.ref(instance))
        return instance

class InstanceTracker:
    __metaclass__ = MetaInstanceTracker

class MetaAutoReloader(MetaInstanceTracker):
    def __new__(cls, name, bases, ns):
        new_class = super(MetaAutoReloader, cls).__new__(
            cls, name, bases, ns)
        f = inspect.currentframe().f_back
        for d in [f.f_locals, f.f_globals]:
            if d.has_key(name):
                old_class = d[name]
                for instance in old_class.__instances__():
                    instance.change_class(new_class)
                    new_class.__instance_refs__.append(
                        weakref.ref(instance))
                # this section only works in 2.3
                for subcls in old_class.__subclasses__():
                    newbases = ()
                    for base in subcls.__bases__:
                        if base is old_class:
                            newbases += (new_class,)
                        else:
                            newbases += (base,)
                    subcls.__bases__ = newbases
                break
        return new_class

class AutoReloader:
    __metaclass__ = MetaAutoReloader
    def change_class(self, new_class):
        self.__class__ = new_class


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
		for prio in self.callbacks_by_priority.keys():
			try:
				self.callbacks_by_priority[prio].remove(callback)
			except:
				pass	
	
	def emit(self, *args, **kwargs):
		keys = self.callbacks_by_priority.keys()
		keys.sort()
		keys.reverse()
		for key in keys:
			for callback in self.callbacks_by_priority[key]:
				callback(*args, **kwargs)
		
	
def init():
	global screen
	flags = 0
	import config
	if config.conf.fullscreen:
		flags |= pygame.FULLSCREEN
	screen = pygame.display.set_mode((800, 600), flags)
	global backbuffer
	global font
	font = pygame.font.Font(os.path.join(data_path, 'DefaultFancy.ttf'), 34)
	global small_font
	small_font = pygame.font.Font(os.path.join(data_path, 'DefaultFancy.ttf'), 20.5)

def info(string):
	from widget import WidgetState
	class InfoState(WidgetState):
		pass
	
	state = InfoState()
	from widget import Label
	Label(string, (None, None)).draw()
	update()
	state.quit()

def coords(stop):
	i = indices(stop)
	return zip(i[0].ravel(), i[1].ravel())

def bound(var, lower, upper):
	return max( min(var, upper), lower)

def is_in_bounds(pos):
	return list(pos) == [bound(pos[i], 1, field_size[i]-1) for i in (0,1)]

def in_bounds(pos):
	return [bound(pos[i], 1, field_size[i]-1) for i in (0,1)]

def flood_fill(fill_map, pos, source, destination):
	"""Simple flood fill algorithm"""

	# stop recursion, if this field is already filled
	if fill_map[pos] != source or pos[1] < 0 or pos[1] >= fill_map.shape[1] - 1:
		return

	y = pos[1]
	# expand horizontally
	left = pos[0]
	while left > 0 and fill_map[left-1][y] == source:
		left -= 1
	right = pos[0]
	while right < fill_map.shape[0]-1 and fill_map[right+1][y] == source:
		right += 1
	fill_map[left:right+1, y] = destination
	assert source != destination
	assert fill_map[pos] != source, str(pos) + " " + str((left, right+1, y))

	# recurse
	for x in range(left, right+1):
		flood_fill(fill_map, (x, y-1), source, destination)
		flood_fill(fill_map, (x, y+1), source, destination)

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
	while fill_map[left-1, y] == source:
		left -= 1
	right = pos[0]
	while fill_map[right+1, y] == source:
		right += 1
	fill_map[left:right+1, y] = destination
	#assert source != destination
	#assert fill_map[pos] != source, str(pos) + " " + str((left, right+1, y))

	# recurse
	for x in range(left-1, right+2):
		flood_fill2(fill_map, (x, y-1), source, destination)
		flood_fill2(fill_map, (x, y+1), source, destination)

