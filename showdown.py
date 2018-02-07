from json import loads

import websocket
from requests import post

WEB_SOCKET_URL = "ws://sim.smogon.com:8000/showdown/websocket"


def authenticate(ws, challstr, username, password):
    post_data = {'act': 'login', 'name': username, 'pass': password, 'challstr': challstr}
    response = post('http://play.pokemonshowdown.com/action.php', data=post_data)
    assertion = loads(response.text[1:])['assertion']
    login_cmd = f'|/trn {username},0,{assertion}'
    ws.send(login_cmd)
    msg = ''
    while not msg.startswith('updateuser') and username in msg:
        msg = ws.recv()


def battle(ws, room_id, username):
    msg = ''
    opponent = username
    while opponent == username:
        while '|player|' not in msg:
            msg = ws.recv()
            print(msg)
        opponent = msg.split('|')[3]

    print(f'Playing against {opponent}')

    ws.send(f'{room_id}|/timer on')


ws = websocket.WebSocket(sslopt={'check_hostname': False})
ws.connect(WEB_SOCKET_URL)
print('Connected')
try:
    msg = ''
    while not msg.startswith('|challstr|'):
        msg = ws.recv()
    challstr = msg.split('|')[1]
    with open('auth.txt', 'r') as file:
        username, password = file.readlines()
    authenticate(ws, challstr, username, password)
    ws.send('|/utm null')  # Team
    ws.send('|/search gen7randombattle')  # Tier
    msg = ''
    while '|init|battle' not in msg:
        msg = ws.recv()
    room_id = msg.split('\n')[0][1:]
    battle(ws, room_id, username)
finally:
    ws.close()
    print('Connection closed')
