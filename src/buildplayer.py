import pygame
from pygame.locals import *
from numpy.oldnumeric import *
import common
import random
from copy import copy

from game import game
from field import Field, Grunt
from player import BasePlayer

class BuildPlayer(BasePlayer):

	select_pic = common.load_image('select.png', alpha=True)
	wait_pic = common.load_image('waitblock.png', alpha=True)
	cantbuild_pic = common.load_image('cantbuild.png', alpha=True)

	def __init__(self, player):
		BasePlayer.__init__(self)
		self.player = player

	def init(self):
		BasePlayer.init(self)
		self.wait_for_block = 0
		self.block = None
		self.pos = self.player.get_center()

		self.wait_pic = common.colorize(BuildPlayer.wait_pic, self.player.color)
		self.select_pic = common.colorize(BuildPlayer.select_pic, self.player.color)
			
	def handle_event(self, event):
		self.handle_build_or_place_event(event, (self.put_block, self.rotate_block), self.pos )

	def handle_movement(self, passed_milliseconds):
		if game.server and self.block == None:
			self.wait_for_block -= passed_milliseconds
			if self.wait_for_block <= 0:
				self.generate_random_block()

	def is_allowed(self, pos):
		if not 'build_only_near_walls' in game.field.map.game_options:
			return True
		else:
			topleft = common.in_bounds(subtract(pos, 3))
			bottomright = common.in_bounds(add(pos, 4))
			surroundings = game.field[topleft[0]:bottomright[0], topleft[1]:bottomright[1]]
			return sometrue(surroundings == self.player.player_id)
	
	def draw_cursor(self):
		if self.block:
			for x in range(3):
				for y in range(3):
					if self.block[x][y]:
						xpos = x + self.pos[0] - 1
						ypos = y + self.pos[1] - 1
						screen_pos = (xpos * common.block_size, ypos * common.block_size)
						common.blit(self.select_pic, screen_pos)
						if not self.is_allowed((xpos, ypos)):
							common.blit(self.cantbuild_pic, screen_pos)
		else:
			common.blit(self.wait_pic, (self.pos[0] * common.block_size, self.pos[1] * common.block_size) )

	def put_block(self):
		# Does the player have a block?
		if not self.block:
			raise common.NoBlockAvailable

		field = game.field
		# Can the block be placed here?
		for x in range(3):
			for y in range(3):
				if self.block[x][y]:
					xpos = x + self.pos[0] - 1
					ypos = y + self.pos[1] - 1
					if 'field_owners' in game.field.map.game_options and field.owner[xpos][ypos] != self.player.player_id:
						raise common.ActionNotPossible
					if not self.is_allowed((xpos,ypos)):
						raise common.ActionNotPossible
					if field[xpos][ypos] not in (Field.EMPTY, Field.HOUSE):
						raise common.FieldNotEmpty
		# Place the block
		for x in range(3):
			for y in range(3):
				if self.block[x][y]:
					xpos = x + self.pos[0] - 1
					ypos = y + self.pos[1] - 1
					if field[xpos][ypos] == Field.HOUSE:
						field.blit_background((xpos,ypos))
						Grunt((xpos, ypos))
					else:
						common.backbuffer_blit(self.player.wall_pic, (xpos * common.block_size, ypos * common.block_size) )
						field[xpos][ypos] = self.player.player_id
		# The player will have to wait a short time until he gets the next block
		self.block = None
		self.wait_for_block = 500
		field.look_for_secured_areas(self.player)

	def move(self, vector):
		old_pos = self.pos
		self.pos = tuple(add(self.pos, vector))
		if self.pos != self.bounded_pos():
			self.pos = old_pos
			raise common.ActionNotPossible
	
	def bounded_pos(self):
		# allow moving closer to the edges if outer rows or coloumns are empty
		margin = ([1,1], [1,1])
		if self.block:
			for side in (0,1):
				for i in range(3):
					if self.block[-side][i]:
						margin[0][side] = 0
					if self.block[i][-side]:
						margin[1][side] = 0

		return tuple(common.bound(self.pos[dim], 1-margin[dim][0], common.field_size[dim] - 2 + margin[dim][1]) for dim in (0,1))
	
	def rotate_block(self):
		if not self.block:
			raise common.ActionNotPossible
		self.block = ( (self.block[0][2], self.block[1][2], self.block[2][2]),
					   (self.block[0][1], self.block[1][1], self.block[2][1]),
					   (self.block[0][0], self.block[1][0], self.block[2][0]) )
		self.pos = self.bounded_pos()
	
	def generate_random_block(self):
		self.generate_block(random.randint(0, 10), random.randint(0, 3))
	
	def generate_block(self, piece, turn):
		if piece in (0,1):
			self.block = ( (0,1,0),
						   (0,1,0),
					  	   (0,1,1), )
		elif piece == 2:
			self.block = ( (0,1,0),
						   (0,1,0),
					  	   (1,1,0), )
		elif piece in (3,4,5):
			self.block = ( (0,1,0),
						   (1,1,0),
					  	   (0,0,0), )
		elif piece in (6,7):
			self.block = ( (0,1,0),
						   (0,1,0),
					  	   (0,1,0), )
		elif piece in (8,9):
			self.block = ( (1,1,0),
						   (0,1,0),
					  	   (1,1,0), )
		elif piece == 10:
			self.block = ( (0,0,0),
						   (0,1,0),
					  	   (0,0,0), )

		if game.server:
			for x in range(turn):
				self.rotate_block()

		self.pos = self.bounded_pos()
	

from network import ServerObject, ClientObject, networkify
class BuildPlayerServer(ServerObject, BuildPlayer):
	def get_state(self):
		return {
			'player': self.player,
		}

class BuildPlayerClient(ClientObject, BuildPlayer):
	def set_state(self, state):
		self.__dict__ = state
		BasePlayer.__init__(self)

networkify(
	cacheable = BuildPlayerServer,
	remote_cache = BuildPlayerClient,
	implementation = BuildPlayer,
	method_names = ('move', 'put_block', 'rotate_block', 'generate_block')
)
