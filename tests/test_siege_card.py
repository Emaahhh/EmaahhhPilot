"""Siege machine card: by picture when known, else the card left of the first hero."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import unittest
from unittest import mock

import numpy as np

from app.core.strategies import AttackStrategy


def _strategy(matches):
    s = AttackStrategy.__new__(AttackStrategy)
    s.vision = mock.Mock()
    s.vision.find_template.side_effect = lambda f, t, **k: matches.get(t, (None, None))
    return s


def _frame(card_at = None):
    f = np.zeros((1440, 2560, 3), dtype = np.uint8)
    if card_at:
        f[1250:1420, card_at - 70:card_at + 70] = (230, 160, 40)  # bright blue card
    return f


# Live 25/11: heroes at 972 / 1134 / 1292, siege card centre at ~808.
HEROES = [(1292, 1329), (1134, 1330), (972, 1332)]


class SiegeCardTests(unittest.TestCase):
    def test_known_picture(self):
        s = _strategy({'siegebarracks.png': (808, 1307)})
        self.assertEqual(s._find_siege_card(_frame(), None), (808, 1307))

    def test_unknown_machine_is_the_card_left_of_the_first_hero(self):
        (x, y) = _strategy({})._card_left_of_heroes(_frame(808), HEROES)
        self.assertLess(abs(x - 808), 20)
        self.assertEqual(y, 1332)

    def test_empty_slot_is_left_alone(self):
        self.assertIsNone(_strategy({})._card_left_of_heroes(_frame(), HEROES))

    def test_troop_card_further_left_is_not_taken(self):
        # No machine: the last troop card sits ~198 px left of the first hero, so the spot one
        # pitch left only overlaps its right part.
        self.assertIsNone(_strategy({})._card_left_of_heroes(_frame(972 - 198), HEROES))

    def test_matches_above_the_bar_are_ignored(self):
        self.assertIsNone(_strategy({})._card_left_of_heroes(_frame(808), [(111, 1064)]))

    def test_unknown_machine_is_deployed_after_the_heroes(self):
        s = _strategy({'RC.png': (972, 1332)})
        s.input, s.stop_event, s.event_handler, s.config = mock.Mock(), None, None, mock.Mock()
        s._random_hero_point = mock.Mock(return_value = (500, 500))
        s.deploy_heroes(_frame(808))
        clicked = [c.args for c in s.input.click.call_args_list]
        self.assertEqual(len(clicked), 4)  # hero card, map, siege card, map
        self.assertLess(abs(clicked[2][0] - 808), 20)


if __name__ == '__main__':
    unittest.main()
