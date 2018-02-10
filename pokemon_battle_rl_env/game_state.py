import numpy as np
from pokemon_battle_rl_env.poke_data_queries import get_move_by_name, moves


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
    def __init__(self, species, gender, stats, moves, ability, item, name=None, health=1.0, condition='', unknown=False):
        self.species = species
        self.health = health
        self.condition = condition
        self.gender = gender
        self.stats = stats
        if moves is None:
            moves = []
        self.moves = moves
        self.ability = ability
        self.item = item
        self.unknown = unknown
        if name is None:
            name = species
        self.name = name


class Trainer:
    def __init__(self, pokemon=None, name=None, mega_used=False):
        self.name = name
        if pokemon is None:
            pokemon = [Pokemon(None, None, None, None, None, None, None, None, None, True)] * 6
        self.pokemon = pokemon
        self.mega_used = mega_used


class GameState:
    def __init__(self):
        self.state = 'ongoing'
        self.player = Trainer()
        self.opponent = Trainer()
        self.weather = None
        self.field = None
        self.player_condition = None
        self.opponent_condition = None
        self.turn = 1

    def to_array(self):
        np.zeros(1)
