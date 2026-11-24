"""run_pass wiring: heroes-only mode picks only the selected hero and executes it (mocked scan)."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import unittest
from types import SimpleNamespace
from unittest import mock

from app.core import upgrader
from app.core.upgrade_menu import RESOURCE_DARK, RESOURCE_GOLD, SECTION_OTHER, UpgradeRow


def _row(label, cost, res):
    return UpgradeRow(label = label, section = SECTION_OTHER, cost = cost, resource = res, affordable = True, center = (1, 1), line_y = 1)


def _advisor(rows, chip = (3, 5)):
    adv = upgrader.UpgradeAdvisor.__new__(upgrader.UpgradeAdvisor)
    scan = SimpleNamespace(rows = rows, chip = chip, hud = (9_000_000, 9_000_000, 400_000))
    adv.scan = lambda: scan
    adv._corroborate_rows = lambda r: r
    adv._rows_without_cooldowns = lambda r: r
    adv._execute = mock.Mock(return_value = True)
    return adv


class HeroPassTests(unittest.TestCase):
    rows = [_row('Cannon', 100, RESOURCE_GOLD), _row('Archer Queen', 200_000, RESOURCE_DARK), _row('Barbarian King', 150_000, RESOURCE_DARK)]

    def test_heroes_mode_starts_only_the_chosen_hero(self):
        adv = _advisor(self.rows)
        res = adv.run_pass(upgrader.MODE_HEROES, reserve_builders = 1, hero_keys = ('queen',), hero_min_free = 2)
        self.assertEqual(res.pick.label, 'Archer Queen')
        self.assertTrue(res.executed)

    def test_heroes_mode_waits_without_enough_free_builders(self):
        adv = _advisor(self.rows, chip = (1, 5))
        res = adv.run_pass(upgrader.MODE_HEROES, reserve_builders = 1, hero_keys = ('queen',), hero_min_free = 2)
        self.assertIsNone(res.pick)
        adv._execute.assert_not_called()

    def test_dry_mode_with_heroes_does_not_execute(self):
        adv = _advisor(self.rows)
        res = adv.run_pass(upgrader.MODE_DRY, reserve_builders = 1, hero_keys = ('king',), hero_min_free = 2)
        self.assertEqual(res.pick.label, 'Barbarian King')
        adv._execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
