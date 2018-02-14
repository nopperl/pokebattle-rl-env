from pokebattle_rl_env.battle_env import BattleEnv
import numpy as np

env = BattleEnv()
for i in range(100):
    env.reset()
    done = env.step(np.random.random(9))
    while not done:
        done = env.step(np.random.random(9))
env.close()
print('Finished')
