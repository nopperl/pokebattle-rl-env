from json import load

with open('data/abilities.json') as file:
    abilities = load(file)['BattleAbilities']

with open('data/items.json') as file:
    items = load(file)['BattleItems']

with open('data/moves.json') as file:
    moves = load(file)['BattleMovedex']

with open('data/pokedex.json') as file:
    pokedex = load(file)['BattlePokedex']

with open('data/typechart.json') as file:
    typechart = load(file)['BattleTypeChart']

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
