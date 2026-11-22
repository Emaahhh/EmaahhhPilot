'''Stuck-screen loop (Attack never reached) and a faster Stop.'''
import _testenv  # noqa: F401 — must precede the app imports (test log folder)
import threading
import time
import unittest
from unittest.mock import Mock, patch


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
    for name in ('_return_home', '_home_screen_recovery', '_maybe_upgrade_walls', '_maybe_auto_upgrade',
                 '_maybe_idle', '_multi_run_collect_home_village_resources'):
        setattr(bot, name, Mock())
    bot._scroll_point = Mock(return_value = (100, 100))
    bot.config.get_point = Mock(return_value = [10, 10])
    return bot


class StuckScreenTests(unittest.TestCase):

    def test_attack_button_missing_is_reported_as_stuck(self):
        bot = _bot()
        bot._find_template_once = Mock(return_value = (None, None))
        bot._wait_for_attack_with_nudge = Mock(return_value = (None, None))
        self.assertEqual(bot._find_match_and_attack(1), 'stuck')

    def test_timed_run_stops_after_stuck_limit(self):
        from app.core.bot import _STUCK_CYCLE_LIMIT
        bot = _bot()
        bot._find_match_and_attack = Mock(return_value = 'stuck')
        with self.assertLogs('BotCore', level = 'WARNING') as logs:
            bot._run_loop(1, 3600)
        self.assertEqual(bot._find_match_and_attack.call_count, _STUCK_CYCLE_LIMIT)
        self.assertTrue(any('stopping' in line for line in logs.output))
        bot._return_home.assert_not_called()  # no battle → no 20 s post-battle wait

    def test_run_until_maxed_backs_off_then_continues(self):
        from app.core.bot import _IDLE_RECHECK_SECONDS, _STUCK_CYCLE_LIMIT
        bot = _bot()
        bot._find_match_and_attack = Mock(return_value = 'stuck')
        # The back-off wait is where the user's Stop lands.
        bot.stop_event.wait.side_effect = lambda s: s == _IDLE_RECHECK_SECONDS
        with self.assertLogs('BotCore', level = 'WARNING'):
            bot._run_loop(1, 0)
        self.assertEqual(bot._find_match_and_attack.call_count, _STUCK_CYCLE_LIMIT)

    def test_successful_attack_resets_the_stuck_counter(self):
        from app.core.bot import _STUCK_CYCLE_LIMIT
        bot = _bot()
        outcomes = (['stuck'] * (_STUCK_CYCLE_LIMIT - 1) + [None]) * 2 + ['stuck'] * _STUCK_CYCLE_LIMIT
        bot._find_match_and_attack = Mock(side_effect = outcomes)
        with self.assertLogs('BotCore', level = 'WARNING'):
            bot._run_loop(1, 3600)
        self.assertEqual(bot._find_match_and_attack.call_count, len(outcomes))


class FastStopTests(unittest.TestCase):

    def service(self, ev):
        from app.services.input import InputService
        ws = Mock()
        ws.hwnd = 1
        ws.get_outer_pixel_size.return_value = (2560, 1440)
        svc = InputService(ws, ev)
        svc.user32 = Mock()
        svc.user32.ClientToScreen.return_value = 0
        return svc

    def test_click_pause_ends_when_stop_is_pressed(self):
        ev = threading.Event()
        svc = self.service(ev)
        threading.Timer(0.1, ev.set).start()
        t0 = time.monotonic()
        svc.click(10, 10, pause = 5)
        self.assertLess(time.monotonic() - t0, 1.0)

    def test_no_clicks_after_stop(self):
        ev = threading.Event()
        ev.set()
        svc = self.service(ev)
        svc.click(10, 10)
        svc.click_at(10, 10)
        svc.scroll(10, 10, 20)
        svc.user32.SendMessageW.assert_not_called()

    def test_scroll_is_interrupted(self):
        ev = threading.Event()
        svc = self.service(ev)
        threading.Timer(0.15, ev.set).start()
        t0 = time.monotonic()
        svc.scroll(10, 10, 20, pause = (0.1, 0.1))
        self.assertLess(time.monotonic() - t0, 0.6)
        self.assertLess(svc.user32.SendMessageW.call_count, 20)


if __name__ == '__main__':
    unittest.main()
