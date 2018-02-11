from json import loads
from pkgutil import get_data

abilities = loads(get_data('pokebattle_rl_env', 'data/abilities.json'))['BattleAbilities']
items = loads(get_data('pokebattle_rl_env', 'data/items.json'))['BattleItems']
moves = loads(get_data('pokebattle_rl_env', 'data/moves.json'))['BattleMovedex']
pokedex = loads(get_data('pokebattle_rl_env', 'data/pokedex.json'))['BattlePokedex']
typechart = loads(get_data('pokebattle_rl_env', 'data/typechart.json'))['BattleTypeChart']

genders = ['f', 'm', 'n']
status_conditions = ['brn', 'par', 'slp', 'frz', 'psn', 'tox', 'confusion', 'trapped']
targets = ['all', 'normal', 'self']
weathers = ['raindance', 'primordialsea', 'sunnyday', 'desolateland', 'sandstorm', 'hail', 'deltastream']


def move_id_to_name(id):
    return moves[id]['name']


def move_name_to_id(name):
    return next(m['id'] for m in moves.values() if m['name'] == name)


def get_move_by_name(name):
    return next(m for m in moves.values() if m['name'] == name)


def get_pokemon_by_species(species):
    return next(p for p in pokedex.values() if p['species'] == species)
