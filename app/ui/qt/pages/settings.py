'''Settings page — profile preferences and manual game-window selection.'''
from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import Qt as _Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QDoubleSpinBox, QSpinBox, QVBoxLayout, QWidget
from app.config import resolve_aspect_key
from app.services.display import DisplayService
from app.services.window import DescendantInfo, WindowCandidate, WindowService
from app.ui.qt import help_text
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import Card, SectionTitle, Separator, SettingRow, ToggleSwitch, hint_label, neutral_button, page_header, primary_button
from app.utils.logger import setup_logger
from app.utils.profile_settings_store import EARTHQUAKE_METHOD_OPTIONS, BB_WALL_UPGRADE_THRESHOLD_M_MAX, RESERVE_BUILDERS_MAX, WALL_UPGRADE_THRESHOLD_M_MAX, ProfileSettings, load_profile_settings, save_profile_settings
from app.utils.window_settings_store import clear_window_selection, load_window_selection, save_window_selection
logger = setup_logger('SettingsPage')

class WindowInfoDialog(QDialog):
    '''Read-only view of every child window/surface under a selected top-level window.'''
    
    def __init__(self, parent, candidate, descendants):
        super().__init__(parent)
        self.setWindowTitle('Window info')
        self.setModal(True)
        self.resize(640, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        layout.setSpacing(SPACING['sm'])
        header = QLabel(f'''Top-level: {candidate.title or '(no title)'}\nClass: {candidate.top_class}    hwnd={candidate.top_hwnd}''')
        header.setWordWrap(True)
        header.setStyleSheet(f'''color: {TOKENS['text']};''')
        layout.addWidget(header)
        count = len(descendants)
        surfaces = sum([ 1 for d in descendants if d.is_surface ])
        summary = QLabel(f'''{count} child window(s), {surfaces} game surface(s). Surfaces are marked [surface].''')
        summary.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        layout.addWidget(summary)
        listing = QListWidget()
        listing.setObjectName('WindowInfoList')
        mono = QFont('Consolas')
        mono.setStyleHint(QFont.StyleHint.Monospace)
        listing.setFont(mono)
        if descendants:
            for d in descendants:
                item = QListWidgetItem(d.display_label())
                if d.is_surface:
                    item.setForeground(QColor(TOKENS['primary']))
                listing.addItem(item)
        else:
            listing.addItem(QListWidgetItem('No child windows found under this window.'))
        layout.addWidget(listing, stretch = 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = neutral_button('Close', parent = self)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)



class SettingsPage(QWidget):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self._candidates = []
        self._display = DisplayService()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'] - 8, 0)
        outer.setSpacing(SPACING['md'])
        outer.addLayout(page_header('Settings', 'Changes are saved automatically.'))
        # The settings cards outgrew the fixed window (upgrade-order/reserve controls) —
        # scroll like the Run page instead of compressing cards into overlap.
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 2, 8, SPACING['lg'])
        layout.setSpacing(SPACING['md'])
        (attack_card, upgrades_card) = self._build_earthquake_card()
        layout.addWidget(attack_card)
        layout.addWidget(upgrades_card)
        layout.addWidget(self._build_app_card())
        (window_card, display_card) = self._build_window_card()
        layout.addWidget(window_card)
        layout.addWidget(display_card)
        layout.addWidget(self._build_about_card())
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    
    _CONTROL_WIDTH = 190

    def _build_about_card(self):
        from app import __version__
        from app.utils.common import get_user_app_data_dir
        card = Card()
        card.card_layout.addWidget(SectionTitle('About'))
        card.card_layout.addWidget(hint_label(f'EmaahhhPilot {__version__} — a personal educational project, not affiliated with Supercell. '
                                              'Based on BasePilot by Efe Bolukbasi and AresPilot (MIT licence).'))
        row = QHBoxLayout()
        btn = neutral_button('Open data folder', parent = card)
        btn.setToolTip('Open the folder with your settings, history and log file.')
        btn.clicked.connect(lambda: self._open_data_folder(get_user_app_data_dir()))
        row.addWidget(btn)
        row.addStretch()
        card.card_layout.addLayout(row)
        return card

    @staticmethod
    def _open_data_folder(path):
        import os
        try:
            os.makedirs(path, exist_ok = True)
            os.startfile(str(path))
        except OSError as exc:
            logger.warning('Cannot open %s: %s', path, exc)

    def _spin(self, spin):
        spin.setFixedWidth(110)
        spin.setAlignment(_Qt.AlignmentFlag.AlignCenter)
        return spin

    def _build_earthquake_card(self):
        '''Returns (attack card, upgrades & walls card). Every control saves on change.'''
        attack = Card()
        attack.card_layout.addWidget(SectionTitle('Attack'))
        self._earthquake = QComboBox()
        self._earthquake.addItems(list(EARTHQUAKE_METHOD_OPTIONS))
        self._earthquake.setFixedWidth(self._CONTROL_WIDTH)
        attack.card_layout.addWidget(SettingRow('Earthquake placement', 'How the 11 earthquake drops are spread over the village.', self._earthquake))

        card = Card()
        card.card_layout.addWidget(SectionTitle('Upgrades & walls'))
        self._wall_threshold = self._spin(QSpinBox())
        self._wall_threshold.setRange(0, WALL_UPGRADE_THRESHOLD_M_MAX)
        self._wall_threshold.setSuffix('M')
        card.card_layout.addWidget(SettingRow('Wall threshold — Home Village', 'With "Upgrade walls" on, upgrade as soon as gold or elixir reaches this amount, before storages fill up. 0 = only when storages are full.', self._wall_threshold))
        card.card_layout.addWidget(Separator())
        self._bb_wall_threshold = self._spin(QDoubleSpinBox())
        self._bb_wall_threshold.setDecimals(1)
        self._bb_wall_threshold.setRange(0.0, BB_WALL_UPGRADE_THRESHOLD_M_MAX)
        self._bb_wall_threshold.setSingleStep(0.1)
        self._bb_wall_threshold.setSuffix('M')
        card.card_layout.addWidget(SettingRow('Wall threshold — Builder Base', 'Builder Base gold or elixir that triggers its wall upgrades. 0 = as soon as the loot pays two walls of the cheapest level.', self._bb_wall_threshold))
        card.card_layout.addWidget(Separator())
        self._upgrade_order = QComboBox()
        self._upgrade_order.addItems(['Priciest first', 'Cheapest first'])
        self._upgrade_order.setFixedWidth(self._CONTROL_WIDTH)
        card.card_layout.addWidget(SettingRow('Upgrade order', 'Priciest first puts full storages into the biggest jobs; dark elixir upgrades always go first. Walls have their own order below.', self._upgrade_order))
        card.card_layout.addWidget(Separator())
        self._wall_order = QComboBox()
        self._wall_order.addItems(['Lowest level first', 'Highest level first'])
        self._wall_order.setFixedWidth(self._CONTROL_WIDTH)
        card.card_layout.addWidget(SettingRow('Wall order', 'Which wall level is upgraded first. Lowest first finishes the weakest walls before the expensive ones (it scans the whole Build list, a few seconds slower). The very last wall of a level is upgraded too.', self._wall_order))
        card.card_layout.addWidget(Separator())
        self._reserve_builders = self._spin(QSpinBox())
        self._reserve_builders.setRange(0, RESERVE_BUILDERS_MAX)
        self._reserve_builders.setSuffix('  builders')
        card.card_layout.addWidget(SettingRow('Reserve builders', 'With Auto upgrade on, keep this many builders free for walls. Set 0 when your walls are maxed.', self._reserve_builders))
        # Save on every change: the bot reads settings.json when a run starts, and an
        # edit left unsaved was silently dropped (showEvent reloads the file) — live
        # repro: "Random Placement" picked, runs kept using Curve Placement.
        self._earthquake.currentIndexChanged.connect(self._auto_save)
        self._wall_threshold.valueChanged.connect(self._auto_save)
        self._bb_wall_threshold.valueChanged.connect(self._auto_save)
        self._upgrade_order.currentIndexChanged.connect(self._auto_save)
        self._wall_order.currentIndexChanged.connect(self._auto_save)
        self._reserve_builders.valueChanged.connect(self._auto_save)
        return (attack, card)

    def _build_app_card(self):
        '''Notifications, notification-area icon and the stop key (all saved on change).'''
        card = Card()
        card.card_layout.addWidget(SectionTitle('App'))
        self._notifications = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Notifications', 'A Windows notification when a run ends by itself, the bot gets stuck or stops with an error.', self._notifications))
        card.card_layout.addWidget(Separator())
        self._tray_on_close = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Keep running in the notification area', 'The close button hides the window near the clock instead of quitting; the bot keeps running. Use the icon\'s menu → Quit to really close.', self._tray_on_close))
        card.card_layout.addWidget(Separator())
        self._stop_hotkey = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('F12 stops the bot', 'Press F12 anywhere, even with the game in front, to stop a run. The key is only taken while a run is active.', self._stop_hotkey))
        for toggle in (self._notifications, self._tray_on_close, self._stop_hotkey):
            toggle.toggled.connect(self._auto_save)
        return card

    def _auto_save(self, *_args):
        if getattr(self, '_loading_settings', False):
            return
        self._on_save()


    def _build_window_card(self):
        '''Returns (game window card, display card).'''
        card = Card()
        card.card_layout.addWidget(SectionTitle('Game window'))
        card.card_layout.addWidget(hint_label("If the bot can't find Clash of Clans, pick the Google Play Games window below and press Test. Windows with a game surface are listed first."))
        self._window_list = QListWidget()
        self._window_list.setObjectName('WindowList')
        self._window_list.setMinimumHeight(140)
        self._window_list.currentRowChanged.connect((lambda _: self._update_window_buttons()))
        card.card_layout.addWidget(self._window_list)
        self._window_status = QLabel('')
        self._window_status.setWordWrap(True)
        self._window_status.setObjectName('Hint')
        card.card_layout.addWidget(self._window_status)
        row = QHBoxLayout()
        self._btn_refresh = neutral_button('Refresh', parent = card)
        self._btn_refresh.clicked.connect(self._refresh_windows)
        row.addWidget(self._btn_refresh)
        self._btn_test = neutral_button('Test', parent = card)
        self._btn_test.clicked.connect(self._on_test_window)
        row.addWidget(self._btn_test)
        self._btn_info = neutral_button('Info', parent = card)
        self._btn_info.clicked.connect(self._on_window_info)
        row.addWidget(self._btn_info)
        self._btn_use = primary_button('Use this window', parent = card)
        self._btn_use.clicked.connect(self._on_use_window)
        row.addWidget(self._btn_use)
        row.addStretch()
        self._btn_auto = neutral_button('Auto-detect', parent = card)
        self._btn_auto.clicked.connect(self._on_auto_detect)
        row.addWidget(self._btn_auto)
        card.card_layout.addLayout(row)
        for (btn, key) in ((self._btn_refresh, 'refresh'), (self._btn_test, 'test'), (self._btn_info, 'info'), (self._btn_use, 'use'), (self._btn_auto, 'auto')):
            btn.setToolTip(help_text.SETTINGS_BUTTONS[key])
        display = Card()
        display.card_layout.addWidget(SectionTitle('Display'))
        display.card_layout.addWidget(hint_label("Ultrawide / 21:9 monitor? Google Play Games locks the game to your display's aspect at launch, so it renders 21:9 (unsupported). Fix: switch to 16:9, FULLY close and reopen Clash, then restore your display — the running game stays 16:9."))
        disp_row = QHBoxLayout()
        self._btn_disp_169 = neutral_button('Switch display to 16:9', parent = display)
        self._btn_disp_169.clicked.connect(self._on_switch_display_169)
        disp_row.addWidget(self._btn_disp_169)
        self._btn_disp_restore = neutral_button('Restore my display', parent = display)
        self._btn_disp_restore.clicked.connect(self._on_restore_display)
        disp_row.addWidget(self._btn_disp_restore)
        disp_row.addStretch()
        self._btn_disp_169.setToolTip(help_text.SETTINGS_BUTTONS['switch169'])
        self._btn_disp_restore.setToolTip(help_text.SETTINGS_BUTTONS['restore'])
        display.card_layout.addLayout(disp_row)
        return (card, display)

    
    def showEvent(self, event):
        super().showEvent(event)
        self._reload_earthquake()
        self._refresh_windows()

    
    def _reload_earthquake(self):
        settings = load_profile_settings()
        self._loading_settings = True  # filling the widgets must not trigger auto-save
        try:
            idx = self._earthquake.findText(settings.earthquake_method)
            if idx >= 0:
                self._earthquake.setCurrentIndex(idx)
            self._wall_threshold.setValue(settings.wall_upgrade_threshold_m)
            self._bb_wall_threshold.setValue(settings.bb_wall_upgrade_threshold_m)
            self._reserve_builders.setValue(settings.reserve_builders)
            self._upgrade_order.setCurrentIndex(1 if settings.upgrade_order == 'cheapest' else 0)
            self._wall_order.setCurrentIndex(1 if settings.wall_order == 'highest' else 0)
            self._notifications.setChecked(settings.notifications)
            self._tray_on_close.setChecked(settings.tray_on_close)
            self._stop_hotkey.setChecked(settings.stop_hotkey)
        finally:
            self._loading_settings = False


    def current_profile(self):
        '''Every field of the page as a ProfileSettings (all of them: a field left out here
        would be reset to its default by the next auto-save).'''
        return ProfileSettings(
            earthquake_method = self._earthquake.currentText(),
            wall_upgrade_threshold_m = self._wall_threshold.value(),
            bb_wall_upgrade_threshold_m = self._bb_wall_threshold.value(),
            reserve_builders = self._reserve_builders.value(),
            upgrade_order = 'cheapest' if self._upgrade_order.currentIndex() == 1 else 'priciest',
            wall_order = 'highest' if self._wall_order.currentIndex() == 1 else 'lowest',
            notifications = self._notifications.isChecked(),
            tray_on_close = self._tray_on_close.isChecked(),
            stop_hotkey = self._stop_hotkey.isChecked())

    def _on_save(self):
        save_profile_settings(self.current_profile())
        self._flash_status_bar('Saved')

    
    def _selected_candidate(self):
        row = self._window_list.currentRow()
        if 0 <= row and row < len(self._candidates):
            pass
        else:
            return None
        return self._candidates[row]

    
    def _update_window_buttons(self):
        cand = self._selected_candidate()
        has_sel = cand is not None
        self._btn_test.setEnabled(has_sel)
        self._btn_use.setEnabled(has_sel)
        self._btn_info.setEnabled(has_sel)

    
    def _refresh_windows(self):
        
        try:
            self._candidates = WindowService().enumerate_windows()
            saved = load_window_selection()
            self._window_list.clear()
            selected_row = -1
            for i, cand in enumerate(self._candidates):
                item = QListWidgetItem(cand.display_label())
                if not cand.is_game:
                    item.setForeground(self._muted_brush())
                self._window_list.addItem(item)
                if not saved.is_set():
                    continue
                if cand.title.strip().lower() != saved.title.strip().lower():
                    continue
                # [fix: decompiler mangled this test — the pinned window was never highlighted]
                if saved.top_class and cand.top_class != saved.top_class:
                    continue
                selected_row = i
            if selected_row >= 0:
                self._window_list.setCurrentRow(selected_row)
            if not self._candidates:
                self._window_status.setText('No visible windows found. Open the game, then Refresh.')
            elif saved.is_set():
                self._window_status.setText(f'''Pinned window: {saved.title or '(saved)'}''')
            else:
                self._window_status.setText('Using auto-detect.')
            self._update_window_buttons()
            return None
        except Exception as exc:
            logger.warning(f'''Could not enumerate windows: {exc}''')
            self._candidates = []


    
    def _muted_brush(self):
        return QColor(TOKENS['text_muted'])

    
    @staticmethod
    def _aspect_label(w, h):
        if not w or not h:
            return 'size unavailable'
        aspect = resolve_aspect_key(w, h)
        if aspect is None:
            return f'''{w}x{h} (not ~16:9/16:10)'''
        pretty = '16:9' if aspect == '16_9' else '16:10'
        return f'''{w}x{h} ({pretty})'''

    
    def _on_test_window(self):
        cand = self._selected_candidate()
        if cand is None:
            return None
        if not cand.is_game:
            self._window_status.setText('No Google Play Games surface (CROSVM) under this window — pick the game window.')
            return None
        ws = WindowService()
        surface_size = ws.window_pixel_size(cand.child_hwnd)
        if surface_size is None:
            self._window_status.setText('Could not read the window size. Is the game minimized?')
            return None
        sub_size = None
        
        try:
            for d in ws.enumerate_descendants(cand.top_hwnd):
                if d.cls.lower() != 'subwin':
                    continue
                sub_size = (d.width, d.height)
                break
            (sw, sh) = surface_size
            lines = [
                f'''Capture target {cand.child_class}: {self._aspect_label(sw, sh)}''']
            if not sub_size is None:
                lines.append(f'''Inner subWin: {self._aspect_label(*sub_size)}''')
            if resolve_aspect_key(sw, sh) is None:
                lines.append('Surface aspect unsupported — try resizing the game window.')
            else:
                lines.append('Surface OK to use.')
            self._window_status.setText('\n'.join(lines))
            return None
        except Exception as exc:
            logger.warning(f'''Could not inspect subWin: {exc}''')


    
    def _on_switch_display_169(self):
        (ok, size, reason) = self._display.switch_to_16_9()
        if ok and reason == 'already_16_9':
            self._window_status.setText('Your display is already 16:9 — just (re)launch Clash in Google Play Games and it will render 16:9.')
        elif ok:
            self._window_status.setText(f'''Display set to {size[0]}x{size[1]} (16:9). Now FULLY close and reopen Clash in Google Play Games, then click "Restore my display".''')
        elif reason == 'no_16_9_mode':
            self._window_status.setText('Your display driver offers no 16:9 mode — use a 16:9 monitor for the game instead.')
        else:
            self._window_status.setText('Could not switch the display resolution.')
        self._flash_status_bar('Display set to 16:9' if ok else 'Display switch failed')


    def _on_restore_display(self):
        (ok, size, reason) = self._display.restore()
        if ok:
            self._window_status.setText(f'''Display restored to {size[0]}x{size[1]}. If you relaunched Clash while in 16:9 it stays 16:9 — press Test to confirm, then Start.''')
        elif reason == 'nothing_to_restore':
            self._window_status.setText('Nothing to restore — you have not switched your display (or it was already restored).')
        else:
            self._window_status.setText('Could not restore the display. Use Windows Settings → Display to set it back.')
        self._flash_status_bar('Display restored' if ok else 'Restore failed')


    def _on_window_info(self):
        cand = self._selected_candidate()
        if cand is None:
            return None

        try:
            descendants = WindowService().enumerate_descendants(cand.top_hwnd)
            WindowInfoDialog(self.window(), cand, descendants).exec()
            return None
        except Exception as exc:
            logger.warning(f'''Could not enumerate descendants: {exc}''')


    
    def _on_use_window(self):
        cand = self._selected_candidate()
        if cand is None:
            return None
        save_window_selection(cand.to_selection())
        self._window_status.setText(f'''Pinned: {cand.title or '(no title)'}. Press Test to verify.''')
        self._flash_status_bar('Window saved')

    
    def _on_auto_detect(self):
        clear_window_selection()
        self._window_status.setText('Cleared — using auto-detect.')
        self._flash_status_bar('Auto-detect')
        self._refresh_windows()

    
    def _flash_status_bar(self, msg):
        win = self.window()
        if isinstance(win, QMainWindow):
            if not win.statusBar() is None:
                win.statusBar().showMessage(msg, 1500)
                return None
            return None


