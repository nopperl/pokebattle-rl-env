from pokebattle_rl_env.battle_env import BattleEnv
import numpy as np

env = BattleEnv()
for i in range(100):
    env.reset()
    _, reward, done, _ = env.step(np.random.random(9))
    print(reward)
    while not done:
        _, reward, done, _ = env.step(np.random.random(9))
        print(reward)
env.close()
print('Finished')
