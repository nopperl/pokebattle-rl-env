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
        self.target = target
        self.disabled = disabled


class Stats:
    def __init__(self, atk, def_, spa, spd, spe):
        self.attack = atk
        self.def_ = def_
        self.spa = spa
        self.spd = spd
        self.spe = spe


class Pokemon:
    def __init__(self, name, gender, stats, moves, ability, item, health=1.0):
        self.name = name
        self.health = health
        self.gender = gender
        self.stats = stats
        self.moves = moves
        self.ability = ability
        self.item = item


class Trainer:
    def __init__(self, pokemon, name=None):
        self.pokemon = pokemon
        self.name = name


class GameState:
    def __init__(self):
        self.state = 'ongoing'

    def to_array(self):
        np.zeros(1)
