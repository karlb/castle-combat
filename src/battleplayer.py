import pygame
from pygame.locals import *
from numpy.oldnumeric import *

import common
import random
from cannon import Shot
from player import BasePlayer
from game import game

class BattlePlayer(BasePlayer):

	crosshair_pic =  common.load_image('crosshair.png', alpha=True)
	empty_crosshair_pic =  common.load_image('notready.png', alpha=True)

	def __init__(self, player):
		BasePlayer.__init__(self)
		self.player = player
		self.move = [0,0]

	def init(self):
		BasePlayer.init(self)
		self.pos = list(multiply(self.player.get_center(), common.block_size))
		self.move = [0,0]
		self.crosshair_pic = common.colorize(BattlePlayer.crosshair_pic, self.player.color)
		self.empty_crosshair_pic = common.colorize(BattlePlayer.empty_crosshair_pic, self.player.color)

	def draw_cursor(self):
		if self.get_free_cannon() and game.phase.time_left > 0:
			pic = self.crosshair_pic
		else:
			pic = self.empty_crosshair_pic
		common.blit(pic, self.pos, centered=True)
	
	def get_move(self):
		keystate = pygame.key.get_pressed()
		keys = self.player.config.keys
		move = [0, 0]

		if keystate[keys.up]:
			move[1] -= 1
		if keystate[keys.down]:
			move[1] += 1
		if keystate[keys.left]:
			move[0] -= 1
		if keystate[keys.right]:
			move[0] += 1
		if keystate[keys.button[1]]:
			move[0] *= 3
			move[1] *= 3

		return move

	def handle_event(self, event):
		if event.type == KEYDOWN:
			if event.key == self.player.config.keys.button[0]:
				self.shoot(self.pos)
		if event.type in (KEYDOWN, KEYUP): 
			if self.get_move() != self.move:
				self.set_movement(self.get_move())
	
	def set_movement(self, move):
		self.move = move

	def handle_movement(self, passed_milliseconds):
		for i in (0, 1):
			self.pos[i] += self.move[i] * passed_milliseconds * 0.1
			self.pos[i] = common.bound(self.pos[i], 0, common.screen.get_size()[i]-1)
	
	def shoot(self, pos):
		# don't shoot after the turn ends
		if game.phase.time_left <= 0:
			raise common.ActionNotPossible
		# look for a free cannon and shoot
		can = self.get_free_cannon()
		if can:
			can.in_use = True
			Shot(can, pos)
			game.cannons.remove(can)
			game.cannons.append(can)
		else:
			raise common.ActionNotPossible

	def get_free_cannon(self):
		available_cannons = [can for can in game.cannons if not can.in_use and can.player is self.player and can.hitpoints > 0]
		if available_cannons:
			return available_cannons[0]
		else:
			return None
	
	
from network import ServerObject, ClientObject, networkify
class BattlePlayerServer(ServerObject, BattlePlayer):
	def get_state(self):
		return {
			'player': self.player,
		}

class BattlePlayerClient(ClientObject, BattlePlayer):
	def set_state(self, state):
		self.__dict__ = state
		BasePlayer.__init__(self)

networkify(
	cacheable = BattlePlayerServer,
	remote_cache = BattlePlayerClient,
	implementation = BattlePlayer,
	method_names = ('shoot', 'set_movement')
)
	
