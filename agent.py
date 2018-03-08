from signal import signal, SIGTERM, SIGINT
from os import remove
from os.path import isfile
import ray
from ray.rllib import ppo
from ray.tune.registry import register_env, get_registry

from pokebattle_rl_env import PokeBattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator, DEFAULT_PUBLIC_CONNECTION

# works only with by placing rollout.py at rllib/ppo/rollout.py

env_creator_name = "PokeBattleEnv-v0"
register_env(env_creator_name, lambda config: PokeBattleEnv(ShowdownSimulator(self_play=True, debug_output=False)))

ray.init()
config = ppo.DEFAULT_CONFIG.copy()
config['num_workers'] = 2
config['timesteps_per_batch'] = 200
config['horizon'] = 500
config['min_steps_per_task'] = 1
agent = ppo.PPOAgent(config=config, env=env_creator_name, registry=get_registry())


def handle_exit(*_):
    if isfile('usernames'):
        remove('usernames')
    exit(0)


for sig in [SIGTERM, SIGINT]:
    signal(sig, handle_exit)

for i in range(1000):
    result = agent.train()
    print(f"result: {result}")
    if i % 10 == 0:
        agent.save()
