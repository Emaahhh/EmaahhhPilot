'''Notification-area icon, Windows notifications and the F12 stop key.

- The icon lives in the notification area (near the clock): double-click shows the window;
  its menu starts / stops the bot and quits the app.
- Notifications (Settings → App): a run that ends by itself, an error, a stuck bot.
- F12 stops the bot. The key is registered only while a run is active.
- "Keep running in the notification area" (Settings → App): the window's close button hides
  the window instead of quitting; the menu's Quit really closes (stopping the bot first).
'''
from __future__ import annotations
import time
from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon
from app.services.hotkey import VK_F12, GlobalHotkey
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
from app.ui.qt.branding import app_icon
from app.utils.common import APP_NAME
from app.utils.logger import setup_logger
from app.utils.profile_settings_store import load_profile_settings
logger = setup_logger('Tray')

_REPEAT_SECONDS = 90  # the same notification text is not shown twice within this time


def needs_attention(msg):
    '''True for status lines that mean the bot gave up or is stuck (worth a notification).'''
    text = (msg or '').lower()
    return ('stopping' in text or 'backing off' in text) and any(m in text for m in ('screen stuck', 'troops not found'))


class TrayController(QObject):

    def __init__(self, window, controller, run_page, parent = None):
        super().__init__(parent or window)
        self._window = window
        self._controller = controller
        self._run_page = run_page
        self._user_stop = False
        self._last_summary = None
        self._recent = {}
        self._hidden_hint_shown = False
        self.quitting = False
        self._tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(app_icon(), window)
            self._tray.setToolTip(APP_NAME)
            self._tray.setContextMenu(self._build_menu())
            self._tray.activated.connect(self._on_activated)
            self._tray.show()
        self._hotkey = GlobalHotkey(parent = self)
        self._hotkey.pressed.connect(self._on_hotkey)
        self._hotkey.registrationFailed.connect(self._on_hotkey_failed)
        controller.runningChanged.connect(self._on_running)
        controller.botStarted.connect(self._on_started)
        controller.botFinished.connect(self._on_finished)
        controller.statusChanged.connect(self._on_status)
        controller.runSummary.connect(self._on_summary)
        if hasattr(run_page, 'scheduleMessage'):
            run_page.scheduleMessage.connect(lambda msg: self.notify('Scheduled start', msg, force = True))

    # ---- menu ----
    def _build_menu(self):
        menu = QMenu()
        show = QAction('Show EmaahhhPilot', menu)
        show.triggered.connect(self.show_window)
        start = QAction('Start', menu)
        start.triggered.connect(self._run_page.request_start_from_taskbar)
        stop = QAction('Stop', menu)
        stop.triggered.connect(self._run_page.request_stop_from_taskbar)
        quit_action = QAction('Quit', menu)
        quit_action.triggered.connect(self._quit)
        for item in (show, start, stop):
            menu.addAction(item)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._menu = menu
        self._start_action = start
        self._stop_action = stop
        stop.setEnabled(False)
        return menu

    def show_window(self):
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def _quit(self):
        self.quitting = True
        self._window.close()

    # ---- settings-driven behaviour ----
    def hide_on_close(self):
        '''True when the close button should only hide the window.'''
        if self.quitting or self._tray is None or not self._tray.isVisible():
            return False
        try:
            return bool(load_profile_settings().tray_on_close)
        except Exception:
            return False

    def window_hidden(self):
        if not self._hidden_hint_shown:
            self._hidden_hint_shown = True
            self.notify(APP_NAME, 'Still running in the notification area. Double-click the icon to open it.', force = True)

    def notify(self, title, message, *, force = False):
        '''Windows notification (respects Settings → App → Notifications unless ``force``).'''
        if self._tray is None:
            return
        try:
            if not force and not load_profile_settings().notifications:
                return
        except Exception:
            pass
        now = time.monotonic()
        key = (title, message)
        if now - self._recent.get(key, -1e9) < _REPEAT_SECONDS:
            return
        self._recent[key] = now
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 8000)

    # ---- bot events ----
    def _on_started(self):
        self._user_stop = False
        self._last_summary = None

    def _on_running(self, running):
        if hasattr(self, '_stop_action'):
            self._stop_action.setEnabled(running)
            self._start_action.setEnabled(not running)
        try:
            use_key = bool(load_profile_settings().stop_hotkey)
        except Exception:
            use_key = True
        if running and use_key:
            self._hotkey.start()
        else:
            self._hotkey.stop()

    def _on_hotkey(self):
        if self._controller.is_running():
            logger.info('%s pressed — stopping the bot', self._hotkey.label)
            self._controller.stop()
            self.notify(APP_NAME, f'Stopped with {self._hotkey.label}.', force = True)

    def _on_hotkey_failed(self, label):
        # F12 is taken (live 24/11): fall back to Ctrl+Shift+F12 once, then report.
        if label == 'F12' and not getattr(self, '_fallback_tried', False) and self._controller.is_running():
            self._fallback_tried = True
            self._hotkey.stop()
            self._hotkey = GlobalHotkey(vk = VK_F12, modifiers = MOD_CONTROL | MOD_SHIFT, label = 'Ctrl+Shift+F12', parent = self)
            self._hotkey.pressed.connect(self._on_hotkey)
            self._hotkey.registrationFailed.connect(self._on_hotkey_failed)
            self._hotkey.start()
            if self._hotkey.is_active():
                self._controller.statusChanged.emit('F12 is used by another program — the stop key is Ctrl+Shift+F12.', False)
            return
        self._controller.statusChanged.emit(f'{label} is used by another program — the stop key is unavailable.', True)

    def _on_status(self, msg, _warning):
        if msg == 'Stopping...':
            self._user_stop = True
        elif needs_attention(msg):
            self.notify('Bot needs attention', msg)

    def _on_summary(self, stats):
        self._last_summary = dict(stats)

    def _on_finished(self, error_msg):
        if error_msg:
            self.notify('Bot stopped with an error', str(error_msg)[:180])
            return
        if self._user_stop:
            return
        s = self._last_summary or {}
        if s.get('village') == 'builder':
            text = f"{s.get('attacks', 0)} attacks, {s.get('walls', 0)} walls."
        else:
            text = f"{s.get('attacks', 0)} attacks — {_amount(s.get('gold', 0))} gold, {_amount(s.get('elixir', 0))} elixir."
        self.notify('Run finished', text)

    def shutdown(self):
        self._hotkey.stop()
        if self._tray is not None:
            self._tray.hide()


def _amount(value):
    value = int(value or 0)
    return f'{value / 1_000_000:.1f}M' if value >= 1_000_000 else f'{value:,}'
