import ray
from ray.rllib import ppo
from ray.tune.registry import register_env, get_registry

from pokebattle_rl_env import BattleEnv

env_creator_name = "PokeBattleEnv-v0"
register_env(env_creator_name, lambda config: BattleEnv())

ray.init()
config = ppo.DEFAULT_CONFIG.copy()
config['num_workers'] = 5
agent = ppo.PPOAgent(config=config, env=env_creator_name, registry=get_registry())


for i in range(1000):
    result = agent.train()
    print(f"result: {result}")
    if i % 10 == 0:
        agent.save()
