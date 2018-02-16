from unittest import TestCase, main
from websocket import WebSocket
from pokebattle_rl_env.showdown_simulator import *
from pokebattle_rl_env.util import generate_username


class TestAuthentication(TestCase):
    def setUp(self):
        self.ws = WebSocket(sslopt={'check_hostname': False})
        self.ws.connect(url='wss://sim.smogon.com/showdown/websocket')
        msg = ''
        while not msg.startswith('|challstr|'):
            msg = self.ws.recv()
        self.challstr = msg[msg.find('|challstr|') + len('|challstr|'):]
        self.ws.settimeout(.5)

    def test_auth_temp_user(self):
        username = generate_username()
        assertion = auth_temp_user(self.challstr, username)
        login_cmd = f'|/trn {username},0,{assertion}'
        self.ws.send(login_cmd)

    def test_login(self):
        with open('auth.txt', 'r') as file:
            username, password = file.read().splitlines()
        assertion = login(self.challstr, username, password)
        login_cmd = f'|/trn {username},0,{assertion}'
        self.ws.send(login_cmd)

    def _username_in_msg(self, username):
        msg = ''
        while not msg.startswith('|updateuser|'):
            msg = self.ws.recv()
        self.assertIn(username, msg)

    def tearDown(self):
        self.ws.close()


class TestMsgParsing(TestCase):
    def test_ident_to_name(self):
        name = ident_to_name('p1a: Metagross')
        self.assertEqual(name, 'Metagross')


if __name__ == '__main__':
    main()
