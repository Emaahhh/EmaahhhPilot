'''History, log filters, settings persistence, hotkey, tray, schedule, collect, single wall.'''
import _testenv  # noqa: F401 — must precede the app imports (test log folder)
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QDateTime
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget
except ImportError:  # pragma: no cover
    QApplication = None


def _app():
    app = QApplication.instance() or QApplication([])
    from app.ui.qt.theme import apply_theme
    apply_theme(app)
    return app


class _TempAppData(unittest.TestCase):
    '''Point LOCALAPPDATA at a temp folder: nothing touches the real settings / history.'''

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {'LOCALAPPDATA': self._tmp.name})
        self._env.start()
        import app.utils.common as common
        self._mig = mock.patch.object(common, '_migration_checked', True)
        self._mig.start()

    def tearDown(self):
        self._mig.stop()
        self._env.stop()
        self._tmp.cleanup()


def _session(**kw):
    base = {'village': 'home', 'duration_s': 3600, 'attacks': 40, 'gold': 8_000_000, 'elixir': 7_000_000, 'dark': 50_000, 'walls': 3}
    base.update(kw)
    return base


class HistoryStoreTests(_TempAppData):

    def test_append_load_and_clear(self):
        from app.utils import history_store as h
        self.assertEqual(h.load_history(), [])
        self.assertIsNotNone(h.append_session(_session(), 'Super Minions'))
        self.assertIsNotNone(h.append_session(_session(attacks = 10), 'Valkyries'))
        sessions = h.load_history()
        self.assertEqual([s['army'] for s in sessions], ['Super Minions', 'Valkyries'])
        self.assertEqual(sessions[0]['gold'], 8_000_000)
        h.clear_history()
        self.assertEqual(h.load_history(), [])

    def test_empty_runs_are_not_saved(self):
        from app.utils import history_store as h
        self.assertIsNone(h.append_session(_session(attacks = 0, walls = 0), 'Valkyries'))
        self.assertEqual(h.load_history(), [])

    def test_corrupt_file_reads_as_empty_and_is_replaced(self):
        from app.utils import history_store as h
        h.get_history_path().parent.mkdir(parents = True, exist_ok = True)
        h.get_history_path().write_text('{not json', encoding = 'utf-8')
        self.assertEqual(h.load_history(), [])
        h.append_session(_session(), 'Edrags')
        self.assertEqual(len(h.load_history()), 1)

    def test_history_is_capped(self):
        from app.utils import history_store as h
        with mock.patch.object(h, 'MAX_SESSIONS', 5):
            for i in range(8):
                h.append_session(_session(attacks = i + 1), 'Edrags')
        self.assertEqual([s['attacks'] for s in h.load_history()], [4, 5, 6, 7, 8])

    def test_summary_and_per_army_yield(self):
        from app.utils import history_store as h
        a = h._clean(dict(_session(), army = 'Super Minions', ended = '2026-11-20T10:00:00'))
        b = h._clean(dict(_session(attacks = 20, gold = 2_000_000, elixir = 1_000_000), army = 'Valkyries', ended = '2026-11-21T10:00:00'))
        bb = h._clean(dict(_session(village = 'builder', attacks = 12, gold = 0, elixir = 0), army = 'Baby Dragon', ended = '2026-11-21T12:00:00'))
        total = h.summarize([a, b, bb])
        self.assertEqual(total['sessions'], 3)
        self.assertEqual(total['attacks'], 72)
        self.assertEqual(total['gold'], 10_000_000)
        self.assertAlmostEqual(total['gold_per_attack'], 10_000_000 / 60)  # Builder Base attacks carry no loot
        rows = h.by_army([a, b, bb])
        self.assertEqual(rows[0]['army'], 'Super Minions')  # best loot per hour first
        self.assertAlmostEqual(rows[0]['gold_per_attack'], 200_000)
        series = h.loot_per_hour_series([a, b, bb])
        self.assertEqual(len(series), 2)  # Builder Base runs are not in the loot chart

    def test_history_page_fills_in(self):
        _app()
        from app.utils import history_store as h
        from app.ui.qt.pages.history import HistoryPage
        h.append_session(_session(), 'Super Minions')
        page = HistoryPage()
        page.resize(900, 900)
        page.show()
        QTest.qWait(30)
        self.assertEqual(page._t_sessions.text(), '1')
        self.assertEqual(page._t_attacks.text(), '40')
        self.assertTrue(page.grab().width() > 0)  # chart + tables paint without error
        page.close()


class LogFilterTests(unittest.TestCase):

    LINES = [
        '2026-11-22 12:00:00 - BotCore - INFO - Bot started',
        '2026-11-22 12:00:05 - BotCore - WARNING - Timeout waiting for attack.png',
        '2026-11-22 12:00:06 - BotCore - ERROR - Bot crashed: boom',
        'Traceback (most recent call last):',
        '  File "x.py", line 1',
        '2026-11-22 12:00:07 - BotCore - INFO - Recovery: clicking Return Home']

    def test_traceback_lines_inherit_the_error_level(self):
        from app.ui.qt.pages.logs import parse_log_lines
        (records, last) = parse_log_lines(self.LINES)
        self.assertEqual([lvl for (lvl, _t) in records], ['INFO', 'WARNING', 'ERROR', 'ERROR', 'ERROR', 'INFO'])
        self.assertEqual(last, 'INFO')

    def test_warnings_and_errors_only(self):
        from app.ui.qt.pages.logs import filter_records, parse_log_lines
        (records, _l) = parse_log_lines(self.LINES)
        shown = [t for (_lvl, t) in filter_records(records, issues_only = True)]
        self.assertEqual(len(shown), 4)
        self.assertNotIn(self.LINES[0], shown)

    def test_search_is_case_insensitive_and_combines_with_level(self):
        from app.ui.qt.pages.logs import filter_records, parse_log_lines
        (records, _l) = parse_log_lines(self.LINES)
        self.assertEqual(len(filter_records(records, query = 'RETURN home')), 1)
        self.assertEqual(len(filter_records(records, issues_only = True, query = 'return home')), 0)
        self.assertEqual(len(filter_records(records, query = '')), 6)

    @unittest.skipIf(QApplication is None, 'PySide6 not installed')
    def test_page_filters_live(self):
        _app()
        from app.ui.qt.pages.logs import LogsPage, parse_log_lines
        page = LogsPage()
        (records, _l) = parse_log_lines(self.LINES)
        page._records.extend(records)
        page._render()
        self.assertEqual(page._log_view.document().blockCount(), 6)
        page._on_level_changed(1)
        self.assertEqual(page._log_view.document().blockCount(), 4)
        page._search.setText('timeout')
        self.assertEqual(page._log_view.document().blockCount(), 1)
        self.assertIn('1 of 6', page._count.text())


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class SettingsPersistenceTests(_TempAppData):

    def test_every_field_survives_a_save_and_a_later_auto_save(self):
        _app()
        from app.ui.qt.pages.settings import SettingsPage
        from app.utils.profile_settings_store import load_profile_settings
        page = SettingsPage()
        page._wall_order.setCurrentIndex(1)
        page._notifications.setChecked(False)
        page._tray_on_close.setChecked(True)
        page._stop_hotkey.setChecked(False)
        page._wall_threshold.setValue(7)
        loaded = load_profile_settings()
        self.assertEqual((loaded.wall_order, loaded.notifications, loaded.tray_on_close, loaded.stop_hotkey, loaded.wall_upgrade_threshold_m),
                         ('highest', False, True, False, 7))
        # Changing something else must not reset the new fields to their defaults.
        page._reserve_builders.setValue(3)
        again = load_profile_settings()
        self.assertEqual((again.wall_order, again.notifications, again.tray_on_close, again.stop_hotkey, again.reserve_builders),
                         ('highest', False, True, False, 3))
        # ... and a page re-created later shows what was saved.
        fresh = SettingsPage()
        fresh._reload_earthquake()
        self.assertEqual((fresh._wall_order.currentIndex(), fresh._tray_on_close.isChecked(), fresh._notifications.isChecked()), (1, True, False))

    def test_defaults_and_garbage_values(self):
        from app.utils import profile_settings_store as s
        s.get_settings_path().write_text('{"wall_order": "sideways", "notifications": "maybe", "tray_on_close": 1}', encoding = 'utf-8')
        loaded = s.load_profile_settings()
        self.assertEqual((loaded.wall_order, loaded.notifications, loaded.tray_on_close, loaded.stop_hotkey), ('lowest', True, True, True))


@unittest.skipIf(QApplication is None or sys.platform != 'win32', 'Windows only')
class HotkeyTests(unittest.TestCase):

    def test_registers_receives_and_releases(self):
        _app()
        from app.services import hotkey as hk
        # Ctrl+Alt+Shift+F9: unlikely to be taken, so the test does not depend on another app.
        key = hk.GlobalHotkey(vk = 0x78, modifiers = 0x0002 | 0x0001 | 0x0004, label = 'Ctrl+Alt+Shift+F9')
        got = []
        key.pressed.connect(lambda: got.append(1))
        key.start()
        try:
            self.assertTrue(key.is_active())
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(key._thread_id, hk.WM_HOTKEY, hk._HOTKEY_ID, 0)
            deadline = time.time() + 2
            while not got and time.time() < deadline:
                QTest.qWait(20)
            self.assertEqual(got, [1])
        finally:
            key.stop()
        self.assertFalse(key.is_active())

    def test_second_registration_of_the_same_key_reports_failure(self):
        _app()
        from app.services import hotkey as hk
        a = hk.GlobalHotkey(vk = 0x79, modifiers = 0x0002 | 0x0001 | 0x0004, label = 'Ctrl+Alt+Shift+F10')
        b = hk.GlobalHotkey(vk = 0x79, modifiers = 0x0002 | 0x0001 | 0x0004, label = 'Ctrl+Alt+Shift+F10')
        failed = []
        b.registrationFailed.connect(lambda label: failed.append(label))
        a.start()
        try:
            b.start()
            QTest.qWait(100)
            self.assertFalse(b.is_active())
            self.assertEqual(failed, ['Ctrl+Alt+Shift+F10'])
        finally:
            b.stop()
            a.stop()


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class TrayNotificationTests(_TempAppData):

    def tray(self):
        from app.ui.qt.tray import TrayController
        controller = mock.Mock()
        controller.is_running.return_value = False
        window = QWidget()
        tray = TrayController(window, controller, mock.Mock(spec = []))
        tray.notify = mock.Mock()
        tray._window_keepalive = window
        return tray

    def test_stuck_lines_are_recognised(self):
        from app.ui.qt.tray import needs_attention
        self.assertTrue(needs_attention('Screen stuck: Attack button not reached 5 times in a row — stopping. Check the game window'))
        self.assertTrue(needs_attention('Troops not found 4 times in a row — stopping. Check the army / saved recipe.'))
        self.assertFalse(needs_attention('Troops not found (1/4) — retrying in 15s.'))
        self.assertFalse(needs_attention('Upgrading walls...'))

    def test_natural_end_notifies_with_the_numbers(self):
        _app()
        tray = self.tray()
        tray._on_started()
        tray._on_summary({'village': 'home', 'attacks': 18, 'gold': 11_725_001, 'elixir': 11_584_346})
        tray._on_finished(None)
        title, text = tray.notify.call_args.args
        self.assertEqual(title, 'Run finished')
        self.assertIn('18 attacks', text)
        self.assertIn('11.7M gold', text)

    def test_user_stop_is_silent_error_and_stuck_notify(self):
        _app()
        tray = self.tray()
        tray._on_started()
        tray._on_status('Stopping...', False)
        tray._on_finished(None)
        tray.notify.assert_not_called()
        tray._on_finished('boom')
        self.assertEqual(tray.notify.call_args.args[0], 'Bot stopped with an error')
        tray.notify.reset_mock()
        tray._on_status('Screen stuck: Attack button not reached 5 times in a row — stopping.', True)
        self.assertEqual(tray.notify.call_args.args[0], 'Bot needs attention')

    def test_notifications_respect_the_setting_and_do_not_repeat(self):
        _app()
        from app.ui.qt.tray import TrayController
        from app.utils.profile_settings_store import ProfileSettings, save_profile_settings
        controller = mock.Mock()
        tray = TrayController(QWidget(), controller, mock.Mock(spec = []))
        shown = []
        tray._tray = mock.Mock()
        tray._tray.showMessage = lambda *a: shown.append(a)
        save_profile_settings(ProfileSettings(notifications = False))
        tray.notify('T', 'm')
        self.assertEqual(shown, [])
        save_profile_settings(ProfileSettings(notifications = True))
        tray.notify('T', 'm')
        tray.notify('T', 'm')  # same text within the repeat window
        self.assertEqual(len(shown), 1)

    def test_close_hides_only_when_enabled(self):
        _app()
        from app.ui.qt.tray import TrayController
        from app.utils.profile_settings_store import ProfileSettings, save_profile_settings
        tray = TrayController(QWidget(), mock.Mock(), mock.Mock(spec = []))
        tray._tray = mock.Mock()
        tray._tray.isVisible.return_value = True
        save_profile_settings(ProfileSettings(tray_on_close = False))
        self.assertFalse(tray.hide_on_close())
        save_profile_settings(ProfileSettings(tray_on_close = True))
        self.assertTrue(tray.hide_on_close())
        tray.quitting = True  # the menu's Quit must really close
        self.assertFalse(tray.hide_on_close())


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class ScheduledStartTests(_TempAppData):

    def page(self):
        from app.ui.qt.pages.run import RunPage
        controller = mock.Mock()
        controller.is_running.return_value = False
        page = RunPage(controller, lambda key: None)
        page.start_bot = mock.Mock()
        self.messages = []
        page.scheduleMessage.connect(self.messages.append)
        return (page, controller)

    def test_due_schedule_starts_once_unattended_and_switches_off(self):
        _app()
        (page, _c) = self.page()
        page._schedule_on.setChecked(True)
        page._schedule_target = QDateTime.currentDateTime().addSecs(-30)
        page._tick_schedule()
        page.start_bot.assert_called_once_with(unattended = True)
        self.assertFalse(page._schedule_on.isChecked())
        page._tick_schedule()
        page.start_bot.assert_called_once()

    def test_not_yet_due_does_nothing_and_shows_a_countdown(self):
        _app()
        (page, _c) = self.page()
        page._schedule_on.setChecked(True)
        page._schedule_target = QDateTime.currentDateTime().addSecs(3 * 3600 + 120)
        page._tick_schedule()
        page.start_bot.assert_not_called()
        self.assertIn('in 3h', page._schedule_row.subtitle.text())

    def test_missed_or_busy_schedule_notifies_instead_of_starting(self):
        _app()
        (page, controller) = self.page()
        page._schedule_on.setChecked(True)
        page._schedule_target = QDateTime.currentDateTime().addSecs(-3600)
        page._tick_schedule()
        self.assertIn('missed', self.messages[-1])
        page._schedule_on.setChecked(True)
        controller.is_running.return_value = True
        page._schedule_target = QDateTime.currentDateTime().addSecs(-5)
        page._tick_schedule()
        self.assertIn('already in progress', self.messages[-1])
        page.start_bot.assert_not_called()

    def test_unattended_start_never_opens_a_dialog_for_ranked(self):
        _app()
        from app.ui.qt.pages.run import RunPage
        controller = mock.Mock()
        controller.is_running.return_value = False
        page = RunPage(controller, lambda key: None)
        messages = []
        page.scheduleMessage.connect(messages.append)
        page._ranked.setChecked(True)
        with mock.patch.object(RunPage, '_game_window_ready', return_value = (True, '')), \
             mock.patch('app.ui.qt.pages.run.RankedAttackConfirmDialog') as dialog:
            page.start_bot(unattended = True)
        dialog.ask.assert_not_called()
        controller.start.assert_not_called()
        self.assertIn('Ranked', messages[-1])

    def test_game_window_missing_is_reported_without_a_dialog(self):
        _app()
        from app.ui.qt.pages.run import RunPage
        controller = mock.Mock()
        controller.is_running.return_value = False
        page = RunPage(controller, lambda key: None)
        messages = []
        page.scheduleMessage.connect(messages.append)
        with mock.patch.object(RunPage, '_game_window_ready', return_value = (False, 'The Clash of Clans window was not found.')), \
             mock.patch('app.ui.qt.pages.run.show_error') as dialog:
            page.start_bot(unattended = True)
        dialog.assert_not_called()
        self.assertEqual(messages, ['The Clash of Clans window was not found.'])

    def test_schedule_choice_is_remembered(self):
        _app()
        (page, _c) = self.page()
        page._schedule_time.setTime(__import__('PySide6.QtCore', fromlist = ['QTime']).QTime(3, 45))
        page._schedule_on.setChecked(True)
        (again, _c2) = self.page()
        self.assertEqual(again._schedule_time.time().toString('HH:mm'), '03:45')
        self.assertTrue(again._schedule_on.isChecked())
        again._schedule_on.setChecked(False)


def _bot():
    from app.config import Config
    from app.core.bot import Bot
    bot = Bot.__new__(Bot)
    bot.config = Config()
    bot.stop_event = mock.Mock()
    bot.stop_event.is_set.return_value = False
    bot.stop_event.wait.return_value = False
    bot.window = mock.Mock()
    bot._update_config_size = mock.Mock()
    bot.input = mock.Mock()
    bot.vision = mock.Mock()
    bot._status_callback = None
    return bot


def _frame_with_bubbles(items, scale = 0.9):
    '''2560x1440 noisy frame with the collect-bubble templates pasted at ``scale``.'''
    from app.utils.common import get_resource_path
    frame = np.full((1440, 2560, 3), (50, 70, 40), np.uint8)
    frame = cv2.add(frame, np.random.default_rng(3).integers(0, 22, frame.shape, dtype = np.uint8))
    for (name, (cx, cy)) in items:
        tpl = cv2.imread(str(get_resource_path(f'templates/16_9/{name}')))
        tpl = cv2.resize(tpl, None, fx = scale, fy = scale, interpolation = cv2.INTER_AREA)
        (th, tw) = tpl.shape[:2]
        frame[cy - th // 2:cy - th // 2 + th, cx - tw // 2:cx - tw // 2 + tw] = tpl
    return frame


class CollectResourcesTests(unittest.TestCase):

    ITEMS = [('hgold.png', (900, 700)), ('helixir.png', (1400, 500)), ('hdelixir.png', (1700, 900)), ('hgold.png', (1000, 1100))]

    def setUp(self):
        from app.config import Config
        Config().set_target_size(2560, 1440)

    def test_bubbles_are_found_and_the_hud_is_ignored(self):
        bot = _bot()
        frame = _frame_with_bubbles(self.ITEMS + [('hgold.png', (2300, 120))])  # a coin on the resource bar
        found = bot._collect_bubbles(frame)
        self.assertEqual(len(found), 4)
        for (_n, (cx, cy)) in self.ITEMS:
            self.assertTrue(any(abs(x - cx) <= 6 and abs(y - cy) <= 6 for (x, y) in found), (cx, cy))
        self.assertFalse(any(x > 2000 and y < 400 for (x, y) in found))

    def test_taps_every_bubble_then_rebases_the_loot_tracker(self):
        bot = _bot()
        bot.window.screenshot.return_value = _frame_with_bubbles(self.ITEMS)
        bot.vision.find_template.return_value = (141, 1384)  # Attack button: home screen
        bot._read_hud_triplet_stable = mock.Mock(return_value = (9_000_000, 8_000_000, 150_000))
        bot._loot_prev_resources = (1, 1, 1)
        bot._check_stop = mock.Mock()
        self.assertEqual(bot._collect_resources_now(), 4)
        self.assertEqual(bot.input.click.call_count, 4)
        self.assertEqual(bot._loot_prev_resources, (9_000_000, 8_000_000, 150_000))  # collected ≠ battle loot

    def test_not_on_home_screen_taps_nothing(self):
        bot = _bot()
        bot.window.screenshot.return_value = _frame_with_bubbles(self.ITEMS)
        bot.vision.find_template.return_value = (None, None)
        self.assertEqual(bot._collect_resources_now(), 0)
        bot.input.click.assert_not_called()

    def test_off_builder_base_and_interval_are_respected(self):
        bot = _bot()
        bot._collect_resources_now = mock.Mock(return_value = 0)
        bot._collect_resources = False
        bot._maybe_collect_resources(force = True)
        bot._collect_resources_now.assert_not_called()
        bot._collect_resources = True
        bot._builder_base = True
        bot._maybe_collect_resources(force = True)
        bot._collect_resources_now.assert_not_called()
        bot._builder_base = False
        bot._collect_last = 0.0
        bot._maybe_collect_resources()
        bot._maybe_collect_resources()  # inside the interval
        self.assertEqual(bot._collect_resources_now.call_count, 1)
        bot._maybe_collect_resources(force = True)
        self.assertEqual(bot._collect_resources_now.call_count, 2)


class SingleWallTests(unittest.TestCase):

    def setUp(self):
        from app.config import Config
        Config().set_target_size(2560, 1440)

    def test_wall_titles_are_told_from_other_buildings(self):
        from app.core.build_panel import title_names_a_wall
        for text in ('wall (level13)', 'wall(evel 13)', 'wa1l (level 13)', 'Wall (Level 7)'):
            self.assertTrue(title_names_a_wall(text), text)
        for text in ('giant bomb', 'giant bomb (level 7)', 'spring trap (level 9)', 'cannon', ''):
            self.assertFalse(title_names_a_wall(text), text)

    def test_pay_buttons_are_found_at_the_open_panel_scale(self):
        from app.core.build_panel import find_single_pay_buttons
        tpl = cv2.imread(str(Path(__file__).resolve().parent.parent / 'templates' / '16_9' / 'singleupgrade.png'))
        frame = np.full((1440, 2560, 3), (60, 80, 50), np.uint8)
        frame = cv2.add(frame, np.random.default_rng(5).integers(0, 20, frame.shape, dtype = np.uint8))
        small = cv2.resize(tpl, None, fx = 0.9, fy = 0.9, interpolation = cv2.INTER_AREA)
        (th, tw) = small.shape[:2]
        for cx in (1138, 1345):
            frame[1193 - th // 2:1193 - th // 2 + th, cx - tw // 2:cx - tw // 2 + tw] = small
        buttons = find_single_pay_buttons(frame)
        self.assertEqual(len(buttons), 2)
        self.assertLess(abs(buttons[0].center[0] - 1138), 5)
        self.assertLess(abs(buttons[1].center[0] - 1345), 5)
        self.assertEqual(find_single_pay_buttons(np.zeros((1440, 2560, 3), np.uint8)), [])

    def wall_bot(self, title = 'wall (level13)', hud = (10_000_000, 9_000_000, 300_000), cost = 1_000_000):
        from app.core.build_panel import SinglePayButton
        bot = _bot()
        bot._wall_pick_cost = cost
        bot._builder_base = False
        bot._read_hud_triplet_stable = mock.Mock(return_value = hud)
        bot._confirm_wall_dialog = mock.Mock()
        self.buttons = [SinglePayButton((1138, 1193), cost, False, 'gold', 0.93), SinglePayButton((1345, 1193), cost, False, 'elixir', 0.93)]
        patches = [mock.patch('app.core.bot.read_bar_title_text', return_value = title),
                   mock.patch('app.core.bot.find_single_pay_buttons', return_value = self.buttons),
                   mock.patch('app.core.bot.read_wall_bar_title', return_value = (13, None))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return bot

    def test_last_wall_is_paid_with_elixir_first(self):
        bot = self.wall_bot()
        self.assertTrue(bot._pay_single_wall(mock.Mock()))
        bot.input.click.assert_called_once_with(pause = 0.3, *(1345, 1193))
        bot._confirm_wall_dialog.assert_called_once_with('elixir')
        self.assertEqual(bot._wall_batch_count, 1)
        self.assertIsNone(bot._single_wall_expected_price)  # cleared again

    def test_gold_pays_when_elixir_cannot(self):
        bot = self.wall_bot(hud = (10_000_000, 400_000, 0))
        self.assertTrue(bot._pay_single_wall(mock.Mock()))
        bot.input.click.assert_called_once_with(pause = 0.3, *(1138, 1193))

    def test_a_building_bar_is_never_paid(self):
        bot = self.wall_bot(title = 'giant bomb (level 7)')
        self.assertFalse(bot._pay_single_wall(mock.Mock()))
        bot.input.click.assert_not_called()

    def test_nothing_is_paid_when_the_loot_cannot_cover_it(self):
        bot = self.wall_bot(hud = (1_000_000, 900_000, 0))  # gold keeps the 50k attack buffer
        self.assertFalse(bot._pay_single_wall(mock.Mock()))
        bot.input.click.assert_not_called()

    def test_confirm_price_must_equal_the_wall_row_price(self):
        from app.core.bot import Bot
        bot = _bot()
        bot._single_wall_expected_price = 4_000_000
        panel = mock.Mock()
        panel.frame.return_value = object()
        button = mock.Mock(price = 2_000_000, red = False, resource = 'gold', layout = 'x')
        with mock.patch('app.core.bot.BuildPanel', return_value = panel), \
             mock.patch('app.core.bot.read_confirm_button', return_value = button):
            with self.assertLogs('BotCore', level = 'WARNING'):
                Bot._confirm_wall_dialog(bot, 'gold')
        panel.click_confirm_and_check.assert_not_called()
        panel.close_all.assert_called_once()

    def test_matching_confirm_price_goes_ahead(self):
        from app.core.bot import Bot
        bot = _bot()
        bot._single_wall_expected_price = 1_000_000
        bot._record_wall_upgrade = mock.Mock()
        panel = mock.Mock()
        panel.frame.return_value = object()
        panel.click_confirm_and_check.return_value = 'ok'
        button = mock.Mock(price = 1_000_000, red = False, resource = 'gold', layout = 'x')
        with mock.patch('app.core.bot.BuildPanel', return_value = panel), \
             mock.patch('app.core.bot.read_confirm_button', return_value = button):
            Bot._confirm_wall_dialog(bot, 'gold')
        panel.click_confirm_and_check.assert_called_once()
        self.assertTrue(bot._wall_upgrade_confirmed)

    def test_the_row_click_falls_back_to_a_single_wall_payment(self):
        # No "Upgrade More" (greyed out) → the single-wall path runs before giving up.
        bot = _bot()
        bot.window.screenshot.return_value = np.zeros((1440, 2560, 3), np.uint8)
        bot._find_upgrade_more = mock.Mock(return_value = (None, None, 1.0))
        bot._pay_single_wall = mock.Mock(return_value = True)
        bot._upgrade_walls_batch = mock.Mock()
        with mock.patch('app.core.bot.BuildPanel'):
            bot._upgrade_walls_from_row((100, 100))
        bot._pay_single_wall.assert_called_once()
        bot._upgrade_walls_batch.assert_not_called()

    def test_wall_order_picks_the_cheapest_row_by_default(self):
        from app.core.bot import Bot
        for (order, expect_cheapest) in (('lowest', True), ('highest', False)):
            bot = _bot()
            bot._wall_order = order
            bot._upgrade_order = 'priciest'  # the building order must not matter
            bot._read_hud_triplet_stable = mock.Mock(return_value = (9_000_000, 9_000_000, 0))
            bot._find_cheapest_wall_row = mock.Mock(return_value = (1, 2))
            panel = mock.Mock()
            panel.open.return_value = True
            panel.frame.return_value = None  # the "highest" walk ends at once
            with mock.patch('app.core.bot.BuildPanel', return_value = panel):
                Bot._find_wall_row_build_panel(bot)
            self.assertEqual(bot._find_cheapest_wall_row.called, expect_cheapest, order)


if __name__ == '__main__':
    unittest.main()
