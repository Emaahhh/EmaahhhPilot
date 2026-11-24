"""Treasury: nearby taps are tried until the Treasury button shows (mocked game)."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import threading
import unittest
from unittest import mock

from app.core import bot as botmod


def _bot(hit_on_tap):
    b = botmod.Bot.__new__(botmod.Bot)
    b.stop_event = threading.Event()
    b.window = mock.Mock(); b.window.screenshot.return_value = mock.Mock(shape = (1440, 2560, 3))
    b.input = mock.Mock(); b.vision = mock.Mock(); b.config = mock.Mock()
    b.config.get_point.return_value = (50, 50)
    b._update_config_size = lambda f: None
    b._check_stop = lambda: None
    b.vision.find_template.return_value = (10, 10)
    b._find_learned_castle = lambda frame: (1200, 740)
    b._rebase_loot_after_collect = mock.Mock()
    taps = {'n': 0}

    def click(x, y, **kw):
        if (x, y) != (50, 50):
            taps['n'] += 1
    b.input.click.side_effect = click

    def wait(tpl, **kw):
        if tpl == 'treasury_btn.png':
            return (1700, 1160) if taps['n'] >= hit_on_tap else (None, None)
        return {'treasury_collect.png': (1300, 1000), 'okay.png': (1500, 900)}.get(tpl, (None, None))
    b._wait_for_image = wait
    return b


class TreasuryRetryTests(unittest.TestCase):
    def test_third_tap_hits_the_castle(self):
        b = _bot(3)
        self.assertTrue(b._treasury_now())
        b._rebase_loot_after_collect.assert_called_once()

    def test_never_hits_means_nothing_pressed_afterwards(self):
        b = _bot(10 ** 6)
        self.assertFalse(b._treasury_now())
        self.assertEqual(sum(1 for c in b.input.click.call_args_list if c.args[:2] != (50, 50)), len(botmod._TREASURY_TAP_OFFSETS))


if __name__ == '__main__':
    unittest.main()
