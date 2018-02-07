from pokemon_battle_rl_env.game_state import GameState


class BattleSimulator:
    def __init__(self):
        self.state = GameState()

    def attack(self, move):
        raise NotImplementedError

    def switch(self, pokemon):
        raise NotImplementedError

    def render(self, mode='human'):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
