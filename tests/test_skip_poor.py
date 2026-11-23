"""Skip poor bases: loot reading and the Next loop (mocked game)."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import threading
import unittest
from unittest import mock

from app.core import bot as botmod
from app.utils.profile_settings_store import ProfileSettings, load_profile_settings, save_profile_settings


def _bot(loots, min_loot = 600_000, next_found = True):
    b = botmod.Bot.__new__(botmod.Bot)
    b.stop_event = threading.Event()
    b._skip_min_loot = min_loot
    b.window = mock.Mock()
    b.window.screenshot.return_value = mock.Mock()
    b.input = mock.Mock()
    b.vision = mock.Mock()
    b.vision.find_template.return_value = (2300, 1100) if next_found else (None, None)
    b._update_config_size = lambda f: None
    b._check_stop = lambda: None
    seq = iter(loots)
    b._read_scout_loot = lambda attempts = 4: next(seq)
    b._wait_for_battle_start = mock.Mock(return_value = (152, 1134))
    return b


class SkipTests(unittest.TestCase):
    def test_rich_base_is_attacked_at_once(self):
        b = _bot([(400_000, 300_000, 5000)])
        self.assertTrue(b._skip_poor_bases())
        b.input.click.assert_not_called()

    def test_poor_bases_are_skipped_until_a_rich_one(self):
        b = _bot([(100_000, 120_000, 0), (200_000, 100_000, 0), (500_000, 400_000, 0)])
        self.assertTrue(b._skip_poor_bases())
        self.assertEqual(b.input.click.call_count, 2)

    def test_unreadable_loot_attacks(self):
        b = _bot([None])
        self.assertTrue(b._skip_poor_bases())
        b.input.click.assert_not_called()

    def test_limit_per_attack(self):
        b = _bot([(1, 1, 0)] * 20)
        self.assertTrue(b._skip_poor_bases())
        self.assertEqual(b.input.click.call_count, botmod._SKIP_MAX_PER_ATTACK)

    def test_missing_next_button_attacks(self):
        b = _bot([(1, 1, 0)] * 3, next_found = False)
        self.assertTrue(b._skip_poor_bases())
        b.input.click.assert_not_called()

    def test_lost_battle_screen_reports_false(self):
        b = _bot([(1, 1, 0)] * 3)
        b._wait_for_battle_start = mock.Mock(return_value = (None, None))
        self.assertFalse(b._skip_poor_bases())


class SettingsRoundTripTests(unittest.TestCase):
    def test_threshold_is_saved_and_clamped(self):
        original = load_profile_settings()
        try:
            save_profile_settings(ProfileSettings(skip_min_loot_k = 900))
            self.assertEqual(load_profile_settings().skip_min_loot_k, 900)
            save_profile_settings(ProfileSettings(skip_min_loot_k = 10 ** 9))
            self.assertEqual(load_profile_settings().skip_min_loot_k, 6000)
        finally:
            save_profile_settings(original)


if __name__ == '__main__':
    unittest.main()
