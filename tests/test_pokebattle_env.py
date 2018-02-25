from unittest import TestCase, main
from pokebattle_rl_env import PokeBattleEnv
from pokebattle_rl_env.pokebattle_env import TURN_THRESHOLD


class MyTestCase(TestCase):
    def test_reward(self):
        env = PokeBattleEnv()
        self.assertEqual(env.reward_range, (-1, 1))
        env.simulator.state.turn = TURN_THRESHOLD
        env.simulator.state.state = 'loss'
        env.simulator.state.forfeited = False
        self.assertEqual(env.compute_reward(), -1)
        env.simulator.state.forfeited = True
        self.assertEqual(env.compute_reward(), -1)
        env.simulator.state.state = 'win'
        self.assertEqual(env.compute_reward(), 1)
        env.simulator.state.forfeited = False
        self.assertEqual(env.compute_reward(), 1)
        env.simulator.state.turn = TURN_THRESHOLD - 1
        self.assertEqual(env.compute_reward(), 1)
        env.simulator.state.forfeited = True
        self.assertEqual(env.compute_reward(), 0)
        env.simulator.state.state = 'loss'
        self.assertEqual(env.compute_reward(), 0)
        env.simulator.state.forfeited = False
        self.assertEqual(env.compute_reward(), -1)
        env.simulator.state.state = 'init'
        self.assertEqual(env.compute_reward(), 0)
        env.simulator.state.state = 'ongoing'
        self.assertEqual(env.compute_reward(), 0)


if __name__ == '__main__':
    main()
