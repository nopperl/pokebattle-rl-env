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
    def __init__(self, name, gender, stats, moves, ability, item, health=1.0, condition=''):
        self.name = name
        self.health = health
        self.condition = condition
        self.gender = gender
        self.stats = stats
        self.moves = moves
        self.ability = ability
        self.item = item


class Trainer:
    def __init__(self, pokemon, name=None, mega_used=False):
        self.name = name
        self.pokemon = pokemon
        self.mega_used = mega_used


class GameState:
    def __init__(self):
        self.state = 'ongoing'
        self.player = None
        self.opponent = None
        self.weather = None
        self.turn = 1

    def to_array(self):
        np.zeros(1)
