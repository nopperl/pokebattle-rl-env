import numpy as np
from gym import Env
from gym.envs.registration import EnvSpec
from gym.spaces import Box

from pokebattle_rl_env.showdown_simulator import ShowdownSimulator


class BattleEnv(Env):
    def __init__(self, simulator=ShowdownSimulator()):
        self.__version__ = "0.1.0"
        self._spec = EnvSpec('PokeBattleEnv-v0')
        self.simulator = simulator
        self.action_space = Box(low=0.0, high=1.0, shape=(self.simulator.num_actions,))
        state_dimensions = len(self.simulator.state.to_array())
        self.observation_space = Box(low=0, high=1000, shape=(state_dimensions,))
        self.reward_range = (-1, 1)
        # ToDo: Set metadata['render.modes']

    def step(self, action):
        action = np.argmax(action)  # ToDo: Handle forced switches (eg Roar) and moves (eg Outrage)
        if action < 4:
            self.simulator.act('attack', action + 1)
        else:
            self.simulator.act('switch', action - 2)
        reward = 1 if self.simulator.state.state == 'won' else -1 if self.simulator.state.state == 'lost' else 0
        return self.simulator.state.to_array(), reward, self.simulator.state.state != 'ongoing', None

    def reset(self):
        self.simulator.reset()
        return self.simulator.state.to_array()

    def render(self, mode='human'):
        return
        if close:
            raise NotImplementedError('Closing after render not yet implemented')
        if mode == 'rgb_array':
            raise NotImplementedError('rendering rgb_arrays not yet implemented')
        if mode is 'human':
            raise NotImplementedError('rendering in human mode not yet implemented')

        else:
            super().render(mode=mode, close=close)

    def close(self):
        self.simulator.close()

    def seed(self, seed=None):
        pass
