from json import loads

import websocket
from requests import post

from pokemon_battle_rl_env.battle_simulator import BattleSimulator
from pokemon_battle_rl_env.game_state import GameState

WEB_SOCKET_URL = "wss://sim.smogon.com/showdown/websocket"
SHOWDOWN_ACTION_URL = "https://play.pokemonshowdown.com/action.php"


class ShowdownSimulator(BattleSimulator):
    def __init__(self):
        print('Using Showdown')
        self.ws = websocket.WebSocket(sslopt={'check_hostname': False})
        self.ws.connect(WEB_SOCKET_URL)
        print('Connected')
        msg = ''
        while not msg.startswith('|challstr|'):
            msg = self.ws.recv()
        challstr = msg.split('|')[1]
        with open('../auth.txt', 'r') as file:
            self.username, self.password = file.readlines()
        self._authenticate(challstr)
        self.ws.send('|/utm null')  # Team
        self.ws.send('|/search gen7randombattle')  # Tier
        msg = ''
        while '|init|battle' not in msg:
            msg = self.ws.recv()
        self.room_id = msg.split('\n')[0][1:]
        msg = ''
        self.opponent = self.username
        initial_state = ''
        while self.opponent == self.username:
            while '|player|' not in msg:
                msg = self.ws.recv()
                if '|request|' in msg:
                    initial_state = msg[msg.find('|request|') + len('|request|'):]
            info = msg.split('|')[3]
            self.opponent_short = info[2]
            self.opponent = info[3]

        print(f'Playing against {self.opponent}')
        print(f'Initial state: {initial_state}')

        self.ws.send(f'{self.room_id}|/timer on')

        msg = ''
        while '|turn|' not in msg:
            msg = self.ws.recv()

        self.state = read_state_json(initial_state)

        super().__init__()

    def _authenticate(self, challstr):
        post_data = {'act': 'login', 'name': self.username, 'pass': self.password, 'challstr': challstr}
        response = post('http://play.pokemonshowdown.com/action.php', data=post_data)
        assertion = loads(response.text[1:])['assertion']
        login_cmd = f'|/trn {self.username},0,{assertion}'
        self.ws.send(login_cmd)
        msg = ''
        while not msg.startswith('updateuser') and self.username in msg:
            msg = self.ws.recv()

    def _attack(self, move):
        self.ws.send(f'{self.room_id}|/move {move}')

    def _switch(self, pokemon):
        self.ws.send(f'{self.room_id}|/switch {pokemon}')

    def _update_state(self):
        msg = ''
        while '|turn|' not in msg and '|win|' in msg and '|tie' not in msg:
            msg = self.ws.recv()
            parse_message(msg, self.state, self.opponent_short)
        # ToDo: add win/loss detection (ie, check whether one pokemon of one side have fainted). Maybe in GameState?

    def render(self, mode='human'):
        if mode is 'human':
            raise NotImplementedError  # Open https://play.pokemonshowdown.com in browser

    def reset(self):
        self.ws.send('|/forfeit')

    def close(self):
        self.ws.close()
        print('Connection closed')


def read_state_json(json):
    return GameState()


def parse_message(msg, state, opponent_short):
    msgs = msg.split('\n')
    for msg in msgs:
        if '|win|' in msg:
            winner = msg[len('|win|'):]
            state.state = 'win' if winner == state.player.name else 'loss'
        elif '|tie' in msg:
            state.state = 'tie'
        elif '|turn|' in msg:
            state.turn = int(msg[len('|turn|'):])
        elif '|request|' in msg:
            state_json = msg[len('|request|'):]
            state = read_state_json(state_json)
        elif '|switch|' in msg or '|drag|' in msg:
            info = msg.split('|')
            if opponent_short in info[1]:
                species = info[2].split(',')[0]
                if ', M' in info[2]:
                    gender = 'm'
                elif ', F' in info[2]:
                    gender = 'f'
                else:
                    gender = 'n'
                health = float(info[3].split('/')[0]) / 100
                switched_in = next((p for p in state.opponent.pokemon if p.species == species), None)
                if switched_in is None:
                    first_unknown = next(p for p in state.opponent.pokemon if p.unknown)
                    first_unknown.unknown = False
                    switched_in = first_unknown
                switched_in.species = species
                switched_in.gender = gender
                switched_in.health = health
                state.opponent.pokemon.insert(0, state.opponent.pokemon.pop(state.opponent.pokemon.index(switched_in)))


    return state
