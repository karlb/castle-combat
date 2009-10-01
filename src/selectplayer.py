import pygame
from pygame.locals import *
from numpy.oldnumeric import *

import common
from game import game
from field import Castle
from player import BasePlayer

class SelectPlayer(BasePlayer):

	select_pic = common.load_image("castleselect.png", alpha=True)

	def __init__(self, player):
		BasePlayer.__init__(self)
		self.player = player
		self.select_pic = common.colorize(SelectPlayer.select_pic, self.player.color)

	def init(self):
		BasePlayer.init(self)
		self.selected_castle = None
		self.selected_castle = self.available_castles()[0]
		self.selected_castle.selected = True
		self.finished = False
	
	def available_castles(self):
		return [
			c for c in game.field.map.castles
			if (c.player is self.player or c.player is None)
			and (not c.selected or c is self.selected_castle)
			]

	def draw_cursor(self):
		if self.finished:
			return
		draw_at = multiply( add(self.selected_castle.pos, (-4, -4)), common.block_size)
		common.blit(self.select_pic, draw_at)

	def select_castle(self, change):
		self.selected_castle.selected = False
		index = self.available_castles().index(self.selected_castle)
		index += change
		if index not in range(len(self.available_castles())):
			index %= len(self.available_castles())
		self.selected_castle = self.available_castles()[index]
		self.selected_castle.selected = True

	def confirm_select(self):
		self.selected_castle.big = True
		pos = self.selected_castle.pos
		# build wall
		x_bound = (pos[0] - 3, pos[0] + 4)
		y_bound = (pos[1] - 3, pos[1] + 4)
		for x in range(x_bound[0], x_bound[1] + 1):
			for y in range(y_bound[0], y_bound[1] + 1):
				if x in x_bound or y in y_bound:
					game.field.kill_grunt_if_there_is_one((x,y))
					game.field[x][y] = self.player.player_id
		# update screen
		game.field.look_for_secured_areas(self.player)
		game.field.draw_backbuffer()
		# disable player
		self.finished = True

	def handle_event(self, event):
		if self.finished:
			return
		if (event.type == KEYDOWN):
			keys = self.player.config.keys
			if event.key in (keys.up, keys.right):
				self.select_castle(-1)
			elif event.key in (keys.down, keys.left):
				self.select_castle(1)
			elif event.key == keys.button[0]:
				self.confirm_select()
			elif event.key == keys.button[1]:
				pass
			else:
				catched = False

	def handle_movement(self, passed_milliseconds):
		pass
	

from network import ServerObject, ClientObject, networkify
class SelectPlayerServer(ServerObject, SelectPlayer):
	def get_state(self):
		return {
			'player': self.player,
		}

class SelectPlayerClient(ClientObject, SelectPlayer):
	def set_state(self, state):
		self.__dict__ = state

		from twisted.internet import reactor
		# needs to be called later, because self.player has not been transferred, yet
		reactor.callLater(0, lambda: SelectPlayer.__init__(self, self.player))

networkify(
	cacheable = SelectPlayerServer,
	remote_cache = SelectPlayerClient,
	implementation = SelectPlayer,
	method_names = ('select_castle', 'confirm_select')
)

