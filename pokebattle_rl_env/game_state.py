from math import floor

import numpy as np

from pokebattle_rl_env.poke_data_queries import abilities, ability_name_to_id, field_effects, genders, \
    get_move_by_name, get_pokemon_by_species, items, moves, targets, typechart, side_conditions, status_conditions, \
    weathers

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


class Pokemon:
    def __init__(self, species=None, gender=None, ability=None, health=1.0, max_health=1.0, stats=None,
                 stat_boosts=None, battle_stats=None, moves=None, special_zmove_ix=None, item=None, name=None,
                 statuses=None, level=100, mega=False, trapped=False, recharge=False, unknown=False):
        self.species = species
        self.health = health
        self.max_health = max_health
        if statuses is None:
            statuses = []
        self.statuses = statuses
        self.gender = gender
        if stats is None:
            stats = {}
        self.stats = stats
        if stat_boosts is None:
            stat_boosts = {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0}
        self.stat_boosts = stat_boosts
        if battle_stats is None:
            battle_stats = {'accuracy': 0, 'evasion': 0}
        self.battle_stats = battle_stats
        if moves is None:
            moves = []
        self.moves = moves
        self.special_zmove_ix = special_zmove_ix
        self.ability = ability
        self.item = item
        self.level = level
        self.mega = mega
        self.trapped = trapped
        self.recharge = recharge
        self.unknown = unknown
        if name is None:
            name = species
        self.name = name
        self.types = []

        # Showdown-related
        self.locked_move_first_index = False
        self.update()

    def update(self):
        if self.species is not None:
            if self.gender is None:
                pokemon = get_pokemon_by_species(self.species)
                if 'gender' in pokemon:
                    self.gender = pokemon['gender']
                elif 'genderRatio' in pokemon:
                    gender_prob = [.0] * 3
                    for gender_r, ratio in pokemon['genderRatio'].items():
                        if gender_r == 'F':
                            gender_prob[0] = ratio
                        elif gender_r == 'M':
                            gender_prob[1] = ratio
                        elif gender_r == 'N':
                            gender_prob[2] = ratio
                    self.gender = np.random.choice(genders, p=gender_prob)
            if self.ability is None:
                pokemon = get_pokemon_by_species(self.species)
                self.ability = ability_name_to_id(pokemon['abilities']['0'])
            if self.stats is None:
                pokemon = get_pokemon_by_species(self.species)
                base_stats = pokemon['baseStats']
                if 'hp' in base_stats:
                    del base_stats['hp']
                stats = {}
                for stat, base in base_stats.items():
                    stats[stat] = calc_stat(base, self.level)
                self.stats = stats
            if self.types is None:
                pokemon = get_pokemon_by_species(self.species)
                self.types = pokemon['types']

    def change_species(self, species):
        self.species = species
        self.ability = None
        self.stats = None
        self.types = None
        self.update()


class Trainer:
    def __init__(self, pokemon=None, name=None, mega_used=False, z_used=False):
        self.name = name
        if pokemon is None:
            pokemon = [Pokemon(unknown=True) for _ in range(6)]
        self.pokemon = pokemon
        self.force_switch = False
        self.mega_used = mega_used
        self.z_used = z_used


class BattleEffect:
    def __init__(self, name, turn=1):
        self.name = name
        self.turn = turn


def calc_stat(base, level, hp=False):
    if hp:
        return floor((2 * base + 31 + 9.2) * level / 100 + level + 10)
    else:
        return floor((2 * base + 31 + 9.2) * level / 100 + 5)


def calc_boosted_stat(stat, boost):
    if boost >= 0:
        return stat * (3 + boost) / 3
    else:
        return stat * 3 / (3 - boost)


def pokemon_list_to_array(pokemon_list):
    state = []
    for pokemon in pokemon_list:
        health = pokemon.health / pokemon.max_health if pokemon.max_health is not None else pokemon.health / 100
        state.append(health)
        for gender in genders:
            state.append(1 if gender == pokemon.gender else 0)
        status_turns = []
        for status in status_conditions:
            status = next((s for s in pokemon.statuses if s.name == status), None)
            if status is not None:
                state.append(1)
                status_turns.append(status.turn)
            else:
                state.append(1)
                status_turns.append(0)
        state += status_turns
        for stat in ['atk', 'def', 'spa', 'spd', 'spe']:
            stat_value = pokemon.stats[stat] if stat in pokemon.stats else DEFAULT_STAT_VALUE
            boost = pokemon.stat_boosts[stat]
            state.append(calc_boosted_stat(stat_value, boost))
        for stat in ['accuracy', 'evasion']:
            state.append(pokemon.battle_stats[stat])
        for ability in abilities:
            state.append(1 if ability == pokemon.ability else 0)
        for type in typechart:
            state.append(1 if type in pokemon.types else 0)
        for item in items:
            state.append(1 if item == pokemon.item else 0)
        state.append(1 if pokemon.mega else 0)
        state.append(1 if pokemon.recharge else 0)
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
        self.field_effects = []
        self.player_conditions = []  # Stealth Rocks, Tailwind, etc
        self.opponent_conditions = []
        self.turn = 1
        self.forfeited = False

    def to_array(self):
        state = []
        state.append(self.turn)
        state.append(1 if self.player.mega_used else 0)
        state.append(1 if self.player.z_used else 0)
        state += pokemon_list_to_array(self.player.pokemon)
        for condition in side_conditions:
            state.append(1 if condition in self.player_conditions else 0)
        state.append(1 if self.opponent.mega_used else 0)
        state.append(1 if self.opponent.z_used else 0)
        state += pokemon_list_to_array(self.opponent.pokemon)
        for condition in side_conditions:
            state.append(1 if condition in self.opponent_conditions else 0)
        field_effect_turns = []
        for effect in field_effects:
            field_effect = next((f for f in self.field_effects if f.name == effect), None)
            if field_effect is not None:
                state.append(1)
                field_effect_turns.append(field_effect.turn)
            else:
                state.append(0)
                field_effect_turns.append(0)
        state += field_effect_turns
        for weather in weathers:
            state.append(1 if self.weather is not None and weather == self.weather.name else 0)
        state.append(self.weather.turn if self.weather is not None else 0)
        state = np.array(state)
        state[state is None] = 0
        return state
