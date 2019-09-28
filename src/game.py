import pygame
from pygame.locals import *
from numpy import *
from twisted.spread import pb

import common
from common import Signal

class Game(pb.Referenceable, common.Borg):

	def __init__(self, players, server=None):
		common.Borg.__init__(self)

		if (players == None):
			return
		
		class DummyPhase:
			phase_name = "none"

		global game
		game = self
		self.server = server
		self.number_of_players = len(players)
		self.players = players
		self.phase = DummyPhase()

		# empty instance lists
		self.cannons = []
		self.shots = []
		from field import Grunt
		Grunt.instances = []

		# signals
		self.build_phase_finished = Signal()
		self.place_phase_finished = Signal()
		self.battle_phase_finished = Signal()
		self.select_phase_finished = Signal()
		self.announce_phase_finished = Signal()
		self.unpause_signal = Signal()
	
	def set_map(self, map):
		import field
		self.field = field.Field(map)

	def print_time(self):
		time = int( max(self.phase.time_left, 0) )
		time_surface = common.font.render(str(time), True, (0,0,0))
		common.blit(time_surface, ((common.screen.get_width()-time_surface.get_width())/2, 0) )

	def get_wall(self, pos):
		for i in (0, 1):
			if pos[i] < 0  or pos[i] >= common.field_size[i]:
				return -1
		return self.field[pos[0]][pos[1]]
		
	def server_call(self, command, *args):
		if self.server:
			self.server.call(command, *args)

	def remote_unpause(self):
		self.unpause_signal.emit()

	def remote_pause(self):
		from widget import Button, WidgetState
		class PauseState(WidgetState):
			def __init__(self):
				WidgetState.__init__(self)
				Button("Game paused by host.", (None, None), None)
				if game.server:
					Button("Continue", (None, common.screen.get_height()/2 + 50), lambda: game.server_call('unpause'))
				Button("Quit", (None, common.screen.get_height()/2 + 85), lambda: self.leave_game())

				game.unpause_signal.connect(self.resume)

			def quit(self):
				WidgetState.quit(self)
				game.unpause_signal.disconnect(self.resume)

			def leave_game(self):
				self.quit()
				game.game_state.quit()

			def resume(self):
				self.quit()
					
		PauseState()
		
	def remote_run(self):
		self.run_callback() # usually quits the last state
		common.info("Starting Game")
		self.field.init()
		self.field.draw_backbuffer()
		from config import PlayerConfig
		PlayerConfig.assign()
		from gamephases import AnnouncePhase, SelectPhase, GameState
		self.game_state = GameState()
		self.phase = AnnouncePhase(SelectPhase)
	
	def remote_next_phase(self):
		print("\t-- Next Phase --")
		self.phase.cleanup()
		self.phase.quit()
		getattr(self, self.phase.phase_name + '_phase_finished').emit() # fire signal
	
	def remote_new_house(self, pos):
		from field import Field
		if self.field[pos] == Field.EMPTY:
			for pl in self.players:
				if pl.secured[pos]:
					raise common.ActionNotPossible
			self.field[pos] = Field.HOUSE
			common.backbuffer_blit(Field.obstacle_pic[Field.HOUSE], multiply(pos, common.block_size))
		else:
			raise common.ActionNotPossible

	def remote_create_grunt(self, pos):
		from field import Grunt
		Grunt(pos)
	
	def remote_move_grunt(self, id, new_pos):
		from field import Grunt
		grunt = [g for g in Grunt.instances if g.id == id][0]
		grunt.move(new_pos)
	
	def remote_rotate_grunt(self, id, new_dir):
		from field import Grunt
		grunt = [g for g in Grunt.instances if g.id == id][0]
		grunt.rotate(new_dir)
	
	def remote_hit(self, pos, cannon_id=-1):
		from field import Field, Grunt
		if cannon_id >= 0:
			cannon = [can for can in game.cannons if can.id == cannon_id][0]
			cannon.in_use = False
		else:
			# hit was caused by grunt
			cannon = None
		# damage target
		target = game.field[pos]
		if target == Field.CANNON:
			for can in game.cannons:
				for offset in common.coords((can.size,)*2):
					if list(pos) == list(add(can.pos, offset)):
						can.hit()
		elif target >= 0 or target in (Field.HOUSE, Field.GRUNT):
			# change field
			if not cannon or cannon.type == 0:
				game.field[pos] = Field.EMPTY
			else:
				game.field[pos] = Field.GARBAGE_NEW
			# recalculate the owner's secured territory if a wall was hit
			if target >= 0:
				player = game.players[target]
				game.field.look_for_secured_areas(player, pos)
			elif target == Field.GRUNT:
				defeated_grunt = [g for g in Grunt.instances if list(g.pos) == list(pos)][0]
				Grunt.instances.remove(defeated_grunt)
			game.field.blit_field(pos)
		else:
			raise common.ActionIrrelevant

game = Game(None, None)
		

