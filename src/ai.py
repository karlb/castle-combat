from numpy import *
from game import game

class BaseAI:
	def __init__(self, player_id):
		self.player = game.players[player_id]

	def act_on_game_event(self, event_name):
		#print 'AI: I received game event "%s"' % event_name
		self.execute_handler(self.game_event_handler, event_name)

	def act_on_player_event(self, event_name, player):
		if player is self.player:
			# print 'AI: I caused the event "%s"' % event_name
			self.execute_handler(self.player_event_handler, event_name)
		else:
			# print 'AI: Player %d caused the event "%s"' % (player.player_id, event_name)
			pass

	def failed_event(self, event_name):
		# print 'AI: I failed to execute action: "%s"' % event_name
		self.execute_handler(self.failed_event_handler, event_name)
	
	def execute_handler(self, handler_hash, event_name):
		try:
			handler = handler_hash[game.phase.phase_name + '/' + event_name]
		except KeyError:
			pass
		else:
			for h in handler:
				h()
	
	def call(self, command, *args):
		self.player.remote_call(command, *args)


class TestAI(BaseAI):

	def __init__(self, player_id):
		BaseAI.__init__(self, player_id)
		self.player_event_handler = {
			'place/move' : (self.move_randomly, lambda: self.call('place_cannon'))
		}
		self.failed_event_handler = {
			'place/move' : (self.move_home, )
		}
		self.game_event_handler = {
			'select/next_phase' : (lambda: self.call("confirm_select"), ),
			'place/next_phase' : (self.move_randomly, )
		}

	def move_randomly(self):
		if self.player.phase_player.new_cannons == 0:
			# stop moving when I won't be able to place a cannon anyway
			return
		import random
		self.call('move', [random.randint(-1, 1) for i in (0,1)])
	
	def move_home(self):
		self.call('move', subtract(self.player.center, self.player.phase_player.pos))
		
	
DefaultAI = TestAI

