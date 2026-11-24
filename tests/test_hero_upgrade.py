"""Hero upgrades: row recognition, priority, free-builder rule, heroes-only mode, settings."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.upgrade_menu import RESOURCE_DARK, RESOURCE_ELIXIR, RESOURCE_GOLD, SECTION_OTHER, UpgradeRow
from app.core.upgrade_policy import UpgradePolicy, choose_upgrade, hero_key
from app.utils import profile_settings_store as store


def row(label, cost, resource):
    return UpgradeRow(label = label, section = SECTION_OTHER, cost = cost, resource = resource,
                      affordable = True, center = (1, 1), line_y = 1)


RESOURCES = (10_000_000, 10_000_000, 500_000)
ALL = ('king', 'queen', 'warden', 'champion', 'prince')


class HeroKeyTests(unittest.TestCase):
    def test_names_and_ocr_noise(self):
        self.assertEqual(hero_key(row('Barbarian King', 1, RESOURCE_DARK)), 'king')
        self.assertEqual(hero_key(row('Archer Oueen', 1, RESOURCE_DARK)), 'queen')
        self.assertEqual(hero_key(row('Barbarian Kinq', 1, RESOURCE_DARK)), 'king')
        self.assertEqual(hero_key(row('GRaNd Warden', 1, RESOURCE_ELIXIR)), 'warden')
        self.assertEqual(hero_key(row('Royal Champion', 1, RESOURCE_DARK)), 'champion')
        self.assertEqual(hero_key(row('Minion Prince', 1, RESOURCE_DARK)), 'prince')

    def test_buildings_are_not_heroes(self):
        for label in ('Cannon', 'Eagle Artillery', 'Laboratory', 'Barracks', 'Clan Castle'):
            self.assertIsNone(hero_key(row(label, 1, RESOURCE_GOLD)), label)


class ChooseTests(unittest.TestCase):
    rows = [row('Cannon', 5_000_000, RESOURCE_GOLD), row('Archer Queen', 200_000, RESOURCE_DARK),
            row('Barbarian King', 150_000, RESOURCE_DARK), row('Grand Warden', 9_000_000, RESOURCE_ELIXIR)]

    def test_cheapest_hero_wins_over_everything(self):
        policy = UpgradePolicy(hero_keys = ALL, hero_min_free = 2)
        self.assertEqual(choose_upgrade(self.rows, RESOURCES, 3, policy).label, 'Barbarian King')

    def test_only_selected_heroes(self):
        policy = UpgradePolicy(hero_keys = ('queen',), hero_min_free = 2)
        self.assertEqual(choose_upgrade(self.rows, RESOURCES, 3, policy).label, 'Archer Queen')

    def test_reserved_builder_stays_free(self):
        policy = UpgradePolicy(hero_keys = ALL, hero_min_free = 1, reserve_builders = 1)
        self.assertIsNone(choose_upgrade(self.rows, RESOURCES, 1, policy))

    def test_min_free_builders_gate_heroes_but_not_other_upgrades(self):
        policy = UpgradePolicy(hero_keys = ALL, hero_min_free = 3, reserve_builders = 1)
        pick = choose_upgrade(self.rows, RESOURCES, 2, policy)      # 2 free < 3: no hero this time
        self.assertEqual(pick.label, 'Archer Queen')                 # normal maxer rule applies (dark elixir first, priciest)

    def test_heroes_only_never_picks_other_rows(self):
        policy = UpgradePolicy(hero_keys = ('king',), hero_min_free = 2, heroes_only = True)
        rows = [row('Cannon', 1000, RESOURCE_GOLD)]
        self.assertIsNone(choose_upgrade(rows, RESOURCES, 3, policy))
        self.assertEqual(choose_upgrade(self.rows, RESOURCES, 3, policy).label, 'Barbarian King')

    def test_unaffordable_hero_is_skipped(self):
        policy = UpgradePolicy(hero_keys = ALL, hero_min_free = 2)
        rows = [row('Barbarian King', 900_000, RESOURCE_DARK), row('Cannon', 1000, RESOURCE_GOLD)]
        self.assertEqual(choose_upgrade(rows, RESOURCES, 3, policy).label, 'Cannon')


class SettingsTests(unittest.TestCase):
    def test_round_trip_and_normalising(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(store, 'get_settings_path', lambda: Path(d) / 's.json'):
            s = store.ProfileSettings(hero_upgrade = True, hero_selection = 'queen, bogus,king', hero_min_free_builders = 99)
            store.save_profile_settings(s)
            back = store.load_profile_settings()
            self.assertTrue(back.hero_upgrade)
            self.assertEqual(back.hero_selection, 'king,queen')
            self.assertEqual(back.hero_min_free_builders, store.HERO_MIN_FREE_MAX)

    def test_empty_selection_means_all(self):
        self.assertEqual(store._normalize_hero_selection(''), ','.join(store.HERO_KEYS))


if __name__ == '__main__':
    unittest.main()
