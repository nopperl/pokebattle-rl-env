from signal import signal, SIGTERM, SIGINT
from os import remove
import ray
from ray.rllib import ppo
from ray.tune.registry import register_env, get_registry

from pokebattle_rl_env import BattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator

env_creator_name = "PokeBattleEnv-v0"
register_env(env_creator_name, lambda config: BattleEnv(ShowdownSimulator(self_play=True, debug_output=True)))

ray.init()
config = ppo.DEFAULT_CONFIG.copy()
config['num_workers'] = 10
config['timesteps_per_batch'] = 50
config['horizon'] = 1000
config['min_steps_per_task'] = 6
agent = ppo.PPOAgent(config=config, env=env_creator_name, registry=get_registry())


def handle_exit(*_):
    remove('usernames')
    exit(0)


for sig in [SIGTERM, SIGINT]:
    signal(sig, handle_exit)

for i in range(1000):
    result = agent.train()
    print(f"result: {result}")
    if i % 10 == 0:
        agent.save()
