from gym import Env
from gym.spaces import Box, MultiBinary

from pokemon_battle_rl_env.showdown_simulator import ShowdownSimulator


class BattleEnv(Env):
    def __init__(self, simulator=ShowdownSimulator()):
        self.__version__ = "0.1.0"
        self.simulator = simulator
        self.action_space = MultiBinary(10)  # Attack using one of 4 moves, switch to one of 5 pokemon or pass
        # ToDo set self.observation_space
        self.reward_range = (-1, 1)
        # ToDo: Set metadata['render.modes']

    def _step(self, action):
        self.simulator.attack(1)
        reward = 1 if self.simulator.state.state == 'won' else -1 if self.simulator.state.state == 'lost' else 0
        return self.simulator.state.to_array(), reward, self.simulator.state.state != 'ongoing', None

    def _reset(self):
        pass

    def render(self, mode='human', close=False):
        if close:
            raise NotImplementedError('Closing after render not yet implemented')
        if mode == 'rgb_array':
            raise NotImplementedError('rendering rgb_arrays not yet implemented')
        if mode is 'human':
            raise NotImplementedError('rendering in human mode not yet implemented')

        else:
            super().render(mode=mode, close=close)

    def _close(self):
        self.simulator.close()

    def _seed(self, seed=None):
        pass
