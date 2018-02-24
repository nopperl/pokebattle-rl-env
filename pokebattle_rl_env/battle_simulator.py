from pokebattle_rl_env.game_state import GameState
from pokebattle_rl_env.poke_data_queries import items


class Action:
    def __init__(self, mode, number):
        self.mode = mode
        self.number = number


default_actions = [Action(mode='attack', number=i) for i in range(1, 5)] + [Action(mode='switch', number=i) for i in
                                                                            range(2, 7)]
default_action_modifiers = ['mega', 'z']


class BattleSimulator:
    def __init__(self):
        self.state = GameState()

    def _attack(self, move, mega=False, z=False):
        raise NotImplementedError

    def _switch(self, pokemon):
        raise NotImplementedError

    def get_available_actions(self):
        actions = []
        if all([p.unknown for p in self.state.player.pokemon]):
            return default_actions
        active = self.state.player.pokemon[0]
        if not self.state.player.force_switch:
            if active.recharge:
                actions.append(Action('attack', 1))
            else:
                enabled_moves_ix = 1
                for i in range(len(active.moves)):
                    if not active.moves[i].disabled:
                        ix = enabled_moves_ix if active.locked_move_first_index else i + 1
                        actions.append(Action('attack', ix))
        if not active.trapped:
            for i in range(1, len(self.state.player.pokemon)):
                pokemon = self.state.player.pokemon[i]
                if pokemon.health > 0:
                    actions.append(Action('switch', i + 1))
        return actions

    def get_available_modifiers(self):
        if all([p.unknown for p in self.state.player.pokemon]):
            return default_action_modifiers
        modifiers = []
        active = self.state.player.pokemon[0]
        if active.item not in items:
            return []
        item = items[active.item]
        if 'megaEvolves' in item and item['megaEvolves'] == active.species:
            modifiers.append('mega')
        return modifiers
        if 'zMove' in item or False:  # ToDo: Better z move integration. Not all the active pokemons move can be used as z move
            if 'zMoveUser' in item and item['zMoveUser'] == active.species:
                modifiers.append('z')
            elif 'zMoveType' in item and item['zMoveType'] in active.types:
                modifiers.append('z')
        return modifiers

    def act(self, action, modifiers):
        self.state.player.force_switch = False
        if action.mode == 'attack':
            self._attack(action.number, 'mega' in modifiers, 'z' in modifiers)
        elif action.mode == 'switch':
            self._switch(action.number)
        else:
            raise ValueError(f'Invalid action mode {action.mode}')
        self._update_state()

    def _update_state(self):
        raise NotImplementedError

    def render(self, mode='human'):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
