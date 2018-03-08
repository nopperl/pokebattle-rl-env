from json import loads
from os.path import getsize, isfile
from random import random
from sys import stderr
from time import sleep

from requests import post
import webbrowser
from websocket import WebSocket
from websocket._exceptions import WebSocketTimeoutException

from pokebattle_rl_env.battle_simulator import BattleSimulator
from pokebattle_rl_env.game_state import BattleEffect, GameState, Move
from pokebattle_rl_env.poke_data_queries import get_move_by_name, ability_name_to_id, item_name_to_id
from pokebattle_rl_env.util import generate_username, generate_token

WEB_SOCKET_URL = 'wss://sim.smogon.com/showdown/websocket'
SHOWDOWN_ACTION_URL = 'https://play.pokemonshowdown.com/action.php'
LOCAL_WEB_SOCKET_URL = 'ws://localhost:8000/showdown/websocket'


def register(challstr, username, password):
    """Registers an account on https://pokemonshowdown.com.

    Args:
        challstr (str): The challenge string sent by the Pokemon Showdown server. Obtain this string by connecting to
            the Pokemon Showdown WebSocket.
        username (str): The username to register. Must be unique and not yet chosen.
        password (str): The password to register. Must be unique and not yet chosen.

    Returns:
        str: The assertion string used as authentication with the WebSocket.

    Raises:
        ValueError: If at least one of the parameters is empty or the authentication using the provided credentials
            failed.
    """
    if len(username) == 0 or len(password) == 0 or len(challstr) == 0:
        raise ValueError('Arguments must be non-empty.')
    post_data = {
        'act': 'register',
        'captcha': 'pikachu',
        'challstr': challstr,
        'cpassword': password,
        'password': password,
        'username': username
    }
    response = post(SHOWDOWN_ACTION_URL, data=post_data)
    if response.text[0] != ']':
        raise ValueError('Invalid username and/or password')
    response = loads(response.text[1:])
    if not response['actionsuccess']:
        raise ValueError('Invalid username and/or password')
    return response['assertion']


def login(challstr, username, password):
    """Logs into an existing account on https://pokemonshowdown.com.

    Args:
        challstr (str): The challenge string sent by the Pokemon Showdown server. Obtain this string by connecting to
            the Pokemon Showdown WebSocket.
        username (str): The username to login.
        password (str): The password to login.

    Returns:
        str: The assertion string used as authentication with the WebSocket.

    Raises:
        ValueError: If at least one of the parameters is empty or the authentication using the provided credentials
            failed.
    """
    if len(username) == 0 or len(password) == 0 or len(challstr) == 0:
        raise ValueError('Arguments must be non-empty.')
    post_data = {'act': 'login', 'name': username, 'pass': password, 'challstr': challstr}
    response = post(SHOWDOWN_ACTION_URL, data=post_data)
    response = loads(response.text[1:])
    return response['assertion']


def auth_temp_user(challstr, username):
    """Logs into a temporary user account on https://pokemonshowdown.com. The account is not password protected and
    deleted after a day.

    Args:
        challstr (str): The challenge string sent by the Pokemon Showdown server. Obtain this string by connecting to
            the Pokemon Showdown WebSocket.
        username (str): The username to register.

    Returns:
        str: The assertion string used as authentication with the WebSocket.

    Raises:
        ValueError: If at least one of the parameters is empty.
    """
    if len(username) == 0 or len(challstr) == 0:
        raise ValueError('Arguments must be non-empty.')
    post_data = {'act': 'getassertion', 'challstr': challstr, 'userid': username}
    response = post(SHOWDOWN_ACTION_URL, data=post_data)
    return response.text


def ident_to_name(ident):
    """Retrieves the pokemon name out of a pokemon identification string.

    Args:
        ident (str): The pokemon identification string.

    Returns:
        str: The name of the pokemon

    Examples:
        >>> ident_to_name('p1a: Metagross')
        'Metagross'
    """
    return ident.split(':')[1][1:]


def ident_to_pokemon(ident, state, opponent_short=None):
    """
    """
    if opponent_short is None or opponent_short in ident:
        pokemon = state.opponent.pokemon
    else:
        pokemon = state.player.pokemon
    name = ident_to_name(ident)
    pokemon = next(p for p in pokemon if p.name == name)
    return pokemon


def parse_health_status(string):
    status = None
    max_health = None
    if ' ' in string:
        health, status = string.split(' ')
    else:
        health = string
    if '/' in health:
        health, max_health = health.split('/')
    return float(health), float(max_health) if max_health is not None else None, status


def parse_pokemon_details(details):
    if ',' in details:
        species = details.split(',')[0]
    else:
        species = details
    if ', F' in details:
        gender = 'f'
    elif ', M' in details:
        gender = 'm'
    else:
        gender = 'n'
    level = 100
    if ', L' in details:
        pos = details.find(', L') + len(', L')
        level = int(details[pos:pos + 2])
    return species, gender, level


def parse_damage_heal(info, state, opponent_short):
    if opponent_short in info[2]:
        damaged = ident_to_pokemon(info[2], state, opponent_short)
        health, max_health, status = parse_health_status(info[3])
        if status is not None and not any(s.name == status for s in damaged.statuses):
            damaged.statuses.append(BattleEffect(status))
        if max_health is not None:
            damaged.max_health = max_health
        damaged.health = health


def parse_field(info, state, start=True):
    move_name = info[2]
    if 'move' in move_name:
        move_name = info[2].split(':')[1][1:]
    move = get_move_by_name(move_name)
    if 'terrain' in move:
        effect = move['terrain']
        state.field_effects = [f for f in state.field_effects if 'terrain' not in f.name]
    elif 'pseudoWeather' in move:
        effect = move['pseudoWeather']
    else:
        return
    if start:
        state.field_effects.append(BattleEffect(effect))
    else:
        effect = next((f for f in state.field_effects if f.name == effect), None)
        if effect is not None:
            state.field_effects.remove(effect)


def parse_mega(info, state, opponent_short):
    if opponent_short in info[2]:
        pokemon = state.opponent.pokemon
        state.opponent.mega_used = True
    else:
        pokemon = state.player.pokemon
        state.player.mega_used = True
    name = ident_to_name(info[2])
    pokemon = next(p for p in pokemon if p.name == name)
    pokemon.item = info[3] if opponent_short in info[2] else pokemon.item
    pokemon.mega = True


def parse_boost(info, state, opponent_short, unboost=False):
    pokemon = ident_to_pokemon(info[2], state, opponent_short)
    stat = info[3]
    modifier = -1 if unboost else 1
    if stat in pokemon.stat_boosts:
        pokemon.stat_boosts[stat] += modifier * int(info[4])
    elif stat in pokemon.battle_stats:
        pokemon.battle_stats[stat] += modifier * int(info[4])


def parse_item(info, state, opponent_short, start=True):
    if opponent_short in info[2]:
        pokemon = state.opponent.pokemon if opponent_short in info[2] else state.player.pokemon
        name = ident_to_name(info[2])
        pokemon = next(p for p in pokemon if p.name == name)
        if start:
            pokemon.item = info[3]
        else:
            pokemon.item = None


def parse_sideeffect(info, state, opponent_short, start=True):
    move_name = info[3]
    if 'move: ' in move_name:
        move_name = move_name.split(':')[1][1:]
    move = get_move_by_name(move_name)
    if 'sideCondition' in move:
        condition = move['sideCondition']
        if opponent_short in info[2]:
            conditions = state.opponent_conditions
        else:
            conditions = state.player_conditions
        if start:
            conditions.append(BattleEffect(condition))
        else:
            condition = next((c for c in conditions if c.name == condition), None)
            if condition is not None:
                conditions.remove(condition)


def parse_specieschange(info, state, opponent_short, details=True):
    pokemon = ident_to_pokemon(info[2], state, opponent_short)
    if details:
        species, gender, level = parse_pokemon_details(info[3])
        pokemon.level = level
    else:
        species = info[3]
        gender = pokemon.gender
    pokemon.change_species(species)
    pokemon.gender = gender
    if len(info) >= 5 and not info[4].startswith('['):
        health, max_health, status = parse_health_status(info[4])
        pokemon.health = health
        pokemon.max_health = max_health if max_health is not None else 100
        if status is not None and not any(s.name == status for s in pokemon.statuses):
            pokemon.statuses.append(BattleEffect(status))


def parse_replace(info, state, opponent_short):
    if opponent_short in info[2]:
        pokemon = state.opponent.pokemon[0]
        name = ident_to_name(info[2])
        species, gender, level = parse_pokemon_details(info[3])
        pokemon.name = name
        pokemon.gender = gender
        pokemon.level = level
        pokemon.change_species(species)


def parse_start_end(info, state, opponent_short, start=True):
    if opponent_short in info[2]:
        pokemon = ident_to_pokemon(info[2], state)
        if info[3] == 'confusion':
            if start:
                pokemon.statuses.append(BattleEffect('confusion'))
            else:
                pokemon.statuses = [s for s in pokemon.statuses if s.name != 'confusion']


def parse_status(info, state, opponent_short, cure=False):
    if opponent_short in info[2]:
        affected = ident_to_pokemon(info[2], state)
        status = info[3]
        if cure:
            affected.statuses = [s for s in affected.statuses if s.name != status]
        else:
            if not any(s.name == status for s in affected.statuses):
                affected.statuses.append(BattleEffect(status))


def parse_move(info, state, opponent_short):
    if opponent_short in info[2]:
        move_name = info[3]
        pokemon = state.opponent.pokemon
        used_move = next((m for m in pokemon[0].moves if m.name == move_name), None)
        if not used_move:
            used_move = Move(name=move_name)
            pokemon[0].moves.append(used_move)


def parse_switch(info, state, opponent_short):
    name = ident_to_name(info[2])
    species, gender, level = parse_pokemon_details(info[3])
    if opponent_short in info[2]:
        pokemon = state.opponent.pokemon
        health, max_health, status = parse_health_status(info[4])
        switched_in = next((p for p in pokemon if p.species == species or p.name == name), None)
        if switched_in is None:
            first_unknown = next(p for p in pokemon if p.unknown)
            first_unknown.unknown = False
            switched_in = first_unknown
        switched_in.name = name
        switched_in.species = species
        switched_in.gender = gender
        switched_in.level = level
        switched_in.health = health
        switched_in.max_health = max_health if max_health is not None else 100
        if status is not None and not any(s.name == state for s in switched_in.statuses):
            switched_in.statuses.append(BattleEffect(status))
        switched_in.update()
        switched_index = pokemon.index(switched_in)
        pokemon[0], pokemon[switched_index] = pokemon[switched_index], pokemon[0]


def parse_auxiliary_info(info, state, opponent_short):
    of_pokemon = None
    ability = None
    item = None
    for part in info:
        if '[from] ability:' in part:
            ability = part[part.find('[from] ability: ') + len('[from] ability: '):]
            ability = ability_name_to_id(ability)
        elif '[from] item' in part:
            item = part[part.find('[from] item: ') + len('[from] item: '):]
            item = item_name_to_id(item)
        elif '[of]' in part:
            if opponent_short in part:
                of_pokemon = part[part.find('[of] ') + len('[of] '):]
                of_pokemon = ident_to_pokemon(of_pokemon, state)
    if of_pokemon is not None:
        if ability is not None:
            of_pokemon.ability = ability
        if item is not None:
            of_pokemon.item = item


def sanitize_hidden_power(move_id):
    if move_id.startswith('hiddenpower'):
        return 'hiddenpower'
    return move_id


def read_state_json(json, state):
    json = loads(json)
    pokemon_list = json['side']['pokemon']
    for i in range(len(pokemon_list)):
        st_pokemon = state.player.pokemon[i]
        pokemon = pokemon_list[i]
        st_pokemon.name = ident_to_name(pokemon['ident'])
        st_pokemon.species, st_pokemon.gender, st_pokemon.level = parse_pokemon_details(pokemon['details'])
        health, max_health, status = parse_health_status(pokemon['condition'])
        if max_health is not None:
            st_pokemon.max_health = max_health
        st_pokemon.health = health
        confused_status = next((s for s in st_pokemon.statuses if s.name == 'confused'), None)
        if status is not None:
            st_pokemon.statuses = [BattleEffect(status)]
        if confused_status is not None:
            st_pokemon.statuses.append(confused_status)
        st_pokemon.stats = pokemon['stats']
        if not all(sanitize_hidden_power(move_id) in [move.id for move in st_pokemon.moves] for move_id in pokemon['moves']):
            st_pokemon.moves = [Move(id=sanitize_hidden_power(move_id)) for move_id in pokemon['moves']]
        st_pokemon.item = pokemon['item']
        st_pokemon.ability = pokemon['ability']
        st_pokemon.unknown = False
        st_pokemon.update()

    st_active_pokemon = state.player.pokemon[0]
    st_active_pokemon.recharge = False
    st_active_pokemon.special_zmove_ix = None
    if 'forceSwitch' not in json:
        st_active_pokemon.locked_move_first_index = False
        active_pokemon = json['active'][0]
        moves = active_pokemon['moves']
        st_active_pokemon.trapped = \
            active_pokemon['trapped'] if 'trapped' in active_pokemon else \
                active_pokemon['maybeTrapped'] if 'maybeTrapped' in active_pokemon else False
        if len(moves) <= 1:
            enabled_move_id = moves[0]['id']
            if enabled_move_id == 'struggle':
                st_active_pokemon.moves = [Move(id='struggle')]
            if enabled_move_id == 'recharge':
                st_active_pokemon.recharge = True
            for move in st_active_pokemon.moves:
                move.disabled = not move.id == enabled_move_id
            st_active_pokemon.locked_move_first_index = True
        else:
            st_active_pokemon.moves = []
            for move in moves:
                move_id = move['id']
                move_id = sanitize_hidden_power(move_id)
                move = Move(id=move_id, pp=move['pp'], disabled=move['disabled'])
                st_active_pokemon.moves.append(move)
            if 'canZMove' in active_pokemon:
                zmoves = active_pokemon['canZMove']
                st_active_pokemon.special_zmove_ix = next(i for i in range(len(zmoves)) if zmoves[i] is not None)
    else:
        st_active_pokemon.trapped = False
        state.player.force_switch = json['forceSwitch'][0]


class ShowdownConnection:
    """Holds information on how to connect to various endpoints of a specific Pokemon Showdown instance.

    There are two useful endpoints of each Pokemon Showdown instance:

    * The WebSocket endpoint, which enables user interaction and is used to run battles
    * The HTTP endpoint, which displays the client and is used to view battles

    :const:`DEFAULT_PUBLIC_CONNECTION` uses the default connection for the public
    instance at https://play.pokemonshowdown.com. :const:`DEFAULT_LOCAL_CONNECTION` uses
    the default connection for the local instance at https://localhost:8000. Specify a new instance of this class to use
    a custom Pokemon Showdown instance not hosted locally.

    Attributes:
        ws_host (str): The hostname of the WebSocket endpoint. Can be different from :attr:`web_host`.
        ws_port (int): The port of the WebSocket endpoint.
        ws_ssl (bool): Whether to use the WebSocket Secure protocol. Keep in mind to use the corresponding
            :attr:`ws_port` (most likely 433).
        web_host (str): The hostname of the HTTP endpoint. Can be different from :attr:`ws_host`.
        web_port (int): The port of the HTTP endpoint.
        web_ssl (bool): Whether to use HTTPS. Keep in mind to use the corresponding :attr:`web_port` (most likely 433).
    """
    def __init__(self, ws_host, ws_port, ws_ssl, web_host, web_port, web_ssl):
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.ws_ssl = ws_ssl
        self.ws_url = ('wss' if ws_ssl else 'ws') + f'://{ws_host}:{ws_port}/showdown/websocket'
        self.web_host = web_host
        self.web_port = web_port
        self.web_ssl = web_ssl
        self.web_url = ('https' if web_ssl else 'http') + f'://{web_host}:{web_port}'


DEFAULT_PUBLIC_CONNECTION = ShowdownConnection(
    ws_host='sim.smogon.com',
    ws_port=443,
    ws_ssl=True,
    web_host='play.pokemonshowdown.com',
    web_port=443,
    web_ssl=True
)

DEFAULT_LOCAL_CONNECTION = ShowdownConnection(
    ws_host='localhost',
    ws_port=8000,
    ws_ssl=False,
    web_host='localhost',
    web_port=8000,
    web_ssl=False
)


class ShowdownSimulator(BattleSimulator):
    """A :class:`pokebattle_rl_env.battle_simulator.BattleSimulator` using
    `Pokemon Showdown <https://pokemonshowdown.com>`_ as backend.

    View ongoing battles at https://play.pokemonshowdown.com/:attr:`room_id` if :attr:`local` is False or at
    http://localhost:8000/:attr:`room_id` if otherwise.

    Attributes:
        state (:class:`pokebattle_rl_env.game_state.GameState`): The current state of the battle.
        auth (str): The authentication method to use to log into https://pokemonshowdown.com. Options:

            * empty string: Log into a temporary account.
            * `'register'`: Generate a username and password to register an account. The credentials will be output on the
              console.
            * path to authentication file: Logs into an account specified in a text file, where the first line specifies
              the username and the second line specifies the password.


        self_play (bool): Whether to use self play. Note that this is a naive self play-implementation. In fact, agents
            simply play against other agents - a temporary text file keeps track of the battles. Thus, self play only
            works if `number of agents % 2 == 0`. If :attr:`self_play` is false, the agent will battle against random
            human opponents.
        connection (:class:`pokebattle_rl_env.showdown_simulator.ShowdownConnection`): Details which Pokemon Showdown
            connection to use. The default connection is to the local instance at https://localhost:8000. Use a local
            instance of Pokemon Showdown whenever possible. See https://github.com/Zarel/Pokemon-Showdown for
            installation instructions. Obviously, if :attr:`self_play` is false, using a local/custom instance is only
            recommended if there are human players on it. Otherwise, set :attr:`connection` to
            :const:`DEFAULT_PUBLIC_CONNECTION` to use the public connection at https://play.pokemonshowdown.com.
        debug_output (bool): Whether to output verbose battle and connectivity information to the console.
        room_id (str): The string used to identify the current battle (room).
    """
    def __init__(self, auth='', self_play=False, connection=DEFAULT_LOCAL_CONNECTION, debug_output=False):
        print('Using Showdown backend')
        self.state = GameState()
        self.auth = auth
        self.self_play = self_play
        self.connection = connection
        self.debug_output = debug_output
        self.room_id = None
        self.ws = None
        super().__init__()

    def _connect(self, auth):
        self.ws = WebSocket(sslopt={'check_hostname': False})
        self.ws.connect(url=self.connection.ws_url)
        if self.debug_output:
            print('Connected')
        msg = ''
        while not msg.startswith('|challstr|'):
            msg = self.ws.recv()
        challstr = msg[msg.find('|challstr|') + len('|challstr|'):]
        if auth == 'register':
            self.username = generate_username()
            self.password = generate_token(16)
            assertion = register(challstr=challstr, username=self.username, password=self.password)
        elif isfile(auth):
            with open(auth, 'r') as file:
                self.username, password = file.read().splitlines()
                self.password = None
            assertion = login(challstr=challstr, username=self.username, password=password)
        else:
            self.username = generate_username()
            self.password = None
            assertion = auth_temp_user(challstr=challstr, username=self.username)
        login_cmd = f'|/trn {self.username},0,{assertion}'
        self.ws.send(login_cmd)
        msg = ''
        while not msg.startswith('|updateuser|') and self.username not in msg:
            msg = self.ws.recv()
            if self.debug_output:
                print(msg)

    def _attack(self, move, mega=False, z=False):
        cmd = f'{self.room_id}|/move {move}'
        cmd += ' mega' if mega else ''
        cmd += ' zmove' if z else ''
        if self.debug_output:
            print(cmd)
        self.ws.send(cmd)

    def _switch(self, pokemon):
        if self.debug_output:
            print(f'{self.room_id}|/switch {pokemon}')
        self.ws.send(f'{self.room_id}|/switch {pokemon}')
        pokemon_list = self.state.player.pokemon
        pokemon_list[0], pokemon_list[pokemon - 1] = pokemon_list[pokemon - 1], pokemon_list[0]
    counter = 0
    self_play_problem = False
    def _update_state(self):
        self.counter += 1
        print(f'{self.state.player.name}, {self.counter}')
        end = False
        while not end:
            if self.self_play:
                # A curios situation occurs in naive self-play, where two environments are reset and set up a battle
                # against each other, yet only one environment actually executes actions. In this case, wait for an
                # answer of the foe and simply break if nothing happens.
                self.ws.settimeout(1)
                try:
                    msg = self.ws.recv()
                except WebSocketTimeoutException:
                    self.ws.settimeout(None)
                    self.self_play_problem = True
                    self.state.state = 'tie'
                    self.state.forfeited = True
                    break
                self.ws.settimeout(None)
            else:
                msg = self.ws.recv()
            end = self._parse_message(msg)

    def _parse_message(self, msg):
        if self.room_id is None and '|init|battle' in msg:
            self.room_id = msg.split('\n')[0][1:]
        end = False
        if not msg.startswith(f'>{self.room_id}'):
            return False
        if self.debug_output:
            print(msg)
        msgs = msg.split('\n')
        for msg in msgs:
            info = msg.split('|')
            if len(info) < 2:
                continue
            if info[1] == 'player':
                if info[3] == self.username:
                    self.player_short = info[2]
                    self.state.player.name = info[3]
                else:
                    self.opponent = info[3]
                    self.state.opponent.name = self.opponent
                    self.opponent_short = info[2]
            elif info[1] == 'win':
                winner = msg[len('|win|'):]
                self.state.state = 'win' if winner == self.state.player.name else 'loss'
                end = True
            elif info[1] == 'tie':
                self.state.state = 'tie'
                end = True
            elif info[1] == 'turn':
                self.state.turn = int(info[2])
                if self.state.turn == 1:
                    self.state.state = 'ongoing'
                end = True
            elif info[1] == 'request':
                if info[2].startswith('{"wait":true') and False:  # ToDo: Start battle on first action?
                    end = True
                elif info[2] != '' and not info[2].startswith('{"wait":true'):
                    read_state_json(info[2], self.state)
                    end = self.state.player.force_switch
            elif info[1] == 'replace':
                parse_replace(info, self.state, self.opponent_short)
            elif info[1] == 'move':
                parse_move(info, self.state, self.opponent_short)
            elif info[1] == 'upkeep':
                for effect in self.state.field_effects + self.state.player_conditions + self.state.opponent_conditions:
                    effect.turn += 1
                for pokemon in self.state.player.pokemon + self.state.opponent.pokemon:
                    for status in pokemon.statuses:
                        status.turn += 1
                pass
            elif info[1] == 'error':
                print(msg, file=stderr)
            elif info[1] == 'switch' or info[1] == 'drag':
                parse_switch(info, self.state, self.opponent_short)
            elif info[1] == '-boost':
                parse_boost(info, self.state, self.opponent_short)
            elif info[1] == '-unboost':
                parse_boost(info, self.state, self.opponent_short, unboost=True)
            elif info[1] == '-damage' or info[1] == '-heal':
                parse_damage_heal(info, self.state, self.opponent_short)
            elif info[1] == '-status':
                parse_status(info, self.state, self.opponent_short)
            elif info[1] == '-curestatus':
                parse_status(info, self.state, self.opponent_short, cure=True)
            elif info[1] == '-message':
                if 'lost due to inactivity.' in info[2] or 'forfeited.' in info[2]:
                    self.state.forfeited = True
            elif info[1] == '-start':
                parse_start_end(info, self.state, self.opponent_short)
            elif info[1] == '-end':
                parse_start_end(info, self.state, self.opponent_short, start=False)
            elif info[1] == '-sidestart':
                parse_sideeffect(info, self.state, self.opponent_short)
            elif info[1] == '-sideend':
                parse_sideeffect(info, self.state, self.opponent_short, start=False)
            elif info[1] == '-weather':
                if info[2] == 'none':
                    self.state.weather = None
                else:
                    if self.state.weather is not None and info[2] == self.state.weather.name and len(info) > 3 and\
                       info[3] == '[upkeep]':
                        self.state.weather.turn += 1
                    else:
                        self.state.weather = BattleEffect(info[2])
            elif info[1] == '-fieldstart':
                parse_field(info, self.state)
            elif info[1] == '-fieldend':
                parse_field(info, self.state, start=False)
            elif info[1] == '-ability':
                pokemon = ident_to_pokemon(info[2], self.state, self.opponent_short)
                ability = ability_name_to_id(info[3])
                pokemon.ability = ability
            elif info[1] == 'endability':
                pokemon = ident_to_pokemon(info[2], self.state, self.opponent_short)
                pokemon.ability = None
            elif info[1] == 'detailschange':
                parse_specieschange(info, self.state, self.opponent_short)
            elif info[1] == '-formechange':
                parse_specieschange(info, self.state, self.opponent_short, details=True)
            elif info[1] == '-transform':
                pokemon = ident_to_pokemon(info[2], self.state, self.opponent_short)
                to_pokemon = ident_to_pokemon(info[3], self.state, self.opponent_short)
                pokemon.change_species(to_pokemon.species)
            elif info[1] == '-mega':
                parse_mega(info, self.state, self.opponent_short)
            elif info[1] == '-item':
                parse_item(info, self.state, self.opponent_short)
            elif info[1] == '-enditem':
                parse_item(info, self.state, self.opponent_short, start=False)
            elif info[1] == '-zpower':
                if self.opponent_short in msg:
                    self.state.opponent.z_used = True
                else:
                    self.state.player.z_used = True
            # ToDo: |-zpower|POKEMON |move|POKEMON|MOVE|TARGET|[zeffect]
            if '[of]' in msg:
                parse_auxiliary_info(info, self.state, self.opponent_short)
        return end

    def render(self, mode='human'):
        """Renders the ongoing battle, if there is any.

        Args:
            mode (str): Details the rendering mode. Currently, only mode `human` is supported. `human` will simply open
                the ongoing battle in a web browser (if one exists). Therefore, it is advised to call :meth:`render`
                only once per battle.
        """
        if mode == 'human' and self.room_id is not None:
            browser_url = f'{self.connection.web_url}/{self.room_id}'
            webbrowser.open(browser_url)

    def reset(self):
        """Resets the simulator to its initial state. Call this function prior to calling :meth:`act`. It automatically
        sets up a new battle, even if there exists an ongoing battle.
        """
        print(f'Reset {self.state.player.name}')
        if self.state.state == 'ongoing':
            if self.debug_output:
                print(f'{self.room_id}|/forfeit')
            self.ws.send(f'{self.room_id}|/forfeit')
        if self.room_id is not None:
            if self.debug_output:
                print(f'|/leave {self.room_id}')
            self.ws.send(f'|/leave {self.room_id}')
            self.room_id = None
            self.state = GameState()
            msg = ''
            while 'deinit' not in msg:
                msg = self.ws.recv()
                if self.debug_output:
                    print(msg)
        if self.ws is None:
            self._connect(self.auth)
            if self.debug_output:
                print(f'Using username {self.username} with password {self.password}')
        self.ws.send('|/utm null')  # Team

        if self.self_play_problem:
            self.self_play_problem = False
            return

        if self.self_play:
            self.ws.settimeout(None)
            # Self play
            sleep(random())
            if not isfile('usernames'):
                open('usernames', 'a').close()
            if getsize('usernames') == 0:
                with open('usernames', 'w') as file:
                    file.write(self.username + '\n')
                if self.debug_output:
                    print('empty')
                while True:
                    msg = self.ws.recv()
                    if self.debug_output:
                        print(msg)
                    if msg.startswith('|updatechallenges|'):
                        json = loads(msg.split('|')[2])
                        if 'challengesFrom' in json and json['challengesFrom']:
                            opponent = next(iter(json['challengesFrom']))
                            self.ws.send(f'|/accept {opponent}')
                            if self.debug_output:
                                print(f'|/accept {opponent}')
                            break
            else:
                with open('usernames', 'r') as file:
                    lines = file.read().splitlines()
                opponent = lines.pop(0)
                with open('usernames', 'w') as file:
                    file.writelines(lines)
                self.ws.send(f'|/challenge {opponent}, gen7randombattle')
                if self.debug_output:
                    print(f'|/challenge {opponent}, gen7randombattle')

            # p >> |/challenge [OPPONENT], gen7randombattle
            # p << |updatechallenges|{"challengesFrom":{},"challengeTo":{"to":"[OPPONENT]","format":"gen7randombattle"}}
            # o << |updatechallenges|{"challengesFrom":{"[PLAYER]":"gen7randombattle"},"challengeTo":null}
            # o >> |/accept [PLAYER]
            # - << |updatechallenges|{"challengesFrom":{},"challengeTo":null}
            # - << |updatesearch|{"searching":[],"games":null}
            # - << |updatesearch|{"searching":[],"games":{"battle-gen7randombattle-706502869":"[Gen 7] Random Battle"}}
        else:
            # Against human players
            self.ws.send('|/search gen7randombattle')  # Tier

        self._update_state()
        if not self.self_play:
            self.ws.send(f'{self.room_id}|/timer on')
        if self.debug_output:
            print(f'Playing against {self.opponent}')

    def close(self):
        """Closes the connection to the WebSocket endpoint."""
        self.ws.close()
        if self.debug_output:
            print('Connection closed')
