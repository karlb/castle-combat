import pygame
from pygame.locals import *

from widget import *
import common
import sound
from config import conf, PlayerConfig

menu_back = common.load_image('back.png')

def draw_background():
	common.backbuffer = menu_back.convert()
	common.blit(common.backbuffer)

class NewGameState(WidgetState):

	def __init__(self):
		WidgetState.__init__(self)

		def start_game(total_players, local_players, ai_players):
			import server
			options = dict(
					difficulty = self.difficulty.value.lower().replace(' ', '_')
			)
			ser = server.Server(self.selected_map(options), total_players)
			ser.run(local_players, ai_players)

		def on_total_change():
			self.local_players.value = min(self.local_players.value, self.total_players.value)
			self.local_players.choices = range(self.total_players.value, 0, -1)
			from map import maps
			self.map.choices = [m.title for m in maps if self.total_players.value in m.allowed_players]
			on_map_change()

		def on_map_change():
			from map import maps, GruntAssault
			self.selected_map = [m for m in maps if m.title == self.map.value and self.total_players.value in m.allowed_players][0]
			if self.selected_map == GruntAssault:
				self.difficulty.hidden = False
			else:
				self.difficulty.hidden = True

		Button("back", (50, -20), self.quit)
		self.total_players = SpinBox("Total Players", (50, 360), (4,3,2,1), default=conf.total_players, on_change=on_total_change)
		self.local_players = SpinBox("Local Players", (50, 400), (4,3,2,1), default=conf.local_players)
		if common.debug:
			self.ai_players = SpinBox("AI Players", (50, 440), (2,1,0), conf.ai_players)
			Button("Start Game", (None, 250), lambda: start_game(self.total_players.value, self.local_players.value, self.ai_players.value))
		else:
			Button("Start Game", (None, 250), lambda: start_game(self.total_players.value, self.local_players.value, 0))
			
		self.map = SpinBox('Map', (500, 360), ('dummy',), on_change=on_map_change)
		self.difficulty = SpinBox('Difficulty', (500, 400), ('Very Easy', 'Easy', 'Medium', 'Hard', 'Very Hard'))

		on_total_change()

	def init_state_display(self):
		draw_background()
	
	def quit(self):
		WidgetState.quit(self)
		# save changes in config
		conf.total_players = self.total_players.value
		conf.local_players = self.local_players.value
		if common.debug:
			conf.ai_players = self.ai_players.value

class JoinGameState(WidgetState):

	def __init__(self):
		WidgetState.__init__(self);
		def join(server, local_players):
			import client
			cl = client.Client(server)
			cl.run(local_players)

		Button("back", (50, -20), self.quit)
		self.server = LineEdit("Server", (50, 360), conf.server)
		self.local_players = SpinBox("Local Players", (50, 400), (2,1))
		Button("Join Game", (None, 250), lambda: join(self.server.value, self.local_players.value) )

	def init_state_display(self):
		draw_background()

	def quit(self):
		WidgetState.quit(self)
		# save changes in config
		conf.server = self.server.value

class ConfigState(WidgetState):

	def __init__(self):
		WidgetState.__init__(self)
		top = 225
		line_height = 40
		(self.up, self.down, self.left, self.right) = ([0, 0], [0, 0], [0, 0], [0, 0])
		self.button = [[0, 0], [0, 0]]
		for i in (0,1):
			keys = PlayerConfig.instances[i].keys
			self.up[i] = [keys.up]
			self.down[i] = [keys.down]
			self.left[i] = [keys.left]
			self.right[i] = [keys.right]
			self.button[i][0] = [keys.button[0]]
			self.button[i][1] = [keys.button[1]]
			Button("Player " + str(i+1), (50 + i*500, top), None)
			KeyConfigButton("Up", (50 + i*500, top + line_height), self.up[i])
			KeyConfigButton("Down", (50 + i*500, top + line_height*2), self.down[i])
			KeyConfigButton("Left", (50 + i*500, top + line_height*3), self.left[i])
			KeyConfigButton("Right", (50 + i*500, top + line_height*4), self.right[i])
			KeyConfigButton("Button 1", (50 + i*500, top + line_height*5), self.button[i][0])
			KeyConfigButton("Button 2", (50 + i*500, top + line_height*6), self.button[i][1])

		Button("back", (50, -20), self.quit)

		def sound_change():
			if self.sound.value == 'On':
				sound.sound_on()
			else:
				sound.sound_off()
		bool_to_on_off = {True:'On', False:'Off'}
		self.sound = SpinBox("Sound", (350, -20), ("On", "Off"), default=bool_to_on_off[conf.sound], on_change=sound_change)
		self.fullscreen = SpinBox("Fullscreen", (500, -20), ("On", "Off"), default=bool_to_on_off[conf.fullscreen])

	def quit(self):
		for i in (0,1):
			keys = PlayerConfig.instances[i].keys
			keys.up = self.up[i][0]
			keys.down = self.down[i][0]
			keys.left = self.left[i][0]
			keys.right = self.right[i][0]
			keys.button[0] = self.button[i][0][0]
			keys.button[1] = self.button[i][1][0]
		is_on = {'On': True, 'Off':False}
		conf.fullscreen = is_on[self.fullscreen.value]
		conf.sound = is_on[self.sound.value]
		WidgetState.quit(self)

class MenuState(WidgetState):

	def __init__(self):
		WidgetState.__init__(self)
		def help():
			from webbrowser import open
			from os.path import abspath
			file = "file://" + abspath("data/doc/rules.html")
			print file
			open(file, new=True)

		draw_background()
		Button("Start New Game", (25, 360), NewGameState)
		Button("Join Existing Game", (25, 400), JoinGameState)
		Button("Quit", (25, -20), self.quit)
		Button("Help", (-25, -20), help)
		Button("Options", (-25, -60), ConfigState)



