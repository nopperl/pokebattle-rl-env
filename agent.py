from argparse import ArgumentParser
from datetime import datetime
from os import makedirs, remove
from os.path import isdir, isfile, join

import ray
from ray.rllib import ppo
from ray.tune.registry import register_env, get_registry

from pokebattle_rl_env import PokeBattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator

# works only with by placing rollout.py at rllib/ppo/rollout.py

parser = ArgumentParser()
parser.add_argument('-o', '--output', type=str, default='', help='Path to the output directory for the learned model')
parser.add_argument('-i', '--iterations', type=int, default=1000, help='Amount of iterations to train the model in')
parser.add_argument('-s', '--save-iterations', type=int, default=10, help='Amount of iterations between each model save')
parser.add_argument('-b', '--batch-steps', type=int, default=200, help='The amount of steps to collect for each training batch')
parser.add_argument('-w', '--workers', type=int, default=2, help='The number of actors to use.')
parser.add_argument('-r', '--restore', type=str, default=None, help='The directory to restore a saved model from')
args = parser.parse_args()

output_path = join(args.output, datetime.today().strftime('%Y-%m-%d-%H-%M-%S'))
logging_path = join(output_path, 'log.txt')
if not isdir(output_path):
    makedirs(output_path)

if isfile('usernames'):
    remove('usernames')

env_creator_name = "PokeBattleEnv-v0"
register_env(env_creator_name, lambda config: PokeBattleEnv(ShowdownSimulator(self_play=False, logging_file=logging_path)))

ray.init()
config = ppo.DEFAULT_CONFIG.copy()
config['num_workers'] = args.workers
config['timesteps_per_batch'] = args.batch_steps
config['horizon'] = 500
config['min_steps_per_task'] = 1
config['gamma'] = 1
config['model']['fcnet_hiddens'] = [2000, 500, 100]
agent = ppo.PPOAgent(config=config, env=env_creator_name, registry=get_registry())

if args.restore is not None:
    agent.restore(args.restore)

for i in range(args.iterations):
    result = agent.train()
    print(f"result: {result}")
    if i % args.save_iterations == 0:
        agent.save(checkpoint_dir=output_path)
