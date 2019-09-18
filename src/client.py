from twisted.internet import reactor
from twisted.spread import pb
from twisted.cred.credentials import Anonymous, UsernamePassword
from widget import WidgetState

# import to allow unjellying
import player
import selectplayer
import placeplayer
import buildplayer
import battleplayer
import map

class WaitForSeverState(WidgetState):
	def __init__(self):
		from widget import Label
		WidgetState.__init__(self)
		Label("Connecting to server", (None, None))

class ClientMind(pb.Referenceable):

	def __init__(self, client):
		self.client = client 
	
	def remote_get_client_info(self):
		info = {
			'game': self.client.game,
			#'players': self.client.game.players,
		}
		return info


class ClientFactory(pb.PBClientFactory):

	def clientConnectionLost(self, connector, reason, reconnecting=0):
		print "Connection to server lost: %s" % reason
		self.client.game.game_state.quit()

class Client:

	def __init__(self, server_name):
		self.server_name = server_name
	
	def run(self, local_players):
		self.local_players = local_players

		self.wait_for_server_state = WaitForSeverState()

		factory = ClientFactory()
		factory.client = self
		reactor.connectTCP(self.server_name , pb.portno, factory)
		#factory.login(Anonymous()).addCallbacks(connected, failure)
		d = factory.login(UsernamePassword("guest", "guest"), ClientMind(self))
		d.addCallbacks(self.connected_callback, self.failure_callback)

	##### callbacks

	def connected_callback(self, perspective):
		print "connected."
		self.perspective = perspective
		d = self.perspective.callRemote('get_server_info')
		d.addCallback(self.get_server_info_callback)
		d.addCallback(self.claim_players_as_local_callback)
		d.addCallback(self.send_ready_callback)

	def send_ready_callback(self, dummy):
		self.perspective.callRemote('client_ready')

	def failure_callback(self, error):
		print "login failure:", error

	def get_server_info_callback(self, info):
		import game
		self.game = game.Game(info['players'])
		self.game.server_game = info['server_game']
		self.game.set_map(info['map'])
		self.game.run_callback = self.wait_for_server_state.quit

	def claim_players_as_local_callback(self, dummy):
		
		def player_claimed(player):
			player.local = True
			print "got player %d!" % player.player_id

		for i in range(self.local_players):
			d = self.perspective.callRemote('claim_player_as_local')
			d.addCallback(lambda *args: player_claimed(*args))


