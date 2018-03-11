from argparse import ArgumentParser
from os import remove
from os.path import isfile
import ray
from ray.rllib import ppo
from ray.tune.registry import register_env, get_registry

from pokebattle_rl_env import PokeBattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator, DEFAULT_PUBLIC_CONNECTION

# works only with by placing rollout.py at rllib/ppo/rollout.py

parser = ArgumentParser()
parser.add_argument('-o', '--output', type=str, default='', help='Path to the output directory for the learned model')
parser.add_argument('-i', '--iterations', type=str, default=1000, help='Amount of iterations to train the model in')
parser.add_argument('-s', '--save-iterations', type=str, default=10, help='Amount of iterations between each model save')
args = parser.parse_args()

if isfile('usernames'):
    remove('usernames')

env_creator_name = "PokeBattleEnv-v0"
register_env(env_creator_name, lambda config: PokeBattleEnv(ShowdownSimulator(self_play=True, debug_output=False)))

ray.init()
config = ppo.DEFAULT_CONFIG.copy()
config['num_workers'] = 2
config['timesteps_per_batch'] = 200
config['horizon'] = 500
config['min_steps_per_task'] = 1
agent = ppo.PPOAgent(config=config, env=env_creator_name, registry=get_registry())

for i in range(args.iterations):
    result = agent.train()
    print(f"result: {result}")
    if i % args.save_iterations == 0:
        agent.save(checkpoint_dir=args.output)
