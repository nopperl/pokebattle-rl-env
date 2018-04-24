import numpy as np

from pokebattle_rl_env.pokebattle_env import PokeBattleEnv
from pokebattle_rl_env.showdown_simulator import ShowdownSimulator, DEFAULT_PUBLIC_CONNECTION

env = PokeBattleEnv(ShowdownSimulator(connection=DEFAULT_PUBLIC_CONNECTION))
for i in range(100):
    env.reset()
    _, reward, done, _ = env.step(np.random.random(11))
    env.render()
    print(reward)
    while not done:
        _, reward, done, _ = env.step(np.random.random(11))
        print(reward)
env.close()
print('Finished')
