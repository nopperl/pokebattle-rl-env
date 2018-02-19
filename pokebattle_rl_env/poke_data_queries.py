from json import loads
from pkgutil import get_data

abilities = loads(get_data('pokebattle_rl_env', 'data/abilities.json'))['BattleAbilities']
items = loads(get_data('pokebattle_rl_env', 'data/items.json'))['BattleItems']
moves = loads(get_data('pokebattle_rl_env', 'data/moves.json'))['BattleMovedex']
pokedex = loads(get_data('pokebattle_rl_env', 'data/pokedex.json'))['BattlePokedex']
typechart = loads(get_data('pokebattle_rl_env', 'data/typechart.json'))['BattleTypeChart']

genders = ['f', 'm', 'n']
status_conditions = ['brn', 'par', 'slp', 'frz', 'psn', 'tox', 'confusion']
targets = ['all', 'normal', 'self']
weathers = [move['weather'] for move in moves.values() if 'weather' in move]
side_conditions = [move['sideCondition'] for move in moves.values() if 'sideCondition' in move]
terrains = [move['terrain'] for move in moves.values() if 'terrain' in move]
pseudoWeathers = [move['pseudoWeather'] for move in moves.values() if 'pseudoWeather' in move]
field_effects = terrains + pseudoWeathers


def ability_name_to_id(name):
    return next(a['id'] for a in abilities.values() if a['name'] == name)


def move_id_to_name(id):
    return moves[id]['name']


def move_name_to_id(name):
    move_id = next((m['id'] for m in moves.values() if m['name'] == name), None)
    if move_id is not None:
        return move_id
    elif name.startswith('Z-'):
        name = name[2:]
        return move_name_to_id(name)
    raise StopIteration


def item_name_to_id(name):
    return next(i['id'] for i in items.values() if i['name'] == name)


def get_move_by_name(name):
    move = next((m for m in moves.values() if m['name'] == name), None)
    if move is not None:
        return move
    elif name.startswith('Z-'):
        name = name[2:]
        return get_move_by_name(name)
    raise StopIteration


def get_pokemon_by_species(species):
    return next(p for p in pokedex.values() if p['species'] == species)
