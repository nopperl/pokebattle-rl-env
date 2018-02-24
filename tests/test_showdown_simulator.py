from unittest import TestCase, main
from websocket import WebSocket
from pokebattle_rl_env.game_state import BattleEffect
from pokebattle_rl_env.showdown_simulator import *
from pokebattle_rl_env.util import generate_username, generate_token
from os.path import dirname, join
from json import dumps


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
        self._username_in_msg(username)

    def test_login(self):
        with open('ts_auth.txt', 'r') as file:
            username, password = file.read().splitlines()
        assertion = login(self.challstr, username, password)
        login_cmd = f'|/trn {username},0,{assertion}'
        self.ws.send(login_cmd)
        self._username_in_msg(username)

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
        player_short = 'p1'
        opponent_short = 'p2'
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

    def test_parse_health_status(self):
        self.assertEqual(parse_health_status('166/229'), (166.0, 229.0, None))
        self.assertEqual(parse_health_status('70/288 brn'), (70.0, 288.0, 'brn'))

    def test_parse_pokemon_details(self):
        self.assertEqual(parse_pokemon_details('Metagross'), ('Metagross', 'n', 100))
        self.assertEqual(parse_pokemon_details('Metagross, shiny, L82'), ('Metagross', 'n', 82))
        self.assertEqual(parse_pokemon_details('Metagross, F'), ('Metagross', 'f', 100))
        self.assertEqual(parse_pokemon_details('Metagross, M'), ('Metagross', 'm', 100))
        self.assertEqual(parse_pokemon_details('Metagross, shiny, F'), ('Metagross', 'f', 100))
        self.assertEqual(parse_pokemon_details('Metagross, shiny, M, L82'), ('Metagross', 'm', 82))

    def test_parse_damage_heal(self):
        state = GameState()
        pokemon = state.opponent.pokemon[2]
        pokemon.name = 'Metagross'
        pokemon.max_health = 100
        pokemon.health = 100
        parse_damage_heal('|-damage|p1a: Metagross|39/100 tox'.split('|'), state, 'p1')
        self.assertEqual(pokemon.health, 39)
        self.assertEqual(pokemon.max_health, 100)
        self.assertEqual(pokemon.statuses[0].name, 'tox')

    def test_parse_field(self):
        state = GameState()
        info = '|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p2a: Tapu Koko'.split('|')
        parse_field(info, state)
        self.assertEqual(state.field_effects[0].name, 'electricterrain')
        info = '|-fieldstart|move: Misty Terrain|[from] ability: Misty Surge|[of] p2a: Tapu Fini'.split('|')
        parse_field(info, state)
        self.assertEqual(state.field_effects[0].name, 'mistyterrain')
        self.assertEqual(len(state.field_effects), 1)
        info = '|-fieldstart|move: Trick Room|[of] p1b: Oranguru'.split('|')
        parse_field(info, state)
        self.assertEqual(state.field_effects[0].name, 'mistyterrain')
        self.assertEqual(state.field_effects[1].name, 'trickroom')
        self.assertEqual(len(state.field_effects), 2)
        parse_field('|-fieldend|Misty Terrain'.split('|'), state, start=False)
        self.assertEqual(state.field_effects[0].name, 'trickroom')
        self.assertEqual(len(state.field_effects), 1)
        parse_field('|-fieldend|move: Trick Room'.split('|'), state, start=False)
        self.assertEqual(state.field_effects, [])

    def test_parse_replace(self):
        state = GameState()
        pokemon = state.opponent.pokemon[0]
        state.opponent.pokemon[0].change_species('Metagross')
        state.opponent.pokemon[1].change_species('Metang')
        info = '|replace|p1a: Zoroark|Zoroark, L78, M'.split('|')
        parse_replace(info, state, 'p1')
        self.assertEqual(pokemon.species, 'Zoroark')
        self.assertEqual(pokemon.ability, 'illusion')
        self.assertEqual(pokemon.gender, 'm')
        self.assertEqual(state.opponent.pokemon[1].species, 'Metang')


class TestUpdateState(TestCase):
    def test_force_switch(self):
        simulator = ShowdownSimulator()
        with open(join(dirname(__file__), 'json', 'force_switch.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        end = simulator._parse_message(f'>battle-1|init|battle\n|request|{json}')
        self.assertTrue(end)
        self.assertTrue(simulator.state.player.force_switch)


class TestRequestJson(TestCase):
    def test_force_switch(self):
        with open(join(dirname(__file__), 'json', 'force_switch.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertFalse(state.player.pokemon[0].trapped)

    def test_recharge(self):
        with open(join(dirname(__file__), 'json', 'recharge.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertTrue(state.player.pokemon[0].recharge)

    def test_struggle(self):
        with open(join(dirname(__file__), 'json', 'struggle.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertEqual(len(state.player.pokemon[0].moves), 1)
        self.assertEqual(state.player.pokemon[0].moves[0].id, 'struggle')

    def test_can_z_move(self):
        with open(join(dirname(__file__), 'json', 'can_z_move.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertEqual(state.player.pokemon[0].special_zmove_ix, 1)
        self.assertEqual(state.player.pokemon[0].moves[state.player.pokemon[0].special_zmove_ix].id, 'clangingscales')

    def test_trapped(self):
        with open(join(dirname(__file__), 'json', 'trapped_2.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertTrue(state.player.pokemon[0].trapped)
        self.assertEqual(len(state.player.pokemon[0].moves), 4)
        self.assertTrue(not any(move.disabled for move in state.player.pokemon[0].moves))

    def test_trapped_zoroark(self):
        with open(join(dirname(__file__), 'json', 'trapped_zoroark.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertTrue(state.player.pokemon[0].trapped)
        self.assertEqual(len(state.player.pokemon[0].moves), 4)
        self.assertTrue(not any(move.disabled for move in state.player.pokemon[0].moves))

    def test_trapped_move(self):
        with open(join(dirname(__file__), 'json', 'trapped_1.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertTrue(state.player.pokemon[0].trapped)
        self.assertEqual(len(state.player.pokemon[0].moves), 4)
        self.assertTrue(all(move.disabled for move in state.player.pokemon[0].moves if move.id != 'outrage'))
        self.assertTrue(not any(move.disabled for move in state.player.pokemon[0].moves if move.id == 'outrage'))

    def test_maybe_trapped_move(self):
        with open(join(dirname(__file__), 'json', 'maybe_trapped_1.json'), 'r') as file:
            json = file.read()
            json = dumps(loads(json))
        state = GameState()
        read_state_json(json, state)
        self.assertTrue(state.player.pokemon[0].trapped)
        self.assertEqual(len(state.player.pokemon[0].moves), 4)
        self.assertTrue(all(move.disabled for move in state.player.pokemon[0].moves if move.id != 'hiddenpower'))
        self.assertTrue(not any(move.disabled for move in state.player.pokemon[0].moves if move.id == 'hiddenpower'))


if __name__ == '__main__':
    main()
