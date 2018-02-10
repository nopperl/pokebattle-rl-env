import numpy as np


class Item:
    def __init__(self, name):
        self.name = name
        self.used = False


class Move:
    def __init__(self, name, pp, target='normal', disabled=False):
        self.name = name
        self.pp = pp
        # add self.type = [type query]
        self.target = target  # maybe query
        self.disabled = disabled


class Stats:
    def __init__(self, atk, def_, spa, spd, spe):
        self.attack = atk
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
        self.player = None
        self.opponent = None
        self.weather = None
        self.field = None
        self.player_condition = None
        self.opponent_condition = None
        self.turn = 1

    def to_array(self):
        np.zeros(1)
