import pygame
from pygame.locals import *
from numpy.oldnumeric import *
from twisted.spread import pb

import common
import random
from game import game

class BasePlayer:

	repeat_threshold = 0.6 # has to be a multiple of repeat_interval
	repeat_interval = 0.12
	directions = ('up', 'down', 'left', 'right')
	movement = {
		'up': (0, -1),
		'down': (0, 1),
		'left': (-1, 0),
		'right': (1, 0),
	}

	def __init__(self):
		def repeat_func(dir):
			looping_call = getattr(self, dir + '_repeat')
			self.move(self.movement[dir]) 
			if looping_call.interval != self.repeat_interval:
				# switch from repeat_threshold to repeat_interval
				looping_call.interval = self.repeat_interval

		from twisted.internet.task import LoopingCall
		for dir in self.directions:
			setattr(self, dir + '_repeat', LoopingCall(repeat_func, dir))

	def init(self):
		# clear key repeat status
		for dir in self.directions:
			looping_call = getattr(self, dir + '_repeat')
			if looping_call.running:
				looping_call.stop()


	def call(self, command, *args, **kwargs):
		if game.server:
			self.player.remote_call(command, *args, **kwargs)
		else:
			self.player.remote_ref.callRemote("call", command, *args, **kwargs)

	def handle_build_or_place_event(self, event, buttons, pos):
		keys = self.player.config.keys
		if (event.type == KEYDOWN):
			for dir in self.directions:
				if event.key == getattr(keys, dir):
					self.move(self.movement[dir])
					looping_call = getattr(self, dir + '_repeat')
					if not looping_call.running:
						looping_call.start(interval=self.repeat_threshold, now=False)
			if event.key == keys.button[0]:
				buttons[0]()
			elif event.key == keys.button[1]:
				buttons[1]()
		if (event.type == KEYUP):
			for dir in self.directions:
				if event.key == getattr(keys, dir):
					looping_call = getattr(self, dir + '_repeat')
					if looping_call.running:
						looping_call.stop()

			
class Player:

	colors = (Color('red'), Color('green'), Color('blue'), Color('yellow'), Color('brown'), Color('cyan'), Color('black'), Color('white'))
	names = ("Red Player", "Green Player", "Blue Player", "Yellow Player", "Brown Player", "Cyan Player", "Black Player", "White Player")

	wall_pic = common.load_image('wall.png')
	ground_pic = common.load_image('ground.png', alpha=True)

	def __init__(self, player_id):
		self.connected = False # for server only
		self.alive = True
		self.secured = zeros(common.field_size)
		self.local = False
		self.ai = False
		#self.center = common.field_size / 2
	
		self.set_player_id(player_id)

		import buildplayer
		import placeplayer
		import battleplayer
		import selectplayer
		self.build_player = buildplayer.BuildPlayerServer(self)
		self.place_player = placeplayer.PlacePlayerServer(self)
		self.battle_player = battleplayer.BattlePlayerServer(self)
		self.select_player = selectplayer.SelectPlayerServer(self)
		
	def set_player_id(self, id):
		self._player_id = id
		self.name = self.names[id]
		self.color = self.colors[id]
		self.wall_pic = common.colorize(self.wall_pic, self.color)
		self.ground_pic = common.colorize(self.ground_pic, self.color)
	def get_player_id(self):
		return self._player_id
	player_id = property(get_player_id, set_player_id)
	
	def set_config(self, config):
		self.config = config
		
	def __repr__(self):
		return self.name
		
	def init_phase(self, phase):
		self.phase_player = eval('self.' + phase + '_player')
		self.phase_player.init()

	def get_center(self):
		return self.get_center_and_field_count()[0]
	
	def get_center_and_field_count(self):
		xsum = ysum = counter = 0
		for x in range(common.field_size[0]):
			for y in range(common.field_size[1]):
				if self.secured[x][y]:
					xsum += x
					ysum += y
					counter += 1

		if counter > 0:
			self.center = [xsum / counter, ysum / counter]

		return self.center[:], counter

#	def castles():
#		def fset(self):
#			raise NotImplementedError
#		def fget(self):
#			from field import Castle
#			return [castle for castle in Castle.instances if castle.player == self]
#		return locals()
#	castles = property(**castles())
			
	def die(self):
		self.alive = False
		self.handle_event = self.handle_movement = self.draw_cursor = lambda *args:None

#	def remote_call(self, command, *args):
		"""Execute a player action on all Clients
		
		This function gets called on the server whenever a player wishes to execute an action.
		The server tries to execute the action, and sends it to all clients if successful.
		"""
		assert game.server, "remote_call may only be called on the server!"
#		from server import ClientAvatar
#		try:
#			eval('self.phase_player.remote_' + command)(*args)
#			#for client in game.server.clients:
#				#client.remote_players[self.player_id].callRemote(command, *args)
#			#for o in self.observers:
#			#	player.callRemote(command, *args)
#			for ai in game.server.ai_players:
#				from twisted.internet import reactor
#				reactor.callLater(0, lambda: ai.act_on_player_event(command, self))
#			print command, 'succeeded for player', self.player_id
#		except common.ActionNotPossible:
#			if self.ai:
#				from twisted.internet import reactor
#				reactor.callLater(0, lambda: self.ai.failed_event(command))
#			print command, 'failed for player', self.player_id		

	# delegations to phase_player
	def draw_cursor(self, *args, **kwargs):
		self.phase_player.draw_cursor(*args, **kwargs)
	def handle_event(self, *args, **kwargs):
		self.phase_player.handle_event(*args, **kwargs)
	def handle_movement(self, *args, **kwargs):
		self.phase_player.handle_movement(*args, **kwargs)

#	def remote_put_block(self, *args, **kwargs):
#		self.phase_player.remote_put_block(*args, **kwargs)
#	def remote_move(self, *args, **kwargs):
#		self.phase_player.remote_move(*args, **kwargs)
#	def remote_rotate_block(self, *args, **kwargs):
#		self.phase_player.remote_draw_cursor(*args, **kwargs)
#	def remote_generate_block(self, *args, **kwargs):
#		self.phase_player.remote_draw_cursor(*args, **kwargs)
#	def remote_place_cannon(self, *args, **kwargs):
#		self.phase_player.remote_place_cannon(*args, **kwargs)
#	def remote_change_type(self, *args, **kwargs):
#		self.phase_player.remote_change_type(*args, **kwargs)
#	def remote_set_movement(self, *args, **kwargs):
#		self.phase_player.remote_set_movement(*args, **kwargs)
#	def remote_shoot(self, *args, **kwargs):
#		self.phase_player.remote_shoot(*args, **kwargs)
#	def remote_draw_cursor(self, *args, **kwargs):
#		self.phase_player.remote_draw_cursor(*args, **kwargs)
#	def remote_draw_cursor(self, *args, **kwargs):
#		self.phase_player.remote_draw_cursor(*args, **kwargs)

	#def select_castle(self, *args, **kwargs):
	#	self.phase_player.select_castle(*args, **kwargs)


class PlayerCacheable(Player, pb.Cacheable, pb.Referenceable):
	def __init__(self, *args, **kwargs):
		Player.__init__(self, *args, **kwargs)
		self.observers = []
	def getStateToCacheAndObserveFor(self, perspective, observer):
		self.observers.append(observer)
		state = self.__dict__.copy()
		for key in ('observers', 'secured', 'wall_pic', 'ground_pic'):
			del state[key]
		state['local'] = False
		state['remote_ref'] = pb.AsReferenceable(self)
		return state 
	#remoteMessageReceived = pb.Referenceable.remoteMessageReceived(self, *args, **kwargs)
	#def remote_select_castle(self, *args, **kwargs):
	#	self.select_castle(*args, **kwargs)

class PlayerRemoteCache(Player, pb.RemoteCache):
	def __init__(self):
		pass
	def setCopyableState(self, state):
		self.__dict__ = state
		self.secured = zeros(common.field_size)
		self.set_player_id(self._player_id)

		import buildplayer
		import placeplayer
		import battleplayer
		import selectplayer
		#self.build_player = buildplayer.BuildPlayer(self)
		#self.place_player = placeplayer.PlacePlayer(self)
		#self.battle_player = battleplayer.BattlePlayer(self)
		#self.select_player = selectplayer.SelectPlayer(self)
#	def callRemote(self, *args, **kwargs):
#		self.remote_ref.callRemote(*args, **kwargs)

	#def select_castle(self, *args, **kwargs):
	#	self.remote_ref.callRemote('select_castle', *args, **kwargs)

pb.setUnjellyableForClass('player.PlayerCacheable', PlayerRemoteCache)

