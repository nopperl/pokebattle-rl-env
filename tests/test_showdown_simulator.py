from unittest import TestCase, main
from websocket import WebSocket
from pokebattle_rl_env.game_state import BattleEffect
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


class TestRequestJson(TestCase):
    def test_recharge(self):
        json = '{"active":[{"moves":[{"move":"Recharge","id":"recharge"}],"trapped":true}],"side":{"name":"test","id":"p2","pokemon":[{"ident":"p2: Slaking","details":"Slaking, L83, F","condition":"240/385","active":true,"stats":{"atk":313,"def":214,"spa":205,"spd":156,"spe":214},"moves":["earthquake","pursuit","doubleedge","gigaimpact"],"baseAbility":"truant","item":"choiceband","pokeball":"pokeball","ability":"truant"}]}}'
        state = GameState()
        read_state_json(json, state)
        self.assertTrue(state.player.pokemon[0].recharge)


if __name__ == '__main__':
    main()
