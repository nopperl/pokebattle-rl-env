from json import loads
from os.path import isfile
from secrets import choice
from string import ascii_letters, digits

import websocket
from requests import post

from pokemon_battle_rl_env.battle_simulator import BattleSimulator
from pokemon_battle_rl_env.game_state import GameState, Move

WEB_SOCKET_URL = "wss://sim.smogon.com/showdown/websocket"
SHOWDOWN_ACTION_URL = "https://play.pokemonshowdown.com/action.php"


def register(challstr, username, password):
    post_data = {
        'act': 'register',
        'captcha': 'pikachu',
        'challstr': challstr,
        'cpassword': password,
        'password': password,
        'username': username
    }
    response = post(SHOWDOWN_ACTION_URL, data=post_data)
    if response[0] != ']':
        raise AttributeError('Invalid username and/or password')
    response = loads(response[1:])
    if not response['actionsuccess']:
        raise AttributeError('Invalid username and/or password')
    return response['assertion']


def login(challstr, username, password):
    post_data = {'act': 'login', 'name': username, 'pass': password, 'challstr': challstr}
    response = post(SHOWDOWN_ACTION_URL, data=post_data)
    response = loads(response.text[1:])
    return response['assertion']


def auth_temp_user(challstr, username):
    post_data = {'act': 'getassertion', 'challstr': challstr, 'userid': username}
    response = post(SHOWDOWN_ACTION_URL, data=post_data)
    return response


def generate_username():
    return 'metergross-' + generate_token(8)


def generate_token(length):
    return ''.join(choice(ascii_letters + digits) for i in range(length))


def parse_switch(msg, state, opponent_short):
    info = msg.split('|')
    name = info[1].split(':')[1][1:]
    species = info[2].split(',')[0]
    if opponent_short in info[1]:
        pokemon = state.opponent.pokemon
        if ', M' in info[2]:
            gender = 'm'
        elif ', F' in info[2]:
            gender = 'f'
        else:
            gender = 'n'
        health = float(info[3].split('/')[0]) / 100
        switched_in = next((p for p in pokemon if p.species == species and p.name == name), None)
        if switched_in is None:
            first_unknown = next(p for p in pokemon if p.unknown)
            first_unknown.unknown = False
            switched_in = first_unknown
        switched_in.name = name
        switched_in.species = species
        switched_in.gender = gender
        switched_in.health = health
    else:
        pokemon = state.player.pokemon
        switched_in = next((p for p in pokemon if p.species == species and p.name == name), None)
    pokemon.insert(0, pokemon.pop(pokemon.index(switched_in)))


def read_state_json(json):
    return GameState()


class ShowdownSimulator(BattleSimulator):
    def __init__(self, auth=''):
        print('Using Showdown backend')
        self._connect()
        print(f'Using username {self.username} with password {self.password}')
        self.ws.send('|/utm null')  # Team
        self.ws.send('|/search gen7randombattle')  # Tier
        self._update_state()
        print(f'Playing against {self.opponent}')
        self.ws.send(f'{self.room_id}|/timer on')
        super().__init__()

    def _connect(self, auth):
        self.ws = websocket.WebSocket(sslopt={'check_hostname': False})
        self.ws.connect(url=WEB_SOCKET_URL)
        print('Connected')
        msg = ''
        while not msg.startswith('|challstr|'):
            msg = self.ws.recv()
        challstr = msg.split('|')[2]
        if auth == 'register':
            self.username = generate_username()
            self.password = generate_token(16)
            assertion = register(challstr=challstr, username=self.username, password=self.password)
        elif isfile(auth):
            with open(auth, 'r') as file:
                self.username, password = file.readlines()
            assertion = login(challstr=challstr, username=self.username, password=password)
        else:
            self.username = generate_username()
            assertion = auth_temp_user(challstr=challstr, username=self.username)
        login_cmd = f'|/trn {self.username},0,{assertion}'
        self.ws.send(login_cmd)
        msg = ''
        while not msg.startswith('updateuser') and self.username not in msg:
            msg = self.ws.recv()

    def _attack(self, move):
        self.ws.send(f'{self.room_id}|/move {move}')

    def _switch(self, pokemon):
        self.ws.send(f'{self.room_id}|/switch {pokemon}')

    def _update_state(self):
        msg = ''
        while '|turn|' not in msg and '|win|' in msg and '|tie' not in msg:
            msg = self.ws.recv()
            self._parse_message(msg)

    def _parse_message(self, msg):
        if not self.room_id and '|init|battle' in msg:
            self.room_id = msg.split('\n')[0][1:]
        msgs = msg.split('\n')  # ToDo: Check whether msg starts with >room_id
        for msg in msgs:
            info = msg.split('|')
            if len(info) < 2:
                break
            if info[1] == 'player':
                if info[3] == self.username:
                    self.player_short = info[2]
                else:
                    self.opponent = info[3]
                    self.opponent_short = info[2]
            elif info[1] == 'win':
                winner = msg[len('|win|'):]
                self.state.state = 'win' if winner == self.state.player.name else 'loss'
            elif info[1] == 'tie':
                self.state.state = 'tie'
            elif info[1] == 'tie':
                self.state.turn = int(msg[len('|turn|'):])
            elif info[1] == 'request':
                state_json = msg[len('|request|'):]
                self.state = read_state_json(state_json)
            elif info[1] == 'move':
                info = msg.split('|')
                if self.opponent_short in info[1]:
                    move_name = info[2]
                    pokemon = self.state.opponent.pokemon
                    used_move = next((m for m in pokemon[0].moves if m.name == move_name), None)
                    if not used_move:
                        used_move = Move(move_name, None, None, None)
                        pokemon[0].moves.append(used_move)
            elif info[1] == 'upkeep':
                pass  # ToDo: update weather, status turns
            elif info[1] == 'switch' or info[1] == 'drag':
                parse_switch(msg, self.state, self.opponent_short)

    def render(self, mode='human'):
        if mode is 'human':
            raise NotImplementedError  # Open https://play.pokemonshowdown.com in browser

    def reset(self):
        if self.state.state == 'ongoing':
            self.ws.send('|/forfeit')
        self.ws.send(f'|/leave {self.room_id}')
        msg = ''
        while 'deinit' not in msg:
            msg = self.ws.recv()

    def close(self):
        self.ws.close()
        print('Connection closed')
