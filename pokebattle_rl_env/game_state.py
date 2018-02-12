import numpy as np

from pokebattle_rl_env.poke_data_queries import abilities, genders, get_move_by_name, get_pokemon_by_species, items, \
    moves, targets, typechart, status_conditions

DEFAULT_STAT_VALUE = 60


class Item:
    def __init__(self, name):
        self.name = name
        self.used = False


class Move:
    def __init__(self, id=None, name=None, pp=None, disabled=False):  # id or name must be provided (xor, id is faster)
        if name is None:
            if id is None:
                raise ValueError('Either id or name must be provided')
            move = moves[id]
            self.id = id
            self.name = move['name']
        else:
            move = get_move_by_name(name)
            self.id = move['id']
            self.name = name
        if pp is None:
            pp = move['pp']
        self.pp = pp
        self.disabled = disabled
        self.type = move['type']
        self.target = move['target']


class Stats:
    def __init__(self, atk, def_, spa, spd, spe):
        self.atk = atk
        self.def_ = def_
        self.spa = spa
        self.spd = spd
        self.spe = spe


class Pokemon:
    def __init__(self, species=None, gender=None, ability=None, health=1.0, max_health=1.0, stats=None, moves=None,
                 item=None, name=None, conditions=None, trapped=False, unknown=False):
        self.species = species
        self.health = health
        self.max_health = max_health
        if conditions is None:
            conditions = []
        self.conditions = conditions
        self.gender = gender
        if stats is None:
            stats = {}
        self.stats = stats
        if moves is None:
            moves = []
        self.moves = moves
        self.ability = ability
        self.item = item
        self.trapped = trapped
        self.unknown = unknown
        if name is None:
            name = species
        self.name = name
        self.types = []
        self.update()

    def update(self):
        if self.species is not None:
            if self.gender is None:
                pokemon = get_pokemon_by_species(self.species)
                if 'gender' in pokemon:
                    self.gender = pokemon['gender']
                elif 'genderRatio' in pokemon:  # ToDo: Use weighted coin toss
                    max_ratio = 0
                    for gender_r, ratio in pokemon['genderRatio'].items():
                        if ratio > max_ratio:
                            self.gender = gender_r
            if self.ability is None:
                pokemon = get_pokemon_by_species(self.species)
                self.ability = pokemon['abilities']['0']
            if self.stats is None:
                pokemon = get_pokemon_by_species(self.species)
                self.stats = pokemon['baseStats']
                del self.stats['hp']
            if self.types is None:
                pokemon = get_pokemon_by_species(self.species)
                self.types = pokemon['types']


class Trainer:
    def __init__(self, pokemon=None, name=None, mega_used=False):
        self.name = name
        if pokemon is None:
            pokemon = [Pokemon(unknown=True) for i in range(6)]
        self.pokemon = pokemon
        self.mega_used = mega_used


def pokemon_list_to_array(pokemon_list):
    state = []
    for pokemon in pokemon_list:
        health = pokemon.health / pokemon.max_health if pokemon.max_health is not None else pokemon.health / 100
        state.append(health)
        for gender in genders:
            state.append(1 if gender == pokemon.gender else 0)
        for condition in status_conditions:
            state.append(1 if condition in pokemon.conditions else 0)
        for stat in ['atk', 'def', 'spa', 'spd', 'spe']:
            state.append(pokemon.stats[stat] if stat in pokemon.stats else DEFAULT_STAT_VALUE)
        for ability in abilities:
            state.append(1 if ability == pokemon.ability else 0)
        for type in typechart:
            state.append(1 if type in pokemon.types else 0)
        for item in items:
            state.append(1 if item == pokemon.item else 0)
        for i in range(4):
            if i >= len(pokemon.moves):
                move_length = len(moves) + len(typechart) + len(targets) + 2
                state += [0] * move_length
            else:
                move = pokemon.moves[i]
                for move_id in moves:
                    state.append(1 if move_id == move.id else 0)
                state.append(move.pp)
                state.append(1 if move.disabled else 0)
                for type in typechart:
                    state.append(1 if type == move.type else 0)
                for target in targets:
                    state.append(1 if target == move.target else 0)
    return state


class GameState:
    def __init__(self):
        self.state = 'init'
        self.player = Trainer()
        self.opponent = Trainer()
        self.weather = None
        self.field = None
        self.player_condition = None  # Stealth Rocks, Tailwind, etc
        self.opponent_condition = None
        self.turn = 1

    def to_array(self):
        state = []
        # ToDo: weather, field
        # ToDo: mega used
        state.append(self.turn)
        state += pokemon_list_to_array(self.player.pokemon)
        state += pokemon_list_to_array(self.opponent.pokemon)
        state = np.array(state)
        state[state is None] = 0
        return state
