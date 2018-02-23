from unittest import TestCase, main
from pokebattle_rl_env.battle_simulator import BattleSimulator
from pokebattle_rl_env.game_state import Move


class TestValidActions(TestCase):
    def setUp(self):
        self.simulator = BattleSimulator()
        self.simulator.state.player.pokemon[0].moves = [Move(id='tackle') for i in range(4)]
        self.simulator.state.player.pokemon[0].unknown = False

    def test_recharge(self):
        self.simulator.state.player.pokemon[0].recharge = True
        self.simulator.state.player.pokemon[0].trapped = True
        valid_actions = self.simulator.get_available_actions()
        self.assertEqual(len(valid_actions), 1)
        self.assertEqual(valid_actions[0].mode, 'attack')
        self.assertEqual(valid_actions[0].number, 1)

    def test_force_switch(self):
        self.simulator.state.player.force_switch = True
        valid_actions = self.simulator.get_available_actions()
        self.assertEqual(len(valid_actions), 5)
        self.assertTrue(all([action.mode == 'switch' for action in valid_actions]))

    def test_trapped(self):
        self.simulator.state.player.pokemon[0].trapped = True
        valid_actions = self.simulator.get_available_actions()
        self.assertEqual(len(valid_actions), 4)
        self.assertTrue(all([action.mode == 'attack' for action in valid_actions]))

    def test_disabled_moves(self):
        self.simulator.state.player.pokemon[0].moves[2].disabled = True
        valid_actions = self.simulator.get_available_actions()
        self.assertEqual(len(valid_actions), 8)
        self.assertFalse(any([action.mode == 'attack' and action.number == 3 for action in valid_actions]))

    def test_locked_move_first_index(self):
        self.simulator.state.player.pokemon[0].locked_move_first_index = True
        self.simulator.state.player.pokemon[0].moves[1].disabled = True
        self.simulator.state.player.pokemon[0].moves[2].disabled = True
        self.simulator.state.player.pokemon[0].moves[3].disabled = True
        valid_actions = self.simulator.get_available_actions()
        self.assertEqual(len(valid_actions), 6)
        self.assertTrue(valid_actions[0].mode == 'attack' and valid_actions[0].number == 1)


if __name__ == '__main__':
    main()
