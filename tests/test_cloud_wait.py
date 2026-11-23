"""Matchmaking clouds must not be mistaken for a battle that never started."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import threading
import unittest
from unittest import mock

import numpy as np

from app.core import bot as botmod


def _frame(value):
    return np.full((1440, 2560, 3), value, dtype=np.uint8)


class CloudWaitTests(unittest.TestCase):
    def test_detector(self):
        self.assertTrue(botmod._looks_like_clouds(_frame(235)))
        self.assertFalse(botmod._looks_like_clouds(_frame(90)))
        green = _frame(0); green[:, :, 1] = 200
        self.assertFalse(botmod._looks_like_clouds(green))

    def _bot(self):
        b = botmod.Bot.__new__(botmod.Bot)
        b.stop_event = threading.Event()
        b.window = mock.Mock()
        return b

    def test_waits_through_clouds_then_battle(self):
        b = self._bot()
        b.window.screenshot.return_value = _frame(240)
        calls = {'n': 0}
        def fake_wait(templates, timeout=10, error=True, **kw):
            calls['n'] += 1
            return (5, 6) if calls['n'] == 3 else (None, None)
        b._wait_for_any_image = fake_wait
        self.assertEqual(b._wait_for_battle_start(base_timeout=0, clouds_timeout=60), (5, 6))
        self.assertEqual(calls['n'], 3)

    def test_gives_up_when_not_clouds(self):
        b = self._bot()
        b.window.screenshot.return_value = _frame(80)
        b._wait_for_any_image = lambda *a, **k: (None, None)
        self.assertEqual(b._wait_for_battle_start(base_timeout=0, clouds_timeout=60), (None, None))


if __name__ == '__main__':
    unittest.main()
