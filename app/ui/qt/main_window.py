'''Main application window — sidebar shell.'''
from __future__ import annotations
import platform
import sys
from app.utils.common import APP_NAME
from PySide6.QtCore import QSettings, QSize, QTimer, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget
from app import __version__
from app.ui.qt.branding import apply_app_icon, logo_pixmap
from app.ui.qt.bot_controller import BotController
from app.ui.qt.dialogs import show_error
from app.ui.qt.pages.history import HistoryPage
from app.ui.qt.pages.logs import LogsPage
from app.ui.qt.pages.players import PlayersWipPage
from app.ui.qt.pages.run import RunPage
from app.ui.qt.pages.settings import SettingsPage
from app.ui.qt.taskbar_thumb_qt import QtTaskbarThumb
from app.ui.qt.tray import TrayController
from app.ui.qt.theme import SIDEBAR_WIDTH, TOKENS, WINDOW_DEFAULT, WINDOW_MIN
from app.ui.qt.widgets import Backdrop, PageTransition, Pulse, sidebar_icon
from app.ui.qt import help_text
PAGE_KEYS = [
    'run',
    'history',
    'settings',
    'players',
    'logs']
PAGE_LABELS = [
    'Run',
    'History',
    'Settings',
    'Players',
    'Logs']

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(*WINDOW_DEFAULT)
        self.setMinimumSize(*WINDOW_MIN)
        self._settings = QSettings(APP_NAME, 'UI')
        self._migrate_legacy_ui_settings()
        self._controller = BotController(bot_version = __version__)
        self._taskbar = None
        self._taskbar_setup_attempts = 0
        self._taskbar_setup_done = False
        central = Backdrop()  # soft colour glows behind the glass panels
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar_panel = QWidget()
        sidebar_panel.setObjectName('SidebarPanel')
        sidebar_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar_panel.setFixedWidth(SIDEBAR_WIDTH)
        sidebar_col = QVBoxLayout(sidebar_panel)
        sidebar_col.setContentsMargins(14, 22, 14, 14)
        sidebar_col.setSpacing(22)
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(4, 0, 0, 0)
        brand_row.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(40))
        brand_row.addWidget(logo)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        brand = QLabel(APP_NAME)
        brand.setObjectName('Brand')
        brand_col.addWidget(brand)
        brand_sub = QLabel('Clash of Clans autopilot')
        brand_sub.setObjectName('BrandSub')
        brand_col.addWidget(brand_sub)
        brand_row.addLayout(brand_col)
        brand_row.addStretch()
        sidebar_col.addLayout(brand_row)
        nav_col = QVBoxLayout()
        nav_col.setSpacing(6)
        menu_title = QLabel('MENU')
        menu_title.setObjectName('SectionTitle')
        menu_title.setContentsMargins(10, 0, 0, 0)
        nav_col.addWidget(menu_title)
        self._sidebar = QListWidget()
        self._sidebar.setObjectName('Sidebar')
        self._sidebar.setIconSize(QSize(18, 18))
        self._sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        for (key, label) in zip(PAGE_KEYS, PAGE_LABELS):
            item = QListWidgetItem(sidebar_icon(key), label, self._sidebar)
            item.setToolTip(help_text.NAV.get(key, ''))
        self._sidebar.setCurrentRow(0)
        nav_col.addWidget(self._sidebar, stretch = 1)
        sidebar_col.addLayout(nav_col, stretch = 1)
        sidebar_col.addWidget(self._build_sidebar_status())
        root.addWidget(sidebar_panel)
        self._stack = QStackedWidget()
        self._run_page = RunPage(self._controller, self.navigate_to)
        self._history_page = HistoryPage(self._controller)
        self._settings_page = SettingsPage()
        self._players_page = PlayersWipPage()  # multi-run is being reworked
        self._logs_page = LogsPage()
        # Same order as PAGE_KEYS: the sidebar row index is the stack index.
        for page in (self._run_page, self._history_page, self._settings_page, self._players_page, self._logs_page):
            self._stack.addWidget(page)
        root.addWidget(self._stack, stretch = 1)
        self._build_status_bar()
        self._wire_signals()
        self._fade_overlay = None
        self._sidebar.currentRowChanged.connect(self._switch_page)
        self._tray = TrayController(self, self._controller, self._run_page)
        self._restore_geometry()

    def _switch_page(self, index):
        '''Show page ``index`` with a short cross-fade: a snapshot of the old page fades
        out on top while the new page slides up a few pixels into place.'''
        if index == self._stack.currentIndex():
            return
        old = self._stack.currentWidget()
        if self._fade_overlay is not None:
            # A click during a transition: end the running one at once.
            self._fade_overlay.finish()
            self._fade_overlay = None
        if old is None or not self.isVisible():
            self._stack.setCurrentIndex(index)
            return
        # Pages are see-through glass: snapshot them together with the backdrop behind.
        central = self.centralWidget()
        rect = self._stack.geometry()
        old_shot = central.grab(rect)
        self._stack.setCurrentIndex(index)
        new_shot = central.grab(rect)
        overlay = PageTransition(central, old_shot, new_shot, rect)

        def done():
            if self._fade_overlay is overlay:
                self._fade_overlay = None

        overlay._on_done = done
        self._fade_overlay = overlay
        overlay.start()


    def _migrate_legacy_ui_settings(self):
        '''One-time QSettings migration from the previous names (BasePilot, then the
        pre-rebrand ClashAutoLoot): window geometry and the Run page choices.'''
        if self._settings.allKeys():
            return None
        for org in ('AresPilot', 'BasePilot', 'ClashAutoLoot'):
            legacy = QSettings(org, 'UI')
            if legacy.allKeys():
                for key in legacy.allKeys():
                    self._settings.setValue(key, legacy.value(key))
                return None

    def _build_sidebar_status(self):
        '''Bottom-of-sidebar badge: bot state with a coloured dot, and the version.'''
        box = QFrame()
        box.setObjectName('SidebarStatus')
        col = QVBoxLayout(box)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(2)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._side_dot = QLabel()
        self._side_dot.setFixedSize(8, 8)
        self._side_pulse = Pulse(self._side_dot, low = 0.25, period = 2000)
        row.addWidget(self._side_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self._side_state = QLabel()
        self._side_state.setStyleSheet('font-weight: 600;')
        row.addWidget(self._side_state)
        row.addStretch()
        col.addLayout(row)
        version_lbl = QLabel(f'''Version {__version__}''')
        version_lbl.setObjectName('BrandSub')
        col.addWidget(version_lbl)
        self._set_sidebar_running(False)
        return box

    def _set_sidebar_running(self, running):
        color = TOKENS['success'] if running else TOKENS['text_faint']
        self._side_dot.setStyleSheet(f'background-color: {color}; border-radius: 4px;')
        self._side_state.setText('Running' if running else 'Idle')
        if running:
            self._side_pulse.start()
        else:
            self._side_pulse.stop()

    def _build_status_bar(self):
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)
        self._status_label = QLabel('Ready')
        self._status_label.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        self._status_label.setContentsMargins(12, 3, 0, 3)
        bar.addWidget(self._status_label, stretch = 1)


    def _wire_signals(self):
        self._controller.statusChanged.connect(self._on_status)
        self._controller.botStarted.connect(self._on_bot_started_status)
        self._controller.botFinished.connect(self._on_bot_finished)
        self._controller.runningChanged.connect(self._on_running_changed)
        # The end-of-run numbers go to the Run page's "Last session" card (no popup);
        # the full text report stays in the log.


    def navigate_to(self, page_key):
        if page_key in PAGE_KEYS:
            self._sidebar.setCurrentRow(PAGE_KEYS.index(page_key))
            return None


    def autostart_run(self, minutes, upgrade_walls, auto_upgrade = 'off', builder_base = False):
        '''CLI ``--autostart``: configure the Run page and press Start.'''
        self._run_page.apply_autostart(minutes, upgrade_walls, auto_upgrade, builder_base)


    def _restore_geometry(self):
        geo = self._settings.value('geometry')
        if not geo is None:
            self.restoreGeometry(geo)
        state = self._settings.value('windowState')
        if not state is None:
            self.restoreState(state)
            return None


    def showEvent(self, event):
        super().showEvent(event)
        if not self._taskbar_setup_done:
            QTimer.singleShot(500, self._setup_taskbar_thumb)
            return None


    def closeEvent(self, event):
        if self._tray.hide_on_close():
            # Close button = "keep running in the notification area": the bot keeps going.
            self._settings.setValue('geometry', self.saveGeometry())
            event.ignore()
            self.hide()
            self._tray.window_hidden()
            return
        if self._controller.is_running():
            self._controller.stop()
            self._controller.wait_stopped(3.0)
        self._tray.shutdown()
        if not self._taskbar is None:
            self._taskbar.teardown()
        self._settings.setValue('geometry', self.saveGeometry())
        self._settings.setValue('windowState', self.saveState())
        event.accept()


    def _setup_taskbar_thumb(self):
        if self._taskbar_setup_done or platform.system() != 'Windows':
            return None

        try:
            self._taskbar = QtTaskbarThumb(self._controller, self._run_page, parent = self)
            if self._taskbar.setup(self):
                self._taskbar.set_running(self._controller.is_running())
                self._taskbar_setup_done = True
                return None
            self._taskbar = None
            return None
        except Exception:
            self._taskbar = None
            return None


    def _on_status(self, msg, warning):
        color = TOKENS['danger'] if warning else TOKENS['text_muted']
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f'''color: {color};''')


    def _on_bot_started_status(self):
        if self._run_page.is_star_bonus_enabled():
            self._status_label.setText('Star Bonus...')
        else:
            self._status_label.setText('Running...')
        self._status_label.setStyleSheet(f'''color: {TOKENS['text_muted']};''')


    def _on_bot_finished(self, error_msg):
        self._controller.on_bot_finished()
        if not self._taskbar is None:
            self._taskbar.set_running(False)
        if error_msg:
            preview = error_msg[:50] + '...' if len(error_msg) > 50 else error_msg
            self._status_label.setText(f'''Error: {preview}''')
            self._status_label.setStyleSheet(f'''color: {TOKENS['danger']};''')
            show_error(self, 'Error', str(error_msg))
            return None
        self._status_label.setText('Stopped')
        self._status_label.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        if sys.platform == 'win32':

            try:
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass


    def _on_running_changed(self, running):
        self._set_sidebar_running(running)
        if not self._taskbar is None:
            self._taskbar.set_running(running)
            return None
