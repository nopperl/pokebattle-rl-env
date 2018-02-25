from unittest import TestCase, main

from pokebattle_rl_env.poke_data_queries import move_name_to_id, get_move_by_name


class TestQueries(TestCase):
    def test_move_name_to_id(self):
        move_id = move_name_to_id('Iron Head')
        self.assertEqual(move_id, 'ironhead')
        move_id = move_name_to_id('Z-Belly Drum')
        self.assertEqual(move_id, 'bellydrum')

    def test_get_move_by_name(self):
        move = get_move_by_name('Iron Head')
        self.assertEqual(move['name'], 'Iron Head')
        move = get_move_by_name('Z-Belly Drum')
        self.assertEqual(move['name'], 'Belly Drum')


if __name__ == '__main__':
    main()
