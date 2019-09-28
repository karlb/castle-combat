from random import randint
import numpy as np
from numpy import *
from twisted.spread import pb
from twisted.internet import reactor

import common
from game import game
from field import Field, Grunt, Castle

class Map(pb.Copyable, pb.RemoteCopy):
	game_options = ()
	build_phase_text = (
		"Repair your walls!",
		"Enclose at least one castle to survive.",
		"Place block / Rotate Block"
	)
	place_phase_text = (
		"Place your cannons!",
		"Position new cannons inside your walls.",
		"Place cannon / Select cannon"
	)
	battle_phase_text = (
		"Shoot at your enemy's walls!",
		"You can also destroy the cannons.",
		"Shoot / Accelerate movement"
	)
	select_phase_text = (
		"Select your Castle!",
		"Choose one castle to be your home castle.",
		"Select Castle / No Action"
	)

	def __init__(self, options):
		pass

	def setup(self):
		self.castles = []
		self.houses = 0
		self.array = zeros(common.field_size, dtype=np.uint8) + Field.EMPTY
	
	def apply(self):
		if 'land_owners' in self.game_options:
			self.set_land_owners()

		game.field.array = self.array
		# The callLater makes sure that the field is initialized on the
		# clients when the houses are added. As a downside, this makes
		# the houses appear only after pressing the button to start the
		# game. TODO: remove this ugly hack and find a proper solution!
		reactor.callLater(0,
			lambda: game.field.add_houses(self.houses)
		)
		self.add_end_test()

		#from field import Castle
		#for castle in self.castles:
		#	Castle(castle['pos'], castle['player'])

		if hasattr(self, 'background_image'):
			game.field.surface = common.load_image(self.background_image)
		else:
			game.field.create_background()

	def set_land_owners(self):
		game.field.owner = where(self.array == Field.RIVER, -1, -2)
		for player in game.players:
			print("setting land for player", player)
			castle = [castle for castle in self.castles if castle.player is player][0]
			common.flood_fill(game.field.owner, castle.pos, -2, player.player_id)
	
	def add_end_test(self):
		def standard_end_test():
			alive = [player for player in game.players if player.alive]
			print("end test %d" % len(alive))
			if len(alive) > 1:			
				return
			if len(alive) == 0:
				string = "Draw game!"
			else:
				string = "%s wins!" % alive[0].name
			print("game end")
			
			from widget import Button, WidgetState
			class EndState(WidgetState):
				def __init__(self):
					WidgetState.__init__(self)
					Button(string, (None, None), None)
					Button("OK", (None, common.screen.get_height()/2 + 50), self.quit)

				def quit(self):
					WidgetState.quit(self)
					game.game_state.quit()
					from state import IgnoreEvent
					raise IgnoreEvent
					
			EndState()
		
		game.build_phase_finished.connect(standard_end_test)

	def getStateToCopy(self):
		state = self.__dict__.copy()
		state['array'] = state['array'].tolist()
		return state
	
	def setCopyableState(self, state):
		state['array'] = array(state['array'])
		self.__dict__ = state


##### Custom Maps #####
		
class GruntAssault(Map):

	title = 'Grunt Assault'
	allowed_players = (1,)
	background_image = 'back-noriver.jpg'

	def __init__(self, options):
		Map.__init__(self, options)
		self.difficulty = options['difficulty']
		self.difficulty_number = dict(
			very_easy = -20,
			easy = -10,
			medium = 0,
			hard = 10,
			very_hard = 20,
		)[self.difficulty]

	def setup(self):
		Map.setup(self)
		self.houses = 100 + self.difficulty_number
		self.castles = [
			Castle(pos=(3 + randint(0, 7) + i * 11, randint(3, 25)), player=None, map=self)
			for i in (0,1,2)
		]
		self.reinforcement_grunts_left = 150 + self.difficulty_number;
		def send_reinforcements():
			new_grunts = self.reinforcement_grunts_left // 10;
			self.reinforcement_grunts_left -= new_grunts
			self.add_grunts(new_grunts)
		game.build_phase_finished.connect(send_reinforcements, priority=-10)
		self.battle_phase_text = (
			"Eleminate all attackers!",
			"",
			"Shoot / Accelerate movement"
		)
	
	def apply(self):
		Map.apply(self)
		self.add_grunts(10)

	def add_end_test(self):
		def win_test():
			from widget import Button, WidgetState
			class EndState(WidgetState):
				def __init__(self):
					WidgetState.__init__(self)
					Button('Castle successfully defended!', (None, None), None)
					Button("OK", (None, common.screen.get_height()/2 + 50), self.quit)

				def quit(self):
					WidgetState.quit(self)
					game.game_state.quit()
					from state import IgnoreEvent
					raise IgnoreEvent

			from field import Grunt
			if not Grunt.instances:
				EndState()
	
		def lost_test():
			from widget import Button, WidgetState
			class EndState(WidgetState):
				def __init__(self):
					WidgetState.__init__(self)
					Button('Your last castle has fallen!', (None, None), None)
					Button("OK", (None, common.screen.get_height()/2 + 50), self.quit)

				def quit(self):
					WidgetState.quit(self)
					game.game_state.quit()
					from state import IgnoreEvent
					raise IgnoreEvent

			if not game.players[0].alive:
				EndState()

		game.battle_phase_finished.connect(win_test)
		game.build_phase_finished.connect(win_test)
		game.build_phase_finished.connect(lost_test)
	
	def add_grunts(self, amount):
		player = game.players[0]
		while amount > 0:
			pos = tuple(randint(0, max-1) for max in common.field_size)
			if game.field[pos] == Field.EMPTY and not player.secured[pos]:
				Grunt(pos)
				amount -= 1
			else:
				amount -= 0.1


class RiverMap(Map):

	title = 'River'
	game_options = ('land_owners', )

	def setup(self):
		Map.setup(self)
		self.houses = 20


class RiverMap2p(RiverMap):

	allowed_players = (2, )
	background_image = 'back-river.jpg'

	def setup(self):
		RiverMap.setup(self)
		for y in range(common.field_size[1]):
			self.array[(common.field_size[0]//2 - 1):(common.field_size[0]//2 + 1), y] = Field.RIVER

		for i in (0, 1, 2):
			self.castles += [
				Castle(pos=(8 + randint(-2,2), (i+1) * 8 - 2 + randint(-1,1)), player=game.players[0], map=self),
				Castle(pos=(30 + randint(-2,2), (i+1) * 8 - 2 + randint(-1,1)), player=game.players[1], map=self),
			]

class RiverMap4p(RiverMap):

	allowed_players = (3, 4)
	background_image = 'back-river4.jpg'
	
	def setup(self):
		RiverMap.setup(self)

		for y in range(common.field_size[1]):
			self.array[(common.field_size[0]/2 - 1):(common.field_size[0]/2 + 1), y] = Field.RIVER
		for x in range(common.field_size[0]):
			self.array[x, (common.field_size[1]/2 - 1):(common.field_size[1]/2 + 1)] = Field.RIVER
		for i in (0, 1):
			self.castles += [
				Castle((5 + randint(-1,1) + i*8, 6 + randint(-1,1)), player=game.players[0], map=self),
				Castle((25 + randint(-1,1) + i*8, 6 + randint(-1,1)), player=game.players[1], map=self),
			]
			if game.number_of_players >= 3:
				self.castles += [Castle((5 + randint(-1,1) + i*8, 21 + randint(-1,1)), player=game.players[2], map=self)]
			if game.number_of_players >= 4:
				self.castles += [Castle((25 + randint(-1,1) + i*8, 21 + randint(-1,1)), player=game.players[3], map=self)]


class ConquerMap(Map):

	title = 'Conquer'
	game_options = ('build_only_near_walls', )
	allowed_players = (2, 3, 4)
	background_image = 'back-noriver.jpg'

	def setup(self):
		Map.setup(self)
		self.houses = 20

		def place_castle():
			def is_place_suitable(pos):
				# would the walls be inside the field?
				for i in (0,1):
					if pos[i] not in list(range(3, common.field_size[i]-4)):
						return False

				# enough free room?
				#topleft = common.in_bounds(subtract(pos, 3))
				#bottomright = common.in_bounds(add(pos, 5))
				#surroundings = self.array[topleft[0]:bottomright[0], topleft[1]:bottomright[1]]
				#if sometrue(surroundings != Field.EMPTY):
				#	return False

				# far enough away from other castles
				topleft = common.in_bounds(subtract(pos, 6))
				bottomright = common.in_bounds(add(pos, 8))
				surroundings = self.array[topleft[0]:bottomright[0], topleft[1]:bottomright[1]]
				if sometrue(surroundings == Field.CASTLE):
					return False
				else:
					return True

			while True:
				pos = tuple(randint(0,common.field_size[i]) for i in (0,1))
				if is_place_suitable(pos):
					self.castles += [ Castle(pos=pos, player=None, map=self), ]
					return

		for i in range(5):
			place_castle()


#	def apply(self):
#		Map.apply(self)


##### Map List #####

maps = (GruntAssault, RiverMap2p, RiverMap4p, ConquerMap)

# does not work. I don't know why.
#import sys
#from twisted.spread.jelly import setUnjellyableForClassTree
#setUnjellyableForClassTree(module=sys.modules[__name__], baseClass=Map, prefix="")

for m in maps:
	pb.setUnjellyableForClass(m, m)

