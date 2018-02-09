from pokemon_battle_rl_env.game_state import GameState


class BattleSimulator:
    num_actions = 9  # Attack using one of 4 moves, switch to one of 5 pokemon

    def __init__(self):
        self.state = GameState()

    def _attack(self, move):
        raise NotImplementedError

    def _switch(self, pokemon):
        raise NotImplementedError

    def act(self, mode, number):
        if mode == 'attack':
            self._attack(number)
        elif mode == 'switch':
            self._switch(number)
        else:
            raise ValueError(f'Invalid action mode {mode}')
        self._update_state()

    def _update_state(self):
        raise NotImplementedError

    def render(self, mode='human'):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
