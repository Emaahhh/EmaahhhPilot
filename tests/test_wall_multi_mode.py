"""Wall batch: Upgrade More must really open the batch bar, else the single wall is paid."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import threading
import unittest
from unittest import mock

from app.core import bot as botmod


def _bot(upgrade_more_gone_after):
    b = botmod.Bot.__new__(botmod.Bot)
    b.stop_event = threading.Event()
    b.window = mock.Mock()
    b.window.screenshot.return_value = mock.Mock(shape = (1440, 2560, 3))
    b.input = mock.Mock()
    b.config = mock.Mock(aspect_key = botmod.ASPECT_16_9)
    b._update_config_size = lambda f: None
    b._check_stop = lambda: None
    state = {'taps': 0}
    b.input.click.side_effect = lambda *a, **k: state.__setitem__('taps', state['taps'] + 1)
    b._find_upgrade_more = lambda f: (None, None, 1.0) if state['taps'] >= upgrade_more_gone_after else (1500, 1200, 1.0)
    return b, state


class EnterMultiModeTests(unittest.TestCase):
    def test_first_tap_works(self):
        b, state = _bot(1)
        with mock.patch.object(botmod.time, 'sleep'):
            self.assertTrue(b._enter_multi_mode(1500, 1200))
        self.assertEqual(state['taps'], 1)

    def test_retaps_when_the_first_tap_is_lost(self):
        b, state = _bot(2)
        self.assertTrue(b._enter_multi_mode(1500, 1200))
        self.assertEqual(state['taps'], 2)

    def test_gives_up_after_three_taps(self):
        b, state = _bot(99)
        self.assertFalse(b._enter_multi_mode(1500, 1200))
        self.assertEqual(state['taps'], 3)


class TwoRowBarTests(unittest.TestCase):
    '''Live 24/11 (wall level 13): Remove / +10 / +1 on top, gold / elixir / Wall Ring below.'''

    def test_roi_covers_the_top_row_buttons(self):
        b, _ = _bot(1)
        pair = mock.Mock()
        pair.gold.center = (716, 1240)
        frame = mock.Mock(shape = (1440, 2560, 3))
        (x, y, w, h) = b._wall_bar_roi_two_rows(frame, pair, 0.9)
        for (px, py) in ((730, 1090), (934, 1090), (1140, 1090)):
            self.assertTrue(x <= px <= x + w and y <= py <= y + h, (px, py))
        self.assertLess(y + h, 1240)  # never reaches the pay-button row

    def test_find_in_bar_falls_back_to_the_two_row_strip(self):
        b, _ = _bot(1)
        pair = mock.Mock()
        pair.gold.center = (716, 1240)
        frame = mock.Mock(shape = (1440, 2560, 3))
        seen = []

        def finder(f, region = None):
            seen.append(region)
            return (1140, 1090) if len(seen) == 2 else (None, None)
        self.assertEqual(b._find_in_bar(finder, frame, pair, 0.9), (1140, 1090))
        self.assertEqual(len(seen), 2)


class BatchFallbackTests(unittest.TestCase):
    def test_pays_the_single_wall_when_the_batch_bar_never_opens(self):
        b, _state = _bot(99)
        b._pay_single_wall = mock.Mock(return_value = True)
        b._deselect_wall_ui = mock.Mock()
        b._upgrade_walls_pick_resource_and_okay = mock.Mock()
        b._upgrade_walls_batch(1500, 1200)
        b._pay_single_wall.assert_called_once()
        b._upgrade_walls_pick_resource_and_okay.assert_not_called()

    def test_no_add_wall_clicks_on_a_single_bar(self):
        b, _state = _bot(99)
        b._pay_single_wall = mock.Mock(return_value = False)
        b._deselect_wall_ui = mock.Mock()
        with mock.patch.object(botmod.VisionService, 'find_active_addwall') as add:
            b._upgrade_walls_batch(1500, 1200)
        add.assert_not_called()
        b._deselect_wall_ui.assert_called_once()


if __name__ == '__main__':
    unittest.main()
