from pokebattle_rl_env.battle_env import BattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator
import numpy as np

env = BattleEnv(ShowdownSimulator(local=False, debug_output=True))
for i in range(100):
    env.reset()
    _, reward, done, _ = env.step(np.random.random(11))
    print(reward)
    while not done:
        _, reward, done, _ = env.step(np.random.random(11))
        print(reward)
env.close()
print('Finished')
