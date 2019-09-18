import pygame
from pygame.locals import *
from Numeric import *

import common
from game import game
from state import State, IgnoreEvent

class GameState(State):

	def handle_keypress(self, event):
		if common.debug and event.type == KEYDOWN:
			if event.key == K_BACKSPACE:
				game.server_call('next_phase')	
				raise IgnoreEvent
			if event.key == K_EQUALS:
				try:
					import cannon
					reload(cannon)
					print "reload successful"
				except:
					print "WARNING: Module reload failed!"
					import traceback
					traceback.print_exc() 

	def handle(self):
		game.phase = game.phase.next_phase()
	
	def quit(self):
		# allow GameState to quit event if it's not the topmost state
		while State.stack[-1] != self:
			State.stack[-1].quit()
		State.quit(self)
		if game.server:
			game.server.quit()

	persistent_events = {
		KEYDOWN: handle_keypress,
	}


class Phase(State):

	def __init__(self):
		State.__init__(self)
		for player in game.players:
			player.init_phase(self.phase_name)

		self.time_left = self.duration
		self.clock = pygame.time.Clock()
		self.clock.tick()

	def handle(self):
		if self.phase_end():
			game.server_call('next_phase')	
		else:
			passed_milliseconds = min(self.clock.tick(), 500)
			# handle redraws and other actions that occur each frame
			self.actions(passed_milliseconds)
 			for player in game.players:
				player.handle_movement(passed_milliseconds)
				player.draw_cursor()
			self.time_left -= passed_milliseconds * 0.001
			game.print_time()
			common.update()
	
	def handle_keypress(self, event):
		if event.type == KEYDOWN:
			if event.key == K_ESCAPE:
				if game.server:
					game.server.call('pause')	
				else:
					game.server_game.callRemote('pause')
				raise IgnoreEvent
		for player in game.players:
			if player.local:
				player.handle_event(event)

	events = {
		KEYDOWN: handle_keypress,
		KEYUP: handle_keypress,
	}
		
class AnnouncePhase(State):
	"""Shows the 'Phase X begins' messages"""

	box_pic = common.load_image('box.png', alpha=True)
	phase_name = 'announce'

	def __init__(self, next_phase):
		State.__init__(self)
		announce_text = getattr(game.field.map, next_phase.phase_name + "_phase_text")
		self.make_announce_surface(*announce_text)
		common.blit(
			self.announce_surface, 
			divide(
				subtract(common.screen.get_size(), self.announce_surface.get_size()),
				2
			)
		)
		common.update()
		self.start_time = pygame.time.get_ticks()
		self.next_phase = next_phase
	
	def proceed_if_waited_long_enough(self, event):
		if pygame.time.get_ticks() > self.start_time + 500:
			game.server_call('next_phase')	
			raise IgnoreEvent

	events = {
		KEYDOWN: proceed_if_waited_long_enough,
	}

	def cleanup(self):
		pass
	
	def make_announce_surface(self, title, instructions, buttons):
		self.announce_surface = self.box_pic.convert_alpha()
		title_pic = common.font.render(title, True, (0,0,0))
		instructions_pic = common.small_font.render(instructions, True, (0,0,0))
		buttons_pic = common.small_font.render("Buttons: " + buttons, True, (0,0,0))
		if game.server:
			continue_string = "< Press any button to continue >"
		else:
			continue_string = "< Waiting for Server to continue >"
		continue_pic = common.small_font.render(continue_string, True, (0,0,0))
		self.announce_surface.blit(
				title_pic,
				((self.announce_surface.get_width() - title_pic.get_width()) / 2, 15)
		)
		self.announce_surface.blit(instructions_pic, (30, 65))
		self.announce_surface.blit(buttons_pic, (30, 90))
		self.announce_surface.blit(
				continue_pic,
				((self.announce_surface.get_width() - continue_pic.get_width()) / 2, 160)
		)
	
class BuildPhase(Phase):

	phase_name = "build"
	duration = 18
	
	def __init__(self):

		def build_actions(passed_milliseconds):
			pygame.time.delay(1)

		pygame.time.set_timer(USEREVENT, 500)
		self.actions = build_actions
		self.next_phase = lambda: AnnouncePhase(PlacePhase)
		Phase.__init__(self)

	def phase_end(self):
		return self.time_left <= 0
	
	def cleanup(self):
		def clean_walls():
			from field import Field
			for player in game.players:
				player_id = player.player_id
				field = game.field.array

				# count how many walls are adjecent to each wall
				adj_walls = zeros(common.field_size)
				adj_walls[1:, :] += where(field[:-1 ,:] == player_id, 1, 0)
				adj_walls[:-1, :] += where(field[1: ,:] == player_id, 1, 0)
				adj_walls[:, 1:] += where(field[:, :-1] == player_id, 1, 0)
				adj_walls[:, :-1] += where(field[:, 1:] == player_id, 1, 0)
				
				# delete all lonely walls
				mask = logical_and(where(adj_walls == 0, 1, 0), where(field == player_id, 1, 0))
				putmask(field, mask, (Field.EMPTY, ))

				# delete every fourth wall with only one adjacent wall
				mask = logical_and(where(adj_walls == 1, 1, 0), where(field == player_id, 1, 0))
				putmask(field, mask, (Field.EMPTY, ) + (player_id, )*3 )

				game.field.look_for_secured_areas(player)
			game.field.draw_backbuffer()
			
		clean_walls()
		game.field.add_houses(5)
		pygame.time.set_timer(USEREVENT, 0)

		# eleminate players
		from field import Castle
		for player in game.players:
			if not [castle for castle in game.field.map.castles if player.secured[castle.pos]]:
				player.die()


class PlacePhase(Phase):

	phase_name = "place"
	duration = 15

	def __init__(self):

		def place_actions(passed_milliseconds):
			pygame.time.delay(1)
	
		pygame.time.set_timer(USEREVENT, 500)
		self.actions = place_actions
		self.next_phase = lambda: AnnouncePhase(BattlePhase)
		Phase.__init__(self)
		
	def phase_end(self):
		return self.time_left <= 0 or not filter(lambda player: player.place_player.new_cannons > 0, game.players)

	def cleanup(self):
		pygame.time.set_timer(USEREVENT, 0)


class BattlePhase(Phase):

	phase_name = "battle"
	duration = 10

	def __init__(self):

		def battle_actions(passed_milliseconds):
			from cannon import Shot
			for can in game.cannons:
				can.blit()
			for shot in game.shots:
				shot.handle(passed_milliseconds)
				shot.draw()
			from field import Grunt
			for grunt in Grunt.instances:
				grunt.handle(passed_milliseconds)

		def remove_garbage():
			from field import Field
			game.field.array += logical_and (
					where(game.field.array >= Field.GARBAGE_NEW, 1, 0),
					where(game.field.array <= Field.GARBAGE_OLD, 1, 0)
			)
			
		self.actions = battle_actions
		self.next_phase = lambda: AnnouncePhase(BuildPhase)
		remove_garbage()
		self.announce_surface = common.font.render("Shoot at your enemy's walls!", True, (0,0,0))
		Phase.__init__(self)
		game.field.draw_backbuffer(draw_cannons=False)
		
	def phase_end(self):
		from cannon import Shot
		return self.time_left <= 0 and not game.shots

	def cleanup(self):
		game.field.draw_backbuffer()


class SelectPhase(Phase):

	phase_name = "select"
	duration = 20

	def __init__(self):

		def select_actions(passed_milliseconds):
			pygame.time.delay(1)

		self.actions = select_actions
		self.next_phase = lambda: AnnouncePhase(PlacePhase)
		Phase.__init__(self)
		
	def phase_end(self):
		return self.time_left <= 0 or not filter(lambda player: not player.select_player.finished, game.players)

	def cleanup(self):
		for player in game.players:
			if not player.select_player.finished:
				player.select_player.remote_confirm_select()


