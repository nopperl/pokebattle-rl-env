from json import load

MOVES_PATH = 'data/moves.json'
with open('data/moves.json') as file:
    moves = load(file)


def move_id_to_name(id):
    return moves[id]['name']


def move_name_to_id(name):
    return next(m['id'] for m in moves.values() if m['name'] == name)


def get_move_by_name(name):
    return next(m for m in moves.values() if m['name'] == name)
