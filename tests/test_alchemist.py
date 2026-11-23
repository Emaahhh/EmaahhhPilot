"""Helper Hut / Alchemist flow (mocked game)."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import threading
import unittest
from unittest import mock

from app.core import bot as botmod


def _bot():
    b = botmod.Bot.__new__(botmod.Bot)
    b.stop_event = threading.Event()
    b.window = mock.Mock()
    b.window.screenshot.return_value = mock.Mock(shape = (1440, 2560, 3))
    b.input = mock.Mock()
    b.vision = mock.Mock()
    b.config = mock.Mock()
    b._update_config_size = lambda f: None
    b._check_stop = lambda: None
    b._rebase_loot_after_collect = mock.Mock()
    b._use_alchemist = True
    b._alchemist_last = 0.0
    return b


class AlchemistTests(unittest.TestCase):
    def test_off_does_nothing(self):
        b = _bot(); b._use_alchemist = False
        b._alchemist_now = mock.Mock()
        b._maybe_use_alchemist(force = True)
        b._alchemist_now.assert_not_called()

    def test_interval(self):
        b = _bot(); b._alchemist_now = mock.Mock(return_value = True)
        b._maybe_use_alchemist(force = True)
        b._maybe_use_alchemist()
        self.assertEqual(b._alchemist_now.call_count, 1)

    def test_full_flow_presses_convert(self):
        b = _bot()
        b.vision.find_template.return_value = (10, 10)  # home screen visible
        b._find_helper_hand = lambda: (500, 400)
        waits = {'alchemist_btn.png': (700, 900), 'convert.png': (1800, 1000), 'convert_confirm.png': (1300, 1090), 'exit.png': (2300, 100)}
        b._wait_for_image = lambda tpl, **kw: waits.get(tpl, (None, None))
        self.assertTrue(b._alchemist_now())
        clicked = [c.args[:2] for c in b.input.click.call_args_list]
        self.assertEqual(clicked[:4], [(500, 400), (700, 900), (1800, 1000), (1300, 1090)])
        b._rebase_loot_after_collect.assert_called_once()

    def test_no_hand_no_clicks(self):
        b = _bot()
        b.vision.find_template.return_value = (10, 10)
        b._find_helper_hand = lambda: (None, None)
        b._find_helper_hut = lambda: (None, None)
        self.assertFalse(b._alchemist_now())
        b.input.click.assert_not_called()

    def test_missing_convert_button_closes_and_does_not_press(self):
        b = _bot()
        b.vision.find_template.return_value = (10, 10)
        b._find_helper_hand = lambda: (500, 400)
        waits = {'alchemist_btn.png': (700, 900)}
        b._wait_for_image = lambda tpl, **kw: waits.get(tpl, (None, None))
        b.config.get_point.return_value = (5, 5)
        self.assertFalse(b._alchemist_now())
        b._rebase_loot_after_collect.assert_not_called()

    def test_hut_used_when_hand_hidden(self):
        b = _bot()
        b.vision.find_template.return_value = (10, 10)
        b._find_helper_hand = lambda: (None, None)
        b._find_helper_hut = lambda: (900, 700)
        waits = {'alchemist_btn.png': (700, 900), 'convert.png': (1800, 1000), 'convert_confirm.png': (1300, 1090)}
        b._wait_for_image = lambda tpl, **kw: waits.get(tpl, (None, None))
        self.assertTrue(b._alchemist_now())
        self.assertEqual(b.input.click.call_args_list[0].args[:2], (900, 700))

    def test_no_confirmation_means_not_converted(self):
        b = _bot()
        b.vision.find_template.return_value = (10, 10)
        b._find_helper_hand = lambda: (500, 400)
        waits = {'alchemist_btn.png': (700, 900), 'convert.png': (1800, 1000)}
        b._wait_for_image = lambda tpl, **kw: waits.get(tpl, (None, None))
        b.config.get_point.return_value = (5, 5)
        self.assertFalse(b._alchemist_now())
        b._rebase_loot_after_collect.assert_not_called()

    def test_not_home_screen(self):
        b = _bot()
        b.vision.find_template.return_value = (None, None)
        self.assertFalse(b._alchemist_now())
        b.input.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
