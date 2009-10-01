import pygame
from pygame.locals import *
import os
import random

import common

music_files = ('farmor8.xm', 'fdream.xm')
next_file = random.randint(0, len(music_files)-1)
enabled = False

class DummySound:
	def play(self):
		pass

cannon = DummySound()
wall_hit = DummySound()

def sound_on():
	if not pygame.mixer.get_init():
		return

	# effects
	global cannon
	cannon = pygame.mixer.Sound(os.path.join(common.data_path, 'sound', 'cannon.wav'))
	global wall_hit
	wall_hit = pygame.mixer.Sound(os.path.join(common.data_path, 'sound', 'drop.wav'))

	# music
	play_music()

def sound_off():
	# effects
	cannon = DummySound()
	wall_hit = DummySound()

	# music
	pygame.mixer.music.stop()

def play_music():
	global next_file
	pygame.mixer.music.load(os.path.join(common.data_path, 'sound', music_files[next_file]))
	pygame.mixer.music.play()
	next_file = (next_file + 1) % len(music_files)
	pygame.mixer.music.set_endevent(common.MUSICEVENT)

import config
if pygame.mixer.get_init() and config.conf.sound:
	sound_on()

