import pygame
from pygame.locals import *
from Numeric import *
from random import randint
from twisted.spread import pb
from copy import deepcopy

from game import game
import common

class Castle(pb.Copyable, pb.RemoteCopy):

	#instances = []
	castle_pic = common.load_image('castle.png', alpha=True)
	bigcastle_pic = common.load_image('bigcastle.png', alpha=True)
	
	def __init__(self, pos, player, map):
		self.pos = tuple(pos)
		self.player = player
		self.big = False
		self.selected = False # For select phase only
		#Castle.instances.append(self)
		for x in (0,1):
			for y in (0,1):
				map.array[pos[0] + x][pos[1] + y] = Field.CASTLE
		
	def backbuffer_blit(self):
		if self.big == False:
			pic = Castle.castle_pic
		else:
			pic = Castle.bigcastle_pic
		
		common.backbuffer_blit(pic, multiply(self.pos, common.block_size))
		# game.field.surface.blit(pic, screen_pos)

	def getStateToCopy(self):
		state = self.__dict__.copy()
		return state
	
	def setCopyableState(self, state):
		self.__dict__ = state

pb.setUnjellyableForClass(Castle, Castle)


class Grunt:

	instances = []
	grunt_pics = [common.load_image('tank%d.png' % (i+1), alpha=True) for i in range(4)]
	movement = ((0, -1), (1, 0), (0, 1), (-1,0))

	def __init__(self, pos):
		self.pos = pos
		self.direction = randint(0,3)
		if not self.instances:
			self.id = 0
		else:
			self.id = max([g.id for g in self.instances]) + 1
		self.instances.append(self)
		self.time_to_action = randint(500, 1000)
		game.field[pos] = Field.GRUNT

		# display grunt on the server and all clients (via callLater because __init__ was called from game.call())
		from twisted.internet import reactor
		#reactor.callLater(0, lambda:
		#	game.server_call("rotate_grunt", self.id, self.direction)
		#)
	
	def handle(self, passed_milliseconds):
		self.time_to_action -= passed_milliseconds
		if self.time_to_action <= 0:
			# have a look at my movement possibilities 
			new_pos = add(self.pos, self.movement[self.direction])
			if common.is_in_bounds(new_pos):
				wall_in_front = game.field[new_pos] >= 0
			else:
				wall_in_front = False
			wall_in_sight = randint(0, 3)
			for i in range(randint(0, 10)):
				test_pos = add(self.pos, multiply(self.movement[self.direction], i))
				if not common.is_in_bounds(test_pos) or game.field[test_pos] in (Field.CASTLE, Field.HOUSE, Field.RIVER) + Field.ANY_GARBAGE:
					wall_in_sight = False
					break
				if game.field[test_pos] >= 0:
					wall_in_sight = True
					break
			# make decision
			if wall_in_front:
				game.server_call("hit", tuple(new_pos))
				self.time_to_action += randint(2000, 4500)
			elif common.is_in_bounds(new_pos) and wall_in_sight and game.field[new_pos] == Field.EMPTY:
				game.server_call("move_grunt", self.id, tuple(new_pos))
				self.time_to_action += randint(1000, 1500)
			else:
				new_dir = (self.direction + 1 - 2 * randint(0,1)) % 4
				game.server_call("rotate_grunt", self.id, new_dir)
				self.time_to_action += randint(1000, 1500)
	
	def rotate(self, new_dir):
		self.direction = new_dir
		game.field.blit_background(self.pos)
		self.backbuffer_blit()
	
	def move(self, new_pos):
		game.field[self.pos] = Field.EMPTY
		game.field.blit_background(self.pos)
		self.pos = new_pos
		game.field[self.pos] = Field.GRUNT
		self.backbuffer_blit()
	
	def backbuffer_blit(self):
		assert game.field[self.pos] == Field.GRUNT
		common.backbuffer_blit(self.grunt_pics[self.direction], multiply(self.pos, common.block_size))


class Field:
	
	# all values >= 0 are walls belonging to the player with that index
	(EMPTY, GARBAGE_OLD, GARBAGE_MED, GARBAGE_NEW, RIVER, CANNON, CASTLE, HOUSE, GRUNT) = range(-1, -10, -1)
	ANY_GARBAGE = GARBAGE_OLD, GARBAGE_MED, GARBAGE_NEW

	obstacle_pic = {
		GARBAGE_NEW: common.load_image('garbage-new.png', alpha=True),
		GARBAGE_MED: common.load_image('garbage-med.png', alpha=True),
		GARBAGE_OLD: common.load_image('garbage-old.png', alpha=True),
		HOUSE: common.load_image('house.png', alpha=True)
	}

	def __init__(self, map):
		self.map = map
		self.array = zeros(common.field_size) + Field.EMPTY

	def init(self):
		self.map.apply()

	def create_background(self):

		def create_basic_background():
			''' Returns an array with one element per pixel in the background.

			This element is 1 if in a river and 0 else
			'''
			is_river = where(self.array == self.RIVER, 1, 0)
			is_river_large = repeat( repeat(is_river, common.block_size, 0), common.block_size, 1)
			return is_river_large

		def scatter(source):
			import RandomArray
			shift3d = RandomArray.randint(-2, 2, (2,) + source.shape)
			shift = shift3d[1] * source.shape[1] + shift3d[0]
			length = product(source.shape)
			source_indices = zeros(source.shape)
			source_indices.flat[:] = arange(length) + shift.flat
			source_indices = maximum(source_indices, 0)
			source_indices = minimum(source_indices, length-1)

			dest = take(source.flat, source_indices)
			
			return dest

		def colorize(source):
			dest = zeros(source.shape + (3,))
			dest[:,:,0] = where(source == 0, 100, 50) 
			dest[:,:,1] = where(source == 0, 120, 50) 
			dest[:,:,2] = where(source == 0, 20, 200) 

			return dest

		import time
		t1 = time.clock()
		pixels = create_basic_background()
		t2 = time.clock()
		pixels = scatter(pixels)
		t3 = time.clock()
		pixels = colorize(pixels)
		t4 = time.clock()
		
		print "Background creation timing:", t2-t1, t3-t2, t4-t3
				
		self.surface = pygame.surfarray.make_surface(pixels)
		common.backbuffer = self.surface.convert()

	def __getitem__(self, index):
		try:
			return self.array[index]
		except IndexError:
			raise IndexError, "Wrong Index: " + str(index)

	def __setitem__(self, index, value):
		self.array[index] = value

	def add_houses(self, amount):
		while amount > 0:
			try: 
				game.server_call( "new_house",
						(
							randint(0, common.field_size[0]-1),
							randint(0, common.field_size[1]-1)
						)
				)
				amount -= 1
			except common.ActionNotPossible:
				pass


	def update(self, pos, draw_cannons=True):
		"""Draws everything on this field, except the ground and player color"""
		screen_pos = multiply(pos, common.block_size) 
		if self[pos] >= 0:
			common.backbuffer.blit(game.players[self[pos]].wall_pic, screen_pos)
		elif self[pos] in self.obstacle_pic.keys():
			common.backbuffer.blit(self.obstacle_pic[self[pos]], screen_pos)
		elif self[pos] == self.CANNON:
			for can in game.cannons:
				if can.pos == pos and (draw_cannons or can.hitpoints <= 0):
					can.backbuffer_blit()
					break
		elif self[pos] == self.CASTLE:
			for castle in self.map.castles:
				if castle.pos == pos:	
					castle.backbuffer_blit()
					break
		elif self[pos] == self.GRUNT:
			for grunt in Grunt.instances:
				if tuple(grunt.pos) == pos:
					grunt.backbuffer_blit()
					return
			assert False, "One Grunt instance must correspond to each field with the value Field.GRUNT, but no instance for " + str(pos) + " found. Instances are at " + str([g.pos for g in Grunt.instances]) + "."
	
	def blit_background(self, pos):
		screen_pos = (pos[0]*common.block_size, pos[1]*common.block_size)
		common.backbuffer_blit( self.surface,
				screen_pos,
				screen_pos + (common.block_size, )*2
		)
	
	def blit_ground(self, pos):
		for player in game.players:
			if player.secured[pos]:
				screen_pos = multiply(pos, common.block_size) 
				common.backbuffer.blit(player.ground_pic, screen_pos)
	
	def blit_field(self, pos):
		self.blit_background(pos)
		self.blit_ground(pos)
		self.update(pos)

	def look_for_secured_areas(self, player, restart_at=None):
						
		def generate_fill_map(player_id):
			"""Generates a map suitable for flood fill

			Empty fields are set to zero, the border and all fields with walls belonging
			to the given player are set to one.
			"""
			# build map with borders
			fill_map = zeros(common.field_size + 4)
			fill_map[0, :] = 1
			fill_map[-1, :] = 1
			fill_map[:, 0] = 1
			fill_map[:, -1] = 1

			# copy player wall into the fill_map
			main_map = where(self.array == player_id, 2, 0)
			fill_map[2:-2, 2:-2] = main_map
			return fill_map

		def update_screen(old_secured, foreign_walls):
			# get some local vars for speed
			block_size = common.block_size
			field_size = common.field_size[1]

			# check which parts have changed
			different = (old_secured != player.secured)
			changed_fields = nonzero(different.flat).tolist()
			changed_fields.reverse()
			for index in changed_fields:
				x, y = divmod(index, field_size)
				# the screen has changed at x, y => update the screen
				if not old_secured[x,y]:
					screen_pos = (x*block_size, y*block_size)
					if self[x,y] in (self.HOUSE, self.GRUNT) or foreign_walls[x,y]:
						self.kill_grunt_if_there_is_one((x,y))
						self.blit_background((x,y))
						self[x,y] = self.EMPTY
					common.backbuffer_blit(player.ground_pic, screen_pos)
				else:
					self.blit_background((x,y))
				self.update((x,y), restart_at == None)

		import time
		t1 = time.clock()

		if not restart_at:
			# do a complete check
			fill_map = generate_fill_map(player.player_id)
			t2 = time.clock()
			common.flood_fill2(fill_map, (1,1), False, True)
		else:
			# just calculate the changes caused by changeing the value at restart_at
			restart_at = add(restart_at, 2)
			fill_map = player.fill_map
			unsecured_surroundings = fill_map[restart_at[0]-1:restart_at[0]+2, restart_at[1]-1:restart_at[1]+2] == 1
			if not nonzero(ravel(unsecured_surroundings)):
				restart_at = subtract(restart_at, 2)
				player.secured[restart_at] = True
				#common.backbuffer.blit(player.ground_pic, [restart_at[i] * common.block_size for i in (0,1)])
				#self.update(restart_at)
				return
			fill_map[restart_at] = 0
			t2 = time.clock()
			common.flood_fill2(fill_map, restart_at, False, True)
		
		t3 = time.clock()

		# save results
		old_secured = player.secured	# for update_screen
		player.secured = (fill_map[2:-2, 2:-2] == 0)
		player.fill_map = fill_map

		# eleminate other player's walls
		foreign_walls = player.secured * (self.array >= 0) * (self.array != player.player_id)
		putmask(self.array, foreign_walls, zeros(self.array.shape) + Field.EMPTY)

		# now we know which areas are secured, so let's update the screen
		update_screen(old_secured, foreign_walls)

		t4 = time.clock()
		print 'Setup:', t2-t1, '+ Flood Fill:', t3-t2, '+ Redraw:', t4-t3, '= Total:', t4-t1

	def kill_grunt_if_there_is_one(self, pos):
		if self[pos] == self.GRUNT:
			defeated_grunt = [g for g in Grunt.instances if tuple(g.pos) == tuple(pos)][0]
			Grunt.instances.remove(defeated_grunt)

	def draw_backbuffer(self, draw_cannons=True):
		common.backbuffer.blit(self.surface, (0,0))
		all_fields = common.coords(common.field_size)
		all_fields.reverse()
		for pos in all_fields:
			self.blit_ground(pos)
			self.update(pos, draw_cannons)
		
		common.blit(common.backbuffer)

