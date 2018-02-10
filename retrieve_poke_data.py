from requests import get
from os.path import join, splitext
from os import remove
from json import dump
from execjs import eval

data_dir = 'pokemon_battle_rl_env/data'
filenames = ['abilities.js', 'items.js', 'moves.js', 'pokedex.js', 'typechart.js']
for filename in filenames:
    url = join('https://raw.githubusercontent.com/Zarel/Pokemon-Showdown/master/data', filename)
    response = get(url)
    file_path = join('.', data_dir, filename)
    with open(file_path, 'w') as file:
        file.write(response.text)
    json = eval(f'require("{file_path}")')
    with open(splitext(file_path)[0] + '.json', 'w') as file:
        dump(json, file)
    remove(file_path)
