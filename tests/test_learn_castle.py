"""Learn Clan Castle: selection box detection and the tap-until-Treasury loop (mocked game)."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from app.core import bot as botmod


def _village():
    rng = np.random.default_rng(1)
    return rng.integers(60, 140, (1440, 2560, 3), dtype=np.uint8)


class SelectionLabelTests(unittest.TestCase):
    def test_label_block_is_found(self):
        base = _village()
        sel = base.copy()
        sel[656:726, 1269:1405] = 255          # name + level label above the selected building
        sel[1000:1100, 900:1500] = 255         # selection bar title: must be ignored
        (x, y) = botmod.Bot._selection_label(sel, base)
        self.assertTrue(1300 <= x <= 1380 and 670 <= y <= 710)

    def test_no_change_means_none(self):
        base = _village()
        self.assertIsNone(botmod.Bot._selection_label(base, base.copy()))


class LearnLoopTests(unittest.TestCase):
    def _bot(self, hit_after):
        b = botmod.Bot.__new__(botmod.Bot)
        b.stop_event = threading.Event()
        base = _village()
        sel = base.copy(); sel[656:726, 1269:1405] = 255
        state = {'taps': 0, 'selected': True}
        b.window = mock.Mock()
        b.window.screenshot.side_effect = lambda: sel if state['selected'] else base
        b.input = mock.Mock()

        def click(x, y, **kw):
            if (x, y) == (50, 50):              # "empty" tap: deselect
                state['selected'] = False
                return
            state['taps'] += 1
            state['selected'] = state['taps'] >= hit_after
        b.input.click.side_effect = click
        b.vision = mock.Mock()
        b.vision.find_template.side_effect = lambda f, tpl, **kw: (5, 5) if (f is sel and tpl == 'treasury_btn.png') else (None, None)
        b.config = mock.Mock(); b.config.get_point.return_value = (50, 50)
        b._update_config_size = lambda f: None
        b._scroll_point = lambda: (1, 1)
        return b, state

    def test_learns_when_a_candidate_hits_the_castle(self):
        b, state = self._bot(hit_after=3)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(botmod.Bot, 'castle_template_path', staticmethod(lambda: Path(d) / 'c.png')), mock.patch.object(botmod.time, 'sleep'):
            (ok, msg) = b.learn_clan_castle()
            self.assertTrue(ok, msg)
            self.assertTrue((Path(d) / 'c.png').exists())

    def test_fails_cleanly_when_nothing_hits(self):
        b, state = self._bot(hit_after=10 ** 6)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(botmod.Bot, 'castle_template_path', staticmethod(lambda: Path(d) / 'c.png')), mock.patch.object(botmod.time, 'sleep'):
            (ok, msg) = b.learn_clan_castle()
            self.assertFalse(ok)
            self.assertFalse((Path(d) / 'c.png').exists())


if __name__ == '__main__':
    unittest.main()
