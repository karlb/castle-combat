from twisted.spread import pb
from twisted.cred.portal import IRealm
from twisted.internet import reactor, defer
from widget import WidgetState
import common

class WaitForPlayersState(WidgetState):
	def __init__(self):
		from widget import Label
		WidgetState.__init__(self)
		Label("Waiting for Players to join", (None, None))

class GamePerspectiveForClient(pb.Referenceable):
	'''Contains all methods related to the Game class, which can be called from the clients
	'''

	def __init__(self, server):
		self.server = server

	def remote_pause(self):
		self.server.call('pause')

	def remote_unpause(self):
		self.server.call('unpause')

class ClientAvatar(pb.Avatar):
	'''This class contains all functions which can be called by the client.

	   There is exacty one instance of this class per connected client.
	'''

	def __init__(self, server, mind):
		self.server = server
		self.mind = mind
		self.ready = False
		print "One client connected. Total: %d" % len(self.server.clients)
		
	##### callbacks

	def logout_callback(self):
		print self, "logged out"
		self.server.clients.remove(self)

		# quit game_state if it didn't quit already
		game_state = self.server.game.game_state
		if game_state in game_state.stack:
			game_state.quit()
		
	##### remote functions
	
	def perspective_claim_player_as_local(self):
		return self.server.claim_player_as_local()
	
	def perspective_get_server_info(self):
		game = self.server.game
		from player import PlayerCacheable
		info = {
			'players': game.players,
			'map': game.field.map,
			'server_game': GamePerspectiveForClient(self.server)
		}
		return info

	def perspective_client_ready(self):
		'''Gets called when the client has been fully initialised'''
		
		def get_client_info_callback(info):
			'''Finishes integration of this client into the game'''
			self.remote_game = info['game']
			#self.remote_players = info['players']
			self.ready = True
			self.server.start_game_if_ready()

		d = self.mind.callRemote('get_client_info')
		d.addCallback(get_client_info_callback)
		

class RequestClientRealm:
	__implements__ = IRealm
	
	def __init__(self, server):
		self.server = server

	def requestAvatar(self, avatarId, mind, *interfaces):
		if pb.IPerspective in interfaces:
			avatar = ClientAvatar(self.server, mind)
			self.server.clients.append(avatar)
			return pb.IPerspective, avatar, avatar.logout_callback 
		else:
			raise NotImplementedError("no interface")

class Server:

	clients = []

	def __init__(self, map, total_players):
		import player
		players = [player.PlayerCacheable(i) for i in range(total_players)]
		import game
		self.game = game.Game(players=players, server=self)
		map.setup()
		self.game.set_map(map)
		self.ai_players = []

		from twisted.cred.portal import Portal
		from twisted.cred.checkers import AllowAnonymousAccess, InMemoryUsernamePasswordDatabaseDontUse
		portal = Portal(RequestClientRealm(self))
		checker = InMemoryUsernamePasswordDatabaseDontUse()
		checker.addUser("guest", "guest")
	#	checker = AllowAnonymousAccess()
		portal.registerChecker(checker)
		self.listening_port = reactor.listenTCP(pb.portno, pb.PBServerFactory(portal))

	def call(self, command, *args):
		try:
			eval('self.game.remote_'+command)(*args)
		except common.ActionNotPossible:
			print command, 'was not possible'
			return

                dl = defer.DeferredList([
                    client.remote_game.callRemote(command, *args)
                    for client in self.clients
                ])
		for ai in self.ai_players:
			ai.act_on_game_event(command)
                return dl
		

	def claim_player_as_local(self):
		for player in self.game.players:
			if not player.connected:
				player.connected = True
				self.start_game_if_ready()
				#return player.player_id, player
				return player
		assert False, "All player slots are already occupied"

	def start_game_if_ready(self):
		all_clients_ready = False not in [client.ready for client in self.clients]
		all_players_connected = False not in [player.connected for player in self.game.players]
		if all_players_connected and all_clients_ready:
			print "Stopping to listen"
			self.listening_port.stopListening()
			reactor.callLater(0, lambda: self.game.server_call("run"))
		
	
	def run(self, local_players, ai_players):
		self.wait_for_players_state = WaitForPlayersState()
		self.game.run_callback = self.wait_for_players_state.quit

		for i in range(local_players):
			#(player_id, avatar) = self.get_player()
			#self.game.players[player_id].local = True
			player = self.claim_player_as_local()
			player.local = True

		for i in range(ai_players):
			import ai
			(player_id, avatar) = self.claim_player_as_local()
			self.game.players[player_id].local = True
			newai = ai.DefaultAI(player_id)
			self.game.players[player_id].ai = newai
			self.ai_players.append(newai)

	def quit(self):
		print "Disconnecting all clients"
		for client in self.clients:
			client.mind.broker.transport.loseConnection()
		self.listening_port.stopListening()
	
