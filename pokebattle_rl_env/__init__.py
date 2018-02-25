from gym.envs.registration import register
from pokebattle_rl_env.pokebattle_env import PokeBattleEnv
register(
    id='PokeBattleEnv-v0',
    entry_point='pokemon_battle_rl_env.battle_env:BattleEnv'
)
