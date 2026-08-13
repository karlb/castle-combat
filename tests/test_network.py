"""Drive a real client connection against a real server

The playthrough tests only ever run the server half. No client connects there,
so Server.clients and every ServerObject's observer list stay empty, both
callRemote() loops iterate over nothing and not a single object is ever
serialised. These tests open an actual perspective broker connection to the
listening port, which is what puts the login, the cacheable state transfer and
the observer bookkeeping under test.

The real Client class cannot take part in those: Game is a Borg, so building a
client side Game alongside the server's would overwrite it. A recording stand-in
plays the client there. The handshake in client.py is covered separately at the
bottom of this file, by a test with no server in the process for it to clash
with, since that handshake is where "no client could join at all" hid before.
"""

import pytest
from twisted.cred.credentials import UsernamePassword
from twisted.internet import reactor
from twisted.python.failure import Failure
from twisted.spread import pb

from castle_combat import menu
from castle_combat.map import ConquerMap
from castle_combat.player import PlayerRemoteCache
from castle_combat.state import MainState


def spin(deferred, limit=500):
    """Run the reactor until the deferred fires and give back its result"""
    outcome = []
    deferred.addBoth(outcome.append)
    for _ in range(limit):
        if outcome:
            break
        reactor.iterate(0.01)
    else:
        raise AssertionError("the deferred never fired")
    if isinstance(outcome[0], Failure):
        outcome[0].raiseException()
    return outcome[0]


def settle(rounds=20):
    """Give the reactor room to deliver whatever is in flight"""
    for _ in range(rounds):
        reactor.iterate(0.01)


class RecordingGame(pb.Referenceable):
    """Stands in for the client's Game and notes what the server forwards

    Server.call() reaches the clients through client.remote_game.callRemote(),
    so every command the server broadcasts lands here as a remote_ lookup.
    """

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if not name.startswith("remote_"):
            raise AttributeError(name)
        command = name[len("remote_") :]
        return lambda *args, **kwargs: self.calls.append(command)


class RecordingMind(pb.Referenceable):
    def __init__(self):
        self.game = RecordingGame()

    def remote_get_client_info(self):
        return {"game": self.game}


@pytest.fixture
def connection():
    """A listening server with one local player and one logged in client"""
    from castle_combat.server import Server

    MainState()
    # the menu leaves a backbuffer behind, which the game draws on when it
    # starts up
    menu.MenuState()
    server = Server(ConquerMap(dict(difficulty="medium")), 2)
    connector = None
    # the port has to come back even when the handshake below fails, or every
    # later test in the file dies binding an address that is still in use
    try:
        # player 0 is the human at this machine, player 1 is left for the client
        server.run(1, 0)

        factory = pb.PBClientFactory()
        # a literal address, because resolving a name would need the reactor's
        # thread pool and these tests only ever iterate the reactor by hand
        connector = reactor.connectTCP("127.0.0.1", pb.portno, factory)
        mind = RecordingMind()
        perspective = spin(factory.login(UsernamePassword(b"guest", b"guest"), mind))

        yield server, perspective, mind
    finally:
        if connector is not None:
            connector.disconnect()
        settle()
        # start_game_if_ready() closes the port itself once everyone is in
        if server.listening_port.connected:
            server.listening_port.stopListening()
        settle()


def test_logging_in_gets_the_client_an_avatar(connection):
    server, _perspective, _mind = connection

    assert len(server.clients) == 1
    assert server.clients[0].mind is not None


def test_the_server_info_carries_the_players_and_the_map(connection):
    server, perspective, _mind = connection

    info = spin(perspective.callRemote("get_server_info"))

    # the players arrive as remote caches, rebuilt from the state the
    # cacheables handed over rather than as the server's own objects
    assert [type(p) for p in info["players"]] == [PlayerRemoteCache] * 2
    assert [p.player_id for p in info["players"]] == [0, 1]
    assert [p.name for p in info["players"]] == [p.name for p in server.game.players]
    assert info["map"].__class__.__name__.endswith("Map")


def test_claiming_a_player_transfers_its_state(connection):
    server, perspective, _mind = connection

    player = spin(perspective.callRemote("claim_player_as_local"))

    # player 0 was taken by the local human, so the client gets player 1
    assert player.player_id == 1
    assert player.name == server.game.players[1].name
    assert server.game.players[1].connected
    # the pictures are dropped from the state and rebuilt on arrival, and
    # local is deliberately sent as False
    assert player.local is False
    assert player.wall_pic is not None


def test_the_server_forwards_its_commands_to_the_client(connection):
    server, perspective, mind = connection

    spin(perspective.callRemote("claim_player_as_local"))
    spin(perspective.callRemote("client_ready"))
    settle()

    # both players are in and the client said it was ready, so the server
    # stops listening and broadcasts the start of the game
    assert server.clients[0].ready
    assert "run" in mind.game.calls


def test_a_client_leaving_eliminates_its_players_and_leaves_the_game_running(
    connection,
):
    """Losing one connection used to end the game for everyone still playing

    logout_callback() quit the server's game_state outright, so whoever was
    left at their keyboard was thrown back to the menu because somebody else's
    wifi blinked. The players that client held are eliminated instead, which is
    a state the game already knows how to finish from.
    """
    from castle_combat.state import State

    server, perspective, _mind = connection
    spin(perspective.callRemote("claim_player_as_local"))
    spin(perspective.callRemote("client_ready"))
    settle()
    game_state = server.game.game_state
    avatar = server.clients[0]
    assert server.game.players[1].alive

    avatar.mind.broker.transport.loseConnection()
    settle()

    assert server.clients == []
    assert server.game.players[1].alive is False
    # the player at this machine keeps playing, and the game is still on
    assert server.game.players[0].alive
    assert game_state in State.stack


def test_transferring_a_player_signs_the_client_up_as_an_observer(connection):
    server, perspective, _mind = connection

    spin(perspective.callRemote("claim_player_as_local"))

    # a player carries its four phase players along in its state, and each of
    # those is a cacheable in its own right, so sending one registers the
    # client as an observer of all of them. This is the list that stays empty
    # in every other test, which is why the callRemote() fan-out in
    # delegate_and_call() never runs there
    player = server.game.players[1]
    assert player.observers
    for phase in ("build", "place", "battle", "select"):
        assert getattr(player, phase + "_player").observers, phase


class FakePerspective:
    """The server end of the handshake, without a server

    Every callRemote() the client makes during login answers at once, so the
    deferred chain in connected_callback() runs straight through.
    """

    def __init__(self, info, claimable):
        self.info = info
        self.claimable = list(claimable)
        self.calls = []

    def callRemote(self, name, *args):
        from twisted.internet import defer

        self.calls.append(name)
        if name == "get_server_info":
            return defer.succeed(self.info)
        if name == "claim_player_as_local":
            return defer.succeed(self.claimable.pop(0))
        return defer.succeed(None)


def test_the_client_handshake_builds_a_game_and_reports_ready():
    """client.py's half of joining, which no other test reaches

    Both bugs that once made joining impossible were on this path and were
    only found by connecting for real. The steps after the connection are
    plain callbacks, so they can be driven without one.
    """
    from castle_combat import client
    from castle_combat.player import PlayerCacheable

    MainState()
    menu.MenuState()
    joiner = client.Client("localhost")
    joiner.local_players = 1
    joiner.wait_for_server_state = client.WaitForSeverState()

    players = [PlayerCacheable(0), PlayerCacheable(1)]
    map = ConquerMap(dict(difficulty="medium"))
    map.setup()
    info = {"players": players, "map": map, "server_game": None}
    perspective = FakePerspective(info, [players[1]])

    joiner.connected_callback(perspective)

    assert perspective.calls == [
        "get_server_info",
        "claim_player_as_local",
        "client_ready",
    ]
    assert joiner.game.players == players
    assert joiner.game.field.map is map
    # the slot the server handed out is the one this machine plays
    assert players[1].local is True
    assert players[0].local is False
