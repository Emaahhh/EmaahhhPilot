'''Attack cycle fixes found live on 22/11:
- the failed Valkyrie-recipe step closed the army window and Attack! was then pressed on
  the village (no battle, troops "not found");
- a cycle whose battle never started still ran the deploy;
- the army trained (Super Minions) was not the one picked (Valkyries).'''
import _testenv  # noqa: F401 — must precede the app imports (test log folder)
import unittest
from unittest.mock import Mock


def _bot():
    from app.config import Config
    from app.core.bot import Bot
    bot = Bot.__new__(Bot)
    bot.config = Config()
    bot.stop_event = Mock()
    bot.stop_event.is_set.return_value = False
    bot.stop_event.wait.return_value = False
    bot.window = Mock()
    bot.window.screenshot.return_value = Mock(shape = (1440, 2560, 3), size = 1)
    bot._update_config_size = Mock()
    bot.input = Mock()
    bot.vision = Mock()
    bot._status_callback = None
    bot._battle_rewards = Mock()
    bot._loot_snapshot_before_attack = Mock()
    bot._wait_for_battle_end = Mock()
    return bot


def _images(present):
    '''_wait_for_image / _find_template_once stand-in: (1, 1) for the names in ``present``.'''
    def look(name, *args, **kwargs):
        return (100, 200) if name in present else (None, None)
    return look


class ArmyWindowReopenTests(unittest.TestCase):

    def test_reopens_through_find_a_match(self):
        bot = _bot()
        screens = iter([set(), {'farmbattle.png'}, {'attack2.png'}])
        state = {'now': set()}

        def wait_for_image(name, *a, **k):
            if name == 'attack2.png' and not state['now']:
                state['now'] = next(screens)  # first look: window gone
                return (None, None)
            return (100, 200) if name in state['now'] else (None, None)

        def click(*a, **k):
            state['now'] = next(screens, state['now'])

        bot._wait_for_image = Mock(side_effect = wait_for_image)
        bot._find_template_once = Mock(return_value = (None, None))
        bot._wait_for_attack_with_nudge = Mock(return_value = (50, 60))
        bot.input.click = Mock(side_effect = click)
        self.assertEqual(bot._army_attack_button('farmbattle.png'), (100, 200))
        clicked = [c.args[:2] for c in bot.input.click.call_args_list]
        self.assertEqual(clicked[0], (50, 60))    # home Battle
        self.assertEqual(clicked[1], (100, 200))  # Find a Match

    def test_gives_up_when_home_is_not_reachable(self):
        bot = _bot()
        bot._wait_for_image = Mock(return_value = (None, None))
        bot._find_template_once = Mock(return_value = (None, None))
        bot._wait_for_attack_with_nudge = Mock(return_value = (None, None))
        self.assertEqual(bot._army_attack_button('farmbattle.png'), (None, None))
        bot.input.click.assert_not_called()


class AttackCycleTests(unittest.TestCase):

    def cycle_bot(self):
        bot = _bot()
        bot._find_template_once = Mock(return_value = (None, None))
        bot._wait_for_attack_with_nudge = Mock(return_value = (10, 20))
        bot._wait_for_image = Mock(side_effect = _images({'farmbattle.png', 'attack2.png'}))
        return bot

    def test_battle_that_never_starts_is_stuck_and_deploys_nothing(self):
        bot = self.cycle_bot()
        bot._wait_for_any_image = Mock(return_value = (None, None))
        bot._get_strategy = Mock()
        self.assertEqual(bot._find_match_and_attack(2), 'stuck')
        bot._get_strategy.assert_not_called()

    def test_other_army_on_the_bar_is_used(self):
        bot = self.cycle_bot()
        bot._wait_for_any_image = Mock(return_value = (5, 5))  # Surrender: battle on
        picked = Mock()
        picked.execute.return_value = False   # Valkyries not on the bar
        actual = Mock()
        actual.execute.return_value = True    # Super Minions are
        bot._get_strategy = Mock(side_effect = lambda m: {3: picked, 2: actual}[m])
        bot._ensure_valkyrie_army_from_recipes = Mock(return_value = True)
        bot._detect_army_method = Mock(return_value = 2)
        with self.assertLogs('BotCore', level = 'WARNING') as logs:
            self.assertIsNone(bot._find_match_and_attack(3))
        actual.execute.assert_called_once()
        self.assertEqual(bot._attacks_done, 1)
        self.assertTrue(any('Super Minions' in line for line in logs.output))

    def test_no_supported_army_is_a_troop_failure(self):
        bot = self.cycle_bot()
        bot._wait_for_any_image = Mock(return_value = (5, 5))
        picked = Mock()
        picked.execute.return_value = False
        bot._get_strategy = Mock(return_value = picked)
        bot._detect_army_method = Mock(return_value = None)
        self.assertEqual(bot._find_match_and_attack(2), 'troop')

    def test_failed_recipe_step_finds_attack_again(self):
        bot = self.cycle_bot()
        bot._wait_for_any_image = Mock(return_value = (5, 5))
        strat = Mock()
        strat.execute.return_value = True
        bot._get_strategy = Mock(return_value = strat)
        bot._ensure_valkyrie_army_from_recipes = Mock(return_value = False)
        bot._army_attack_button = Mock(return_value = (300, 400))
        with self.assertLogs('BotCore', level = 'WARNING'):
            bot._find_match_and_attack(3)
        bot._army_attack_button.assert_called_once_with('farmbattle.png')
        self.assertIn((300, 400), [c.args[:2] for c in bot.input.click.call_args_list])


if __name__ == '__main__':
    unittest.main()
