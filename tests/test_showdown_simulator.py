from unittest import TestCase, main
from websocket import WebSocket
from pokebattle_rl_env.showdown_simulator import *
from pokebattle_rl_env.util import generate_username, generate_token


class TestAuthentication(TestCase):
    def setUp(self):
        self.ws = WebSocket(sslopt={'check_hostname': False})
        self.ws.connect(url='wss://sim.smogon.com/showdown/websocket')
        msg = ''
        while not msg.startswith('|challstr|'):
            msg = self.ws.recv()
        self.challstr = msg[msg.find('|challstr|') + len('|challstr|'):]
        self.ws.settimeout(.5)

    def test_auth_temp_user(self):
        username = generate_username()
        assertion = auth_temp_user(self.challstr, username)
        login_cmd = f'|/trn {username},0,{assertion}'
        self.ws.send(login_cmd)

    def test_login(self):
        with open('ts_auth.txt', 'r') as file:
            username, password = file.read().splitlines()
        assertion = login(self.challstr, username, password)
        login_cmd = f'|/trn {username},0,{assertion}'
        self.ws.send(login_cmd)

    def _username_in_msg(self, username):
        msg = ''
        while not msg.startswith('|updateuser|'):
            msg = self.ws.recv()
        self.assertIn(username, msg)

    def tearDown(self):
        self.ws.close()


class TestMsgParsing(TestCase):
    def test_ident_to_name(self):
        name = ident_to_name('p1a: Metagross')
        self.assertEqual(name, 'Metagross')

    def test_ident_to_pokemon(self):
        state = GameState()
        name_to_find = 'Metagross'
        player_short = 'p1a'
        opponent_short = 'p2a'
        for pokemon in state.player.pokemon:
            pokemon.name = generate_token(5)
        state.player.pokemon[4].name = name_to_find
        pokemon = ident_to_pokemon(player_short + ': ' + name_to_find, state, opponent_short)
        self.assertEqual(pokemon.name, name_to_find)
        state.player.pokemon[4].name = 'Metang'
        for pokemon in state.opponent.pokemon:
            pokemon.name = generate_token(5)
        state.opponent.pokemon[3].name = name_to_find
        pokemon = ident_to_pokemon(opponent_short + ': ' + name_to_find, state, opponent_short)
        self.assertEqual(pokemon.name, name_to_find)
        pokemon = ident_to_pokemon(opponent_short + ': ' + name_to_find, state)
        self.assertEqual(pokemon.name, name_to_find)


if __name__ == '__main__':
    main()
