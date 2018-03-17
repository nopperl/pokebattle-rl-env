from argparse import ArgumentParser

import ray
from ray.rllib import ppo
from ray.tune.registry import register_env, get_registry

from pokebattle_rl_env import PokeBattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator

parser = ArgumentParser()
parser.add_argument('-l', '--load', type=str, help='The directory to load a trained model from')
parser.add_argument('-b', '--battles', type=int, default=1000, help='Amount of battles to test the model')
args = parser.parse_args()

env = PokeBattleEnv(ShowdownSimulator(self_play=False))
env_creator_name = "PokeBattleEnv-v0"
register_env(env_creator_name, lambda config: env)

ray.init()
config = ppo.DEFAULT_CONFIG.copy()
config['num_workers'] = 1
config['timesteps_per_batch'] = 200
config['horizon'] = 500
config['min_steps_per_task'] = 1
agent = ppo.PPOAgent(config=config, env=env_creator_name, registry=get_registry())

agent.restore(args.load)

for battle in range(args.battles):
    observation = env.reset()
    env.render()
    done = False
    while not done:
        action = agent.compute_action(observation)
        observation, _, done, _ = env.step(action)
