from math import exp

import numpy as np
from gym import Env
from gym.envs.registration import EnvSpec
from gym.spaces import Box

from pokebattle_rl_env.showdown_simulator import ShowdownSimulator

TURN_THRESHOLD = 10


def softmax(x):
    return np.exp(x) / np.sum(np.exp(x), axis=0)


def sigmoid(x):
    return 1 / (1 + exp(-x))


class PokeBattleEnv(Env):
    def __init__(self, simulator=ShowdownSimulator()):
        self.__version__ = "0.1.0"
        self._spec = EnvSpec('PokeBattleEnv-v0')
        self.simulator = simulator
        num_actions = len(self.simulator.get_available_actions()) + len(self.simulator.get_available_modifiers())
        self.action_space = Box(low=0.0, high=1.0, shape=(num_actions,), dtype=np.float32)
        state_dimensions = len(self.simulator.state.to_array())
        self.observation_space = Box(low=0, high=1000, shape=(state_dimensions,), dtype=np.float32)
        self.reward_range = (-1, 1)
        # ToDo: Set metadata['render.modes']

    def get_action(self, action_probs):
        valid_actions = self.simulator.get_available_actions()
        if len(valid_actions) == 0:
            from pickle import dump
            from pokebattle_rl_env.util import generate_token
            with open(generate_token(5), 'wb') as file:
                dump(self.simulator.state, file)
        estimates = []
        for valid_action in valid_actions:
            if valid_action.mode == 'attack':
                action_ix = valid_action.number - 1
            elif valid_action.mode == 'switch':
                action_ix = valid_action.number + 2
            else:
                continue
            estimates.append(action_probs[action_ix])
        estimates = softmax(estimates)
        action = np.random.choice(valid_actions, p=estimates)
        return action

    def get_action_modifier(self, action_probs):
        valid_modifiers = self.simulator.get_available_modifiers()
        modifiers = []
        for valid_modifier in valid_modifiers:
            prob = 0
            if valid_modifier == 'mega':
                prob = action_probs[len(action_probs) - 1]
            prob = sigmoid(prob)
            if np.random.binomial(1, prob):
                modifiers.append(valid_modifier)
        return modifiers

    def compute_reward(self):
        if not (self.simulator.state.forfeited and self.simulator.state.turn < TURN_THRESHOLD):
            if self.simulator.state.state == 'win':
                return 1
            elif self.simulator.state.state == 'loss':
                return -1
        return 0

    def step(self, action):
        game_action = self.get_action(action)
        modifiers = self.get_action_modifier(action)
        self.simulator.act(game_action, modifiers)
        observation = self.simulator.state.to_array()
        reward = self.compute_reward()  # ToDo: Maybe negative reward for assigning probability to invalid action
        done = self.simulator.state.state in ['win', 'loss', 'tie']
        return observation, reward, done, None

    def reset(self):
        self.simulator.reset()
        return self.simulator.state.to_array()

    def render(self, mode='human'):
        return
        if mode == 'rgb_array':
            raise NotImplementedError('rendering rgb_arrays not yet implemented')
        if mode is 'human':
            raise NotImplementedError('rendering in human mode not yet implemented')

        else:
            super().render(mode=mode)

    def close(self):
        self.simulator.close()

    def seed(self, seed=None):
        pass
