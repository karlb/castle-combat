import pygame
from pygame.locals import *
from random import randint
import math

import common
from game import game
import sound

class Shot:

	shot_pic = common.load_image('shot.png', alpha=True)

	def __init__(self, cannon, target):
		game.shots.append(self)
		self.cannon = cannon
		self.origin = map(lambda x: (x + cannon.size*0.5) * common.block_size, cannon.pos)
		self.target = tuple(target)
		self.time_since_start = 0.0
		self.time_to_target = math.hypot(self.origin[0] - target[0], self.origin[1] - target[1]) * 7
		sound.cannon.play()
		
	def draw(self):
		common.blit(self.shot_pic, self.get_pos(), centered=True)
		
	def get_pos(self):
		return map(lambda o, t: o * (1-self.ratio) + t * self.ratio, self.origin, self.target)
		
	def handle(self, passed_milliseconds):
		self.time_since_start += passed_milliseconds
		try:
			self.ratio = self.time_since_start/self.time_to_target
		except ZeroDivisionError:
			self.ratio = 1
		if (self.ratio >= 1):
			# target hit
			sound.wall_hit.play()
			self.ratio = 1
			game.shots.remove(self)
			if game.server:
				x = int(self.get_pos()[0]) / common.block_size
				y = int(self.get_pos()[1]) / common.block_size
				game.server_call("hit", (x,y), self.cannon.id)
				

class Cannon(common.AutoReloader):

	cannon_pic = ( 
			[common.load_image('cannon%04d.png' % i, -1) for i in range(1, 31)],
			[common.load_image('bigcannon%04d.png' % i, -1) for i in range(1, 31)],
	)
	destroyed_pic = (
			[common.load_image('destroyed-cannon%d.png' % i, -1) for i in range(1, 6)],
			[common.load_image('destroyed-bigcannon%d.png' % i, -1) for i in range(1, 6)],

	)
	price = (1, 3)

	def __init__(self, pos, player, type=0):
		self.player = player
		self.pos = tuple(pos)
		self.in_use = False
		self.id = len(game.cannons)
		self.type = type
		self.cannon_pic = Cannon.cannon_pic[self.type]
		self.static_pic = self.cannon_pic[0]
		if type == 0:
			self.size = 2
			self.hitpoints = 6
		else:
			self.size = 3
			self.hitpoints = 18
	
		import field
		for x in range(self.size):
			for y in range(self.size):
				if not player.secured[self.pos[0]+x][self.pos[1]+y]:
					raise common.AreaNotSecured
				if game.field[self.pos[0]+x][self.pos[1]+y] != field.Field.EMPTY:
					raise common.FieldNotEmpty

		for x in range(self.size):
			for y in range(self.size):
				game.field[self.pos[0]+x][self.pos[1]+y] = field.Field.CANNON
				
		game.cannons.append(self)

	def hit(self):
		print "cannon hit!"
		self.hitpoints -= 1
		if self.hitpoints == 0:
			self.static_pic = self.destroyed_pic[self.type][randint(0, 4)]
			self.backbuffer_blit()

	def backbuffer_blit(self):
		common.backbuffer_blit(self.static_pic, (self.pos[0]*common.block_size, self.pos[1]*common.block_size) )

	def blit(self):
		if self.hitpoints <= 0:
			return
		cannon_center = [(self.pos[i] + (2.0 + self.type)/2) * common.block_size for i in range(2)]
		delta = [self.player.battle_player.pos[i] - cannon_center[i] for i in range(2)]
		if delta[0] == 0:
			if delta[1] < 0:
				pic = 0
			else:
				pic = 15
		else:
			angle = math.atan(delta[1]/delta[0])
			angle = angle/(2*math.pi) + 1.23
			if delta[0] < 0:
				angle += 0.5
			pic = int((1-angle) * 30)
			while pic < 0:
				pic += 30
		try:
			common.blit(self.cannon_pic[pic], (self.pos[0]*common.block_size, self.pos[1]*common.block_size) )
		except IndexError:
			print pic, angle
			raise

