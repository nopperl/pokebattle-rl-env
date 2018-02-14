from json import loads
from os.path import isfile
from secrets import choice
from string import ascii_letters, digits

from requests import post
from websocket import WebSocket

from pokebattle_rl_env.battle_simulator import BattleSimulator
from pokebattle_rl_env.game_state import GameState, Move
from pokebattle_rl_env.poke_data_queries import get_move_by_name, ability_name_to_id

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
    if response.text[0] != ']':
        raise AttributeError('Invalid username and/or password')
    response = loads(response.text[1:])
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
    return response.text


def generate_username():
    return generate_token(8)


def generate_token(length):
    return ''.join(choice(ascii_letters + digits) for i in range(length))


def ident_to_name(ident):
    return ident.split(':')[1][1:]


def ident_to_pokemon(ident, state, opponent_short=None):
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
    if ', M' in details:
        gender = 'm'
    elif ', F' in details:
        gender = 'f'
    else:
        gender = 'n'
    return species, gender


def parse_damage_heal(info, state, opponent_short):
    if opponent_short in info[2]:
        name = ident_to_name(info[2])
        damaged = next(p for p in state.opponent.pokemon if p.name == name)
        health, max_health, status = parse_health_status(info[3])
        if status is not None and status not in damaged.statuses:
            damaged.statuses.append(status)
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
    elif 'pseudoWeather' in move:
        effect = move['pseudoWeather']
    else:
        return
    if start:
        state.field_effects.append(effect)
    else:
        if effect in state.field_effects:
            state.field_effects.remove(effect)



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
            if start:
                state.opponent_conditions.append(condition)
            else:
                state.opponent_conditions.remove(condition)
        else:
            if start:
                state.player_conditions.append(condition)
            else:
                state.player_conditions.remove(condition)


def parse_mega(info, state, opponent_short):
    pokemon = ident_to_pokemon(info[2], state, opponent_short)
    pokemon.item = info[3]
    pokemon.mega = True


def parse_specieschange(info, state, opponent_short, details=True):
    pokemon = ident_to_pokemon(info[2], state, opponent_short)
    if details:
        species, gender = parse_pokemon_details(info[3])
    else:
        species = info[3]
        gender = pokemon.gender
    pokemon.change_species(species)
    pokemon.gender = gender
    if len(info) >= 5 and not info[4].startswith('[from]'):
        health, max_health, status = parse_health_status(info[4])
        pokemon.health = health
        pokemon.max_health = max_health if max_health is not None else 100
        if status not in pokemon.statuses:
            pokemon.statuses.append(status)


def parse_start_end(info, state, opponent_short, start=True):
    if opponent_short in info[2]:
        pokemon = ident_to_pokemon(info[2], state)
        if info[3] == 'confusion':
            if start:
                pokemon.statuses.append('confusion')
            else:
                pokemon.statuses.remove('confusion')


def parse_status(info, state, opponent_short, cure=False):
    if opponent_short in info[2]:
        affected = ident_to_pokemon(info[2], state)
        status = info[3]
        if status not in affected.statuses:
            if cure:
                affected.statuses.remove(status)
            else:
                affected.statuses.append(status)


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
    species, gender = parse_pokemon_details(info[3])
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
        switched_in.health = health
        switched_in.max_health = max_health if max_health is not None else 100
        if status not in switched_in.statuses:
            switched_in.statuses.append(status)
        switched_in.update()
    else:
        pokemon = state.player.pokemon
        switched_in = next((p for p in pokemon if p.species == species or p.name == name), None)
        switched_index = pokemon.index(switched_in)
        pokemon[0], pokemon[switched_index] = pokemon[switched_index], pokemon[0]


def sanitize_hidden_power(move_id):
    if move_id.startswith('hiddenpower') and move_id.endswith('60'):
        move_id = move_id[:-2]
    return move_id


def read_state_json(json, state):
    json = loads(json)
    st_active_pokemon = state.player.pokemon[0]
    st_active_pokemon.moves = []
    active_pokemon = json['active'][0]
    moves = active_pokemon['moves']
    if 'trapped' in active_pokemon and len(moves) <= 1:
        st_active_pokemon.trapped = active_pokemon['trapped']
        enabled_move_id = moves[0]['id']
        for move in st_active_pokemon.moves:
            move.disabled = not move.id == enabled_move_id
    elif 'maybeTrapped' in active_pokemon:
        st_active_pokemon.trapped = active_pokemon['maybeTrapped']
    else:
        st_active_pokemon.trapped = False
        for move in moves:
            move_id = move['id']
            move_id = sanitize_hidden_power(move_id)
            move = Move(id=move_id, pp=move['pp'], disabled=move['disabled'])
            st_active_pokemon.moves.append(move)
    pokemon_list = json['side']['pokemon']
    for i in range(len(pokemon_list)):
        st_pokemon = state.player.pokemon[i]
        pokemon = pokemon_list[i]
        st_pokemon.name = ident_to_name(pokemon['ident'])
        st_pokemon.species, st_pokemon.gender = parse_pokemon_details(pokemon['details'])
        health, max_health, status = parse_health_status(pokemon['condition'])
        if max_health is not None:
            st_pokemon.max_health = max_health
        st_pokemon.health = health
        st_pokemon.statuses = [status]
        st_pokemon.stats = pokemon['stats']
        if not pokemon['active'] and not all(
                move_id in [move.name for move in st_pokemon.moves] for move_id in pokemon['moves']):
            st_pokemon.moves = [Move(id=sanitize_hidden_power(move_id)) for move_id in pokemon['moves']]
        st_pokemon.item = pokemon['item']
        st_pokemon.ability = pokemon['ability']
        st_pokemon.unknown = False


class ShowdownSimulator(BattleSimulator):
    def __init__(self, auth='auth.txt'):
        print('Using Showdown backend')
        self.state = GameState()
        self.auth = auth
        self.room_id = None
        self.ws = None
        super().__init__()

    def _connect(self, auth):
        self.ws = WebSocket(sslopt={'check_hostname': False})
        self.ws.connect(url=WEB_SOCKET_URL)
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
            print(msg)

    def _attack(self, move, mega=False, z=False):
        cmd = f'{self.room_id}|/switch {move}'
        cmd += ' mega' if mega else ''
        cmd += ' zmove' if z else ''
        print(cmd)
        self.ws.send(cmd)

    def _switch(self, pokemon):
        print(f'{self.room_id}|/switch {pokemon}')
        self.ws.send(f'{self.room_id}|/switch {pokemon}')

    def _update_state(self):
        end = False
        while not end:
            msg = self.ws.recv()
            end = self._parse_message(msg)

    def _parse_message(self, msg):
        if self.room_id is None and '|init|battle' in msg:
            self.room_id = msg.split('\n')[0][1:]
        end = False
        if not msg.startswith(f'>{self.room_id}'):
            return False
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
                if info[2].startswith('{"forceSwitch":[true]'):
                    self.force_switch = True
                    end = True
                    continue
                if info[2] != '' and not info[2].startswith('{"wait":true'):
                    read_state_json(info[2], self.state)
            elif info[1] == 'move':
                parse_move(info, self.state, self.opponent_short)
            elif info[1] == 'upkeep':
                pass  # ToDo: update weather, status turns
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
                    self.state.weather = info[2]
            elif info[1] == '-fieldstart':
                parse_field(info, self.state)
            elif info[1] == '-fieldend':
                parse_field(info, self.state, start=False)
            # ToDo: Handle |-activate|POKEMON|ability: ABIlITY and [from] ability: ABILITY in -curestatus, -weather, -formechange, -damage, -heal, etc
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
            elif info[1] == '-transform':  # ToDo: Does -transform change POKEMON?
                pokemon = ident_to_pokemon(info[2], self.state, self.opponent_short)
                to_pokemon = ident_to_pokemon(info[3], self.state, self.opponent_short)
                pokemon.change_species(to_pokemon.species)
            elif info[1] == '-mega':
                if self.opponent_short in info[2]:
                    pokemon = self.state.opponent.pokemon
                    self.state.opponent.mega_used = True
                else:
                    pokemon = self.state.player.pokemon
                    self.state.player.mega_used = True
                name = ident_to_name(info[2])
                pokemon = next(p for p in pokemon if p.name == name)
                pokemon.item = info[3]
                pokemon.mega = True
            elif info[1] == '-item':
                parse_item(info, self.state, self.opponent_short)
            elif info[1] == '-enditem':
                parse_item(info, self.state, self.opponent_short, start=False)
            # ToDo: |[from] item:
            if '[from] ability:' in msg and '[of]' in msg:
                of_pokemon = None
                for part in info:
                    if '[from] ability:' in part:
                        ability = part[part.find('[from] ability: ') + len('[from] ability: '):]
                        ability = ability_name_to_id(ability)
                    elif '[of]' in part:
                        if self.opponent_short in part:
                            of_pokemon = part[part.find('[of] ') + len('[of] '):]
                            of_pokemon = ident_to_pokemon(of_pokemon, self.state)
                if of_pokemon is not None:
                    of_pokemon.ability = ability

            # ToDo: |-zpower|POKEMON |move|POKEMON|MOVE|TARGET|[zeffect]
        return end

    def render(self, mode='human'):
        if mode is 'human':
            raise NotImplementedError  # Open https://play.pokemonshowdown.com in browser

    def reset(self):
        if self.state.state == 'ongoing':
            self.ws.send(f'{self.room_id}|/forfeit')
        if self.room_id is not None:
            self.ws.send(f'|/leave {self.room_id}')
            self.room_id = None
            self.state = GameState()
            msg = ''
            while 'deinit' not in msg:
                msg = self.ws.recv()
                print(msg)
        if self.ws is None:
            self._connect(self.auth)
            print(f'Using username {self.username} with password {self.password}')
        self.ws.send('|/utm null')  # Team
        self.ws.send('|/search gen7randombattle')  # Tier
        self._update_state()
        print(f'Playing against {self.opponent}')
        self.ws.send(f'{self.room_id}|/timer on')

    def close(self):
        self.ws.close()
        print('Connection closed')
