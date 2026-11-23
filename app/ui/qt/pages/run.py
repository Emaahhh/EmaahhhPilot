'''Run page — attack, schedule, modes, live status, controls.'''
from __future__ import annotations
import json
import time
from datetime import datetime
from typing import Callable, List, Optional
from app.utils.common import APP_NAME
from app.ui.qt import help_text
from PySide6.QtCore import QDateTime, QSettings, QTime, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QScrollArea, QSpinBox, QTimeEdit, QVBoxLayout, QWidget
from app.config import check_game_window_aspect_for_start
from app.ui.qt._constants import ATTACK_STRATEGIES, BUILDER_BASE_ATTACK_STRATEGIES, BUILDER_BASE_ATTACK_STRATEGIES_UNDER_DEV, BUILDER_BASE_PRIORITISE_LABELS
from app.ui.qt.bot_controller import BotController
from app.ui.qt.dialogs import RankedAttackConfirmDialog, show_bb_prioritise_help, show_error, show_under_development
from app.ui.qt.theme import SPACING, TOKENS
from PySide6.QtGui import QColor
from app.ui.qt.widgets import Card, HelpButton, HoverGlow, bind_descriptions, Pulse, SectionTitle, Separator, SettingRow, StatTile, StepperButton, ToggleSwitch, chip_button, danger_button, hint_label, link_button, page_header, primary_button, segment_button, segmented, set_state_pill, state_pill
from app.utils.player_list_store import PlayerEntry, load_players

class RunPage(QWidget):
    # A scheduled start that could not go ahead (text for a notification).
    scheduleMessage = Signal(str)
    _STRATEGY_LABELS = [
        'Valkyries',
        'Sneaky Goblins',
        'Super Minions',
        'Edrags']
    _VILLAGE_LABELS = [
        'Home Village',
        'Builder Base']
    _AUTO_UPGRADE_LABELS = [
        ('Off', 'off'),
        ('Dry run', 'dry'),
        ('Maxer', 'maxer'),
        ('Rusher', 'rusher')]

    def __init__(self, controller, navigate_to, parent = None):
        super().__init__(parent)
        self._controller = controller
        self._navigate_to = navigate_to
        self._settings = QSettings(APP_NAME, 'UI')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'] - 8, 0)
        outer.setSpacing(SPACING['md'])
        # Title row: Start / Stop stay visible at the top right, outside the scroll.
        outer.addLayout(page_header('Run', 'Pick a village and an army, then press Start.', self._build_controls()))
        outer.addWidget(self._build_village_selector(), 0, Qt.AlignmentFlag.AlignLeft)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 2, 8, SPACING['lg'])
        layout.setSpacing(SPACING['md'])
        # Live status first: while the bot runs it is what you look at.
        self._status_card = self._build_status_card()
        layout.addWidget(self._status_card)
        layout.addWidget(self._build_preview_card())
        self._attack_card = self._build_attack_card()
        layout.addWidget(self._attack_card)
        self._bb_attack_card = self._build_bb_attack_card()
        layout.addWidget(self._bb_attack_card)
        layout.addWidget(self._build_schedule_card())
        self._modes_card = self._build_modes_card()
        layout.addWidget(self._modes_card)
        self._bb_modes_card = self._build_bb_modes_card()
        layout.addWidget(self._bb_modes_card)
        self._last_session_card = self._build_last_session_card()
        self._bb_last_session_card = self._build_bb_last_session_card()
        layout.addWidget(self._last_session_card)
        layout.addWidget(self._bb_last_session_card)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self._apply_village_ui()
        self._restore_choices()
        self._controller.botStarted.connect(self._on_bot_started)
        self._controller.botFinished.connect(self._on_bot_finished_ui)
        self._controller.runningChanged.connect(self._on_running_changed)
        self._controller.stateChanged.connect(self._on_state_changed)
        self._controller.lootChanged.connect(self._on_loot_changed)
        self._controller.statusChanged.connect(self._on_status_line)
        self._controller.runSummary.connect(self._on_run_summary)
        self._load_last_session()

    
    def _build_village_selector(self):
        self._village_group = QButtonGroup(self)
        self._village_group.setExclusive(True)
        buttons = []
        for i, label in enumerate(self._VILLAGE_LABELS):
            btn = segment_button(label)
            btn.setMinimumWidth(140)
            if label == 'Home Village':
                btn.setChecked(True)
            self._village_group.addButton(btn, i)
            buttons.append(btn)
        self._village_group.idClicked.connect(self._on_village_changed)
        bind_descriptions(buttons, help_text.VILLAGES)
        return segmented(buttons)

    
    def _is_builder_base(self):
        btn = self._village_group.checkedButton()
        return btn is not None and btn.text() == 'Builder Base'

    
    def _on_village_changed(self, _button_id):
        self._apply_village_ui()

    
    def _apply_village_ui(self):
        builder_base = self._is_builder_base()
        self._attack_card.setVisible(not builder_base)
        self._modes_card.setVisible(not builder_base)
        self._bb_attack_card.setVisible(builder_base)
        self._bb_modes_card.setVisible(builder_base)
        self._last_session_card.setVisible(not builder_base)
        self._bb_last_session_card.setVisible(builder_base)
        # Loot tiles are Home Village figures; the Builder Base tracks attacks and walls.
        self._loot_tiles.setVisible(not builder_base)
        self._stat_loot_rate.setVisible(not builder_base)
        # Alone on its row (Builder Base) the run-time tile keeps a tile's width.
        self._stat_runtime.setMaximumWidth(260 if builder_base else 16777215)
        # Same "Run until maxed" switch for both villages; the hint says what it does here.
        self._until_hint.setText(self._UNTIL_HINT_BB if builder_base else self._UNTIL_HINT_HOME)


    def _build_attack_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Attack Strategy'))
        self._strategy_group = QButtonGroup(self)
        self._strategy_group.setExclusive(True)
        buttons = []
        for i, label in enumerate(self._STRATEGY_LABELS):
            btn = segment_button(label)
            if label == 'Valkyries':
                btn.setChecked(True)
            self._strategy_group.addButton(btn, i)
            buttons.append(btn)
        card.card_layout.addWidget(segmented(buttons, stretch = True))
        self._strategy_hint = hint_label('')
        bind_descriptions(buttons, help_text.STRATEGIES, self._strategy_hint)
        card.card_layout.addWidget(self._strategy_hint)
        card.card_layout.addWidget(hint_label('Bring that army in the game. Heroes, siege machines, Super Dragons and Earthquakes in the army are used too.'))
        return card


    def _build_bb_attack_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Attack Strategy'))
        self._bb_strategy_group = QButtonGroup(self)
        self._bb_strategy_group.setExclusive(True)
        buttons = []
        for i, label in enumerate(BUILDER_BASE_ATTACK_STRATEGIES):
            btn = segment_button(label)
            if label == 'Baby Dragon':
                btn.setChecked(True)
            self._bb_strategy_group.addButton(btn, i)
            buttons.append(btn)
        for label in BUILDER_BASE_ATTACK_STRATEGIES_UNDER_DEV:
            btn = segment_button(label, under_development = True)
            btn.setToolTip('Under development')
            btn.clicked.connect((lambda _checked = False: show_under_development(self.window())))
            buttons.append(btn)
        card.card_layout.addWidget(segmented(buttons, stretch = True))
        self._bb_strategy_hint = hint_label('')
        bind_descriptions(buttons, help_text.BB_STRATEGIES, self._bb_strategy_hint)
        card.card_layout.addWidget(self._bb_strategy_hint)
        return card

    
    _UNTIL_HINT_HOME = 'Farms, upgrades, and idles in a loop until you press Stop. When storages are full and nothing can be started, the bot waits and rechecks every 5 minutes instead of attacking for nothing.'
    _UNTIL_HINT_BB = 'Builder Base: attacks (and upgrades walls, if on) in a loop until you press Stop — no time limit.'

    def _build_schedule_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Schedule'))
        self._star_bonus = ToggleSwitch(parent = card)
        self._star_bonus.toggled.connect(self._on_star_bonus_toggle)
        card.card_layout.addWidget(SettingRow('Star Bonus', 'Stops once the daily Star Bonus is claimed (at most 15 minutes).', self._star_bonus))
        card.card_layout.addWidget(Separator())
        self._until_maxed = ToggleSwitch(parent = card)
        self._until_maxed.toggled.connect(self._on_until_maxed_toggle)
        until_row = SettingRow('Run until maxed', self._UNTIL_HINT_HOME, self._until_maxed)
        self._until_hint = until_row.subtitle
        card.card_layout.addWidget(until_row)
        card.card_layout.addWidget(Separator())
        self._minutes_spin = QSpinBox()
        self._minutes_spin.setObjectName('DurationSpin')
        # Built-in arrows hidden by the theme (QSpinBox#DurationSpin::up-button), NOT by
        # setButtonSymbols(NoButtons) — that collapses the text field to 1 px on Windows.
        self._minutes_spin.setRange(1, 999)
        self._minutes_spin.setValue(15)
        self._minutes_spin.setFixedSize(64, 32)
        self._minutes_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_col = QVBoxLayout()
        step_col.setSpacing(3)
        step_col.setContentsMargins(0, 0, 0, 0)
        self._btn_spin_up = StepperButton(up = True, parent = card)
        self._btn_spin_up.clicked.connect((lambda : self._step_minutes(1)))
        self._btn_spin_down = StepperButton(up = False, parent = card)
        self._btn_spin_down.clicked.connect((lambda : self._step_minutes(-1)))
        self._btn_spin_up.setToolTip(help_text.STEPPER_UP)
        self._btn_spin_down.setToolTip(help_text.STEPPER_DOWN)
        self._minutes_spin.setToolTip(help_text.MINUTES)
        step_col.addWidget(self._btn_spin_up)
        step_col.addWidget(self._btn_spin_down)
        self._minutes_unit = QLabel('min')
        self._minutes_unit.setObjectName('DurationUnit')
        self._minutes_unit.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        duration = QWidget()
        spin_group = QHBoxLayout(duration)
        spin_group.setContentsMargins(0, 0, 0, 0)
        spin_group.setSpacing(6)
        self._duration_chips = []
        for minutes in (5, 10, 20, 30, 60):
            chip = chip_button(f'{minutes}m', parent = card)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip(help_text.CHIP.format(minutes = minutes))
            chip.clicked.connect((lambda _checked = False, m = minutes: self._set_minutes(m)))
            spin_group.addWidget(chip)
            self._duration_chips.append(chip)
        (self._btn_5m, self._btn_10m, self._btn_20m) = self._duration_chips[:3]
        spin_group.addSpacing(SPACING['sm'])
        spin_group.addWidget(self._minutes_spin)
        spin_group.addLayout(step_col)
        spin_group.addWidget(self._minutes_unit)
        duration_row = SettingRow('Duration', 'How long a timed run lasts.', duration)
        self._duration_label = duration_row.title
        self._duration_hint = duration_row.subtitle
        card.card_layout.addWidget(duration_row)
        card.card_layout.addWidget(Separator())
        # Scheduled start: one-shot, at a time of day. Needs the PC awake and the game open.
        self._schedule_time = QTimeEdit(QTime(2, 0))
        self._schedule_time.setDisplayFormat('HH:mm')
        self._schedule_time.setFixedWidth(84)
        self._schedule_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._schedule_time.setToolTip(help_text.SCHEDULE_TIME)
        self._schedule_on = ToggleSwitch(parent = card)
        sched = QWidget()
        sched_row = QHBoxLayout(sched)
        sched_row.setContentsMargins(0, 0, 0, 0)
        sched_row.setSpacing(SPACING['sm'])
        sched_row.addWidget(self._schedule_time)
        sched_row.addWidget(self._schedule_on)
        self._schedule_row = SettingRow('Scheduled start', self._SCHEDULE_HINT, sched)
        card.card_layout.addWidget(self._schedule_row)
        self._schedule_target = None
        self._schedule_timer = QTimer(self)
        self._schedule_timer.setInterval(15000)
        self._schedule_timer.timeout.connect(self._tick_schedule)
        self._schedule_on.toggled.connect(self._on_schedule_toggled)
        self._schedule_time.timeChanged.connect(self._on_schedule_time_changed)
        self._on_star_bonus_toggle(self._star_bonus.isChecked())
        return card

    # ---- scheduled start ----
    _SCHEDULE_HINT = 'Starts one run at this time (today, or tomorrow if it has passed). The PC must be awake and the game open.'
    _SCHEDULE_GRACE_MINUTES = 10

    def _next_schedule_target(self):
        now = QDateTime.currentDateTime()
        target = QDateTime(now.date(), self._schedule_time.time())
        if target < now.addSecs(-self._SCHEDULE_GRACE_MINUTES * 60):
            target = target.addDays(1)
        return target

    def _on_schedule_toggled(self, on):
        self._settings.setValue('run/scheduleOn', bool(on))
        if on:
            self._schedule_target = self._next_schedule_target()
            self._schedule_timer.start()
            self._update_schedule_text()
        else:
            self._schedule_target = None
            self._schedule_timer.stop()
            self._schedule_row.set_subtitle(self._SCHEDULE_HINT)

    def _on_schedule_time_changed(self, _time):
        self._settings.setValue('run/scheduleTime', self._schedule_time.time().toString('HH:mm'))
        if self._schedule_on.isChecked():
            self._schedule_target = self._next_schedule_target()
            self._update_schedule_text()

    def _update_schedule_text(self):
        if self._schedule_target is None:
            return
        secs = max(0, QDateTime.currentDateTime().secsTo(self._schedule_target))
        when = self._schedule_target.toString('ddd HH:mm')
        self._schedule_row.set_subtitle(f'Next run: {when} — in {secs // 3600}h {secs % 3600 // 60:02d}m. The PC must stay awake and the game open.')

    def _tick_schedule(self):
        if not self._schedule_on.isChecked() or self._schedule_target is None:
            return
        now = QDateTime.currentDateTime()
        if now < self._schedule_target:
            self._update_schedule_text()
            return
        late = self._schedule_target.secsTo(now)
        self._schedule_on.setChecked(False)  # one-shot
        if late > self._SCHEDULE_GRACE_MINUTES * 60:
            self.scheduleMessage.emit('The scheduled start was missed (the PC was asleep or the app closed). Set it again.')
            return
        if self._controller.is_running():
            self.scheduleMessage.emit('Scheduled start skipped: a run is already in progress.')
            return
        self.start_bot(unattended = True)


    def _build_modes_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Modes'))
        self._auto_upgrade_group = QButtonGroup(self)
        self._auto_upgrade_group.setExclusive(True)
        buttons = []
        for i, (label, _key) in enumerate(self._AUTO_UPGRADE_LABELS):
            btn = segment_button(label)
            if label == 'Off':
                btn.setChecked(True)
            self._auto_upgrade_group.addButton(btn, i)
            buttons.append(btn)
        card.card_layout.addWidget(SettingRow('Auto upgrade', None, segmented(buttons)))
        self._auto_hint = hint_label('')
        bind_descriptions(buttons, help_text.AUTO_UPGRADE, self._auto_hint)
        card.card_layout.addWidget(self._auto_hint)
        card.card_layout.addWidget(Separator())
        self._upgrade_walls = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Upgrade walls', 'Spends gold and elixir on walls. The trigger threshold is in Settings.', self._upgrade_walls))
        card.card_layout.addWidget(Separator())
        self._collect = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Collect resources', 'Taps the gold, elixir and dark elixir bubbles of your collectors every few minutes while farming.', self._collect))
        card.card_layout.addWidget(Separator())
        self._alchemist = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Alchemist', help_text.ALCHEMIST, self._alchemist))
        card.card_layout.addWidget(Separator())
        self._skip_poor = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Skip poor bases', help_text.SKIP_RUN, self._skip_poor))
        card.card_layout.addWidget(Separator())
        self._treasury = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Clan Castle treasury', help_text.TREASURY, self._treasury))
        card.card_layout.addWidget(Separator())
        self._ranked = ToggleSwitch(parent = card, danger = True)
        card.card_layout.addWidget(SettingRow('Ranked attack fill', 'Uses your ranked attacks. Leave it off unless you want that.', self._ranked))
        card.card_layout.addWidget(Separator())
        self._multi_run = ToggleSwitch(parent = card)
        mr_control = QWidget()
        mr_row = QHBoxLayout(mr_control)
        mr_row.setContentsMargins(0, 0, 0, 0)
        mr_row.setSpacing(SPACING['sm'])
        edit_players = link_button('Edit list ›', parent = card)
        edit_players.setToolTip('Open the Players page (multi-run is a work in progress).')
        edit_players.clicked.connect((lambda : self._navigate_to('players')))
        mr_row.addWidget(edit_players)
        mr_row.addWidget(self._multi_run)
        card.card_layout.addWidget(SettingRow('Multi-run', 'Farms every account of the player list, top to bottom.', mr_control))
        return card


    def _build_bb_modes_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Modes'))
        self._bb_prioritise_group = QButtonGroup(self)
        self._bb_prioritise_group.setExclusive(True)
        buttons = []
        for i, label in enumerate(BUILDER_BASE_PRIORITISE_LABELS):
            btn = segment_button(label)
            if label == 'Both':
                btn.setChecked(True)
            self._bb_prioritise_group.addButton(btn, i)
            buttons.append(btn)
        prior_control = QWidget()
        prior_row = QHBoxLayout(prior_control)
        prior_row.setContentsMargins(0, 0, 0, 0)
        prior_row.setSpacing(SPACING['sm'])
        help_btn = HelpButton((lambda : show_bb_prioritise_help(self.window())), parent = card)
        help_btn.setToolTip(help_text.HELP_BB)
        prior_row.addWidget(help_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        prior_row.addWidget(segmented(buttons))
        prior_setting = SettingRow('Prioritise', 'When the bot ends each battle.', prior_control)
        bind_descriptions(buttons, help_text.BB_PRIORITISE, prior_setting.subtitle)
        card.card_layout.addWidget(prior_setting)
        card.card_layout.addWidget(Separator())
        self._bb_upgrade_walls = ToggleSwitch(parent = card)
        card.card_layout.addWidget(SettingRow('Upgrade walls', 'Builder Base walls, with their own threshold in Settings.', self._bb_upgrade_walls))
        card.card_layout.addWidget(Separator())
        self._bb_multi_run = ToggleSwitch(parent = card, under_development = True)
        bb_mr_row = SettingRow('Multi-run', 'Under development for the Builder Base.', self._bb_multi_run)
        bb_mr_row.title.setEnabled(False)
        card.card_layout.addWidget(bb_mr_row)
        return card


    @staticmethod
    def _tiles_row(*tiles):
        row = QHBoxLayout()
        row.setSpacing(10)
        for tile in tiles:
            row.addWidget(tile, 1)
        return row

    def _build_status_card(self):
        card = Card()
        card.setObjectName('HeroCard')
        head = QHBoxLayout()
        head.addWidget(SectionTitle('Live status'))
        head.addStretch()
        self._stat_state = state_pill('IDLE')
        self._state_pulse = Pulse(self._stat_state, low = 0.55)
        head.addWidget(self._stat_state)
        card.card_layout.addLayout(head)
        self._stat_runtime = StatTile('Run time')
        self._stat_gold = StatTile('Gold', dot = TOKENS['gold'])
        self._stat_elixir = StatTile('Elixir', dot = TOKENS['elixir'])
        self._stat_dark = StatTile('Dark elixir', dot = TOKENS['dark_elixir'])
        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        tiles.addWidget(self._stat_runtime, 1)
        self._loot_tiles = QWidget()
        loot_row = self._tiles_row(self._stat_gold, self._stat_elixir, self._stat_dark)
        loot_row.setContentsMargins(0, 0, 0, 0)
        self._loot_tiles.setLayout(loot_row)
        tiles.addWidget(self._loot_tiles, 3)
        tiles.addStretch(0)
        card.card_layout.addLayout(tiles)
        self._stat_loot_rate = QLabel('Per hour: shown after 10 minutes of farming.')
        self._stat_loot_rate.setObjectName('Hint')
        card.card_layout.addWidget(self._stat_loot_rate)
        self._stat_note = QLabel('Start the bot to see the live state here.')
        self._stat_note.setWordWrap(True)
        self._stat_note.setObjectName('Hint')
        card.card_layout.addWidget(self._stat_note)
        # Run time ticks once a second while the bot runs and freezes on the final
        # value when the run ends.
        self._run_started_at = None
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1000)
        self._runtime_timer.timeout.connect(self._tick_runtime)
        return card

    # ---- game preview ----
    _PREVIEW_WIDTH = 480
    _PREVIEW_MS = 3000

    def _build_preview_card(self):
        card = Card()
        head = QHBoxLayout()
        head.addWidget(SectionTitle('Game preview'))
        head.addStretch()
        self._preview_age = QLabel('')
        self._preview_age.setObjectName('Hint')
        head.addWidget(self._preview_age)
        card.card_layout.addLayout(head)
        self._preview = QLabel('Open the game to see it here.')
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(48)
        self._preview.setObjectName('Hint')
        card.card_layout.addWidget(self._preview)
        card.card_layout.addWidget(hint_label('What the bot sees, refreshed every few seconds: if it sits on a popup, you will notice here.'))
        self._preview_ws = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(self._PREVIEW_MS)
        self._preview_timer.timeout.connect(self._update_preview)
        return card

    def showEvent(self, event):
        super().showEvent(event)
        self._preview_timer.start()
        QTimer.singleShot(300, self._update_preview)

    def hideEvent(self, event):
        self._preview_timer.stop()
        super().hideEvent(event)

    def _preview_frame(self):
        '''(frame, age in s) — the bot's own last capture while it runs (no second capture
        competing with it), a fresh one otherwise.'''
        if self._controller.is_running():
            ws = self._controller.bot.window
            frame = getattr(ws, 'last_frame', None)
            return (frame, time.monotonic() - ws.last_frame_time) if frame is not None else (None, 0.0)
        if self._preview_ws is None:
            from app.services.window import WindowService
            self._preview_ws = WindowService()
        try:
            return (self._preview_ws.screenshot(), 0.0)
        except Exception:
            return (None, 0.0)

    def _update_preview(self):
        win = self.window()
        if not self.isVisible() or win.isMinimized():
            return
        (frame, age) = self._preview_frame()
        if frame is None or getattr(frame, 'size', 0) == 0:
            self._preview.setPixmap(QPixmap())
            self._preview.setMinimumHeight(48)  # no picture: do not keep a tall empty box
            self._preview.setText('Game window not found. Open Clash of Clans (16:9).')
            self._preview_age.setText('')
            return
        import cv2
        (h, w) = frame.shape[:2]
        self._preview.setMinimumHeight(int(self._PREVIEW_WIDTH * h / w) + 8)
        small = cv2.resize(frame, (self._PREVIEW_WIDTH, int(self._PREVIEW_WIDTH * h / w)), interpolation = cv2.INTER_AREA)
        image = QImage(small.data, small.shape[1], small.shape[0], small.strides[0], QImage.Format.Format_BGR888).copy()
        self._preview.setText('')
        self._preview.setPixmap(QPixmap.fromImage(image))
        self._preview_age.setText('' if age < 8 else f'last frame {int(age)} s ago')

    def _build_last_session_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Last session'))
        self._last_gold = StatTile('Gold', dot = TOKENS['gold'], small = True)
        self._last_elixir = StatTile('Elixir', dot = TOKENS['elixir'], small = True)
        self._last_walls = StatTile('Walls', small = True)
        self._last_attacks = StatTile('Attacks', small = True)
        self._last_duration = StatTile('Duration', small = True)
        card.card_layout.addLayout(self._tiles_row(self._last_gold, self._last_elixir, self._last_walls, self._last_attacks, self._last_duration))
        self._last_note = hint_label('Filled in when a run ends.')
        card.card_layout.addWidget(self._last_note)
        return card

    def _build_bb_last_session_card(self):
        '''Builder Base runs: shown in place of "Last session" while Builder Base is selected.'''
        card = Card()
        card.card_layout.addWidget(SectionTitle('Last session — Builder Base'))
        self._bb_last_attacks = StatTile('Attacks', small = True)
        self._bb_last_walls = StatTile('Walls', small = True)
        self._bb_last_duration = StatTile('Duration', small = True)
        card.card_layout.addLayout(self._tiles_row(self._bb_last_attacks, self._bb_last_walls, self._bb_last_duration))
        self._bb_last_note = hint_label('Filled in when a Builder Base run ends.')
        card.card_layout.addWidget(self._bb_last_note)
        return card

    @staticmethod
    def _fmt_duration(seconds):
        seconds = max(0, int(seconds))
        return f'{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'

    def _tick_runtime(self):
        if self._run_started_at is not None:
            self._stat_runtime.setText(self._fmt_duration(time.monotonic() - self._run_started_at))

    @staticmethod
    def _fmt_thousands(value):
        return f'{int(round(value)):,}'

    def _show_last_session(self, stats):
        self._last_gold.animate_to(int(stats.get('gold', 0)), self._fmt_thousands)
        self._last_elixir.animate_to(int(stats.get('elixir', 0)), self._fmt_thousands)
        self._last_walls.animate_to(int(stats.get('walls', 0)))
        self._last_attacks.animate_to(int(stats.get('attacks', 0)))
        self._last_duration.animate_to(int(stats.get('duration_s', 0)), self._fmt_duration)
        ended = stats.get('ended')
        self._last_note.setText(f'Ended {ended}' if ended else '')

    def _show_bb_last_session(self, stats):
        self._bb_last_attacks.animate_to(int(stats.get('attacks', 0)))
        self._bb_last_walls.animate_to(int(stats.get('walls', 0)))
        self._bb_last_duration.animate_to(int(stats.get('duration_s', 0)), self._fmt_duration)
        ended = stats.get('ended')
        self._bb_last_note.setText(f'Ended {ended}' if ended else '')

    def _on_run_summary(self, stats):
        """End of a run: refresh the Last session card and keep it across app restarts."""
        stats = dict(stats)
        stats['ended'] = datetime.now().strftime('%d/%m %H:%M')
        builder = stats.get('village') == 'builder'
        (self._show_bb_last_session if builder else self._show_last_session)(stats)
        try:
            self._settings.setValue('run/lastSessionBB' if builder else 'run/lastSession', json.dumps(stats))
        except Exception:
            pass

    def _load_last_session(self):
        try:
            raw = self._settings.value('run/lastSession', '', type = str)
            if raw:
                self._show_last_session(json.loads(raw))
        except Exception:
            pass
        try:
            raw = self._settings.value('run/lastSessionBB', '', type = str)
            if raw:
                self._show_bb_last_session(json.loads(raw))
        except Exception:
            pass

    @staticmethod
    def _fmt_amount(value):
        value = int(value)
        if value >= 1000000:
            return f'''{value / 1000000:.1f}M'''
        if value >= 10000:
            return f'''{value / 1000:.0f}k'''
        return str(value)

    # Token names, resolved when used so the colours follow the active theme.
    _STATE_COLORS = {
        'farming': 'success',  # engaged green
        'running': 'success',
        'idling': 'warning',   # holding amber
        'idle': 'text_muted',
    }

    _LIVE_STATES = ('farming', 'running')

    def _set_state(self, state):
        state = str(state)
        set_state_pill(self._stat_state, state.upper(), TOKENS[self._STATE_COLORS.get(state.lower(), 'primary_hov')])
        # The pill "breathes" while the bot is actively working.
        if state.lower() in self._LIVE_STATES:
            self._state_pulse.start()
        else:
            self._state_pulse.stop()

    def _on_state_changed(self, payload):
        state = payload.get('state')
        if state:
            self._set_state(state)
        note = payload.get('note')
        if note:
            self._stat_note.setText(f'''Upgrades: {note}''')

    def _on_loot_changed(self, gold, elixir, dark, elapsed):
        self._stat_gold.animate_to(gold, self._fmt_amount)
        self._stat_elixir.animate_to(elixir, self._fmt_amount)
        self._stat_dark.animate_to(dark, self._fmt_amount)
        if elapsed < 600:
            # A per-hour figure extrapolated from a few minutes is noise — hold it back.
            self._stat_loot_rate.setText('Per hour: shown after 10 minutes of farming.')
            return None
        hours = elapsed / 3600
        self._stat_loot_rate.setText(f'''Per hour:  {self._fmt_amount(gold / hours)} gold  ·  {self._fmt_amount(elixir / hours)} elixir  ·  {self._fmt_amount(dark / hours)} dark elixir''')

    def _on_status_line(self, msg, _warning):
        if msg.lower().startswith(('idling', 'resuming')):
            idling = msg.lower().startswith('idling')
            self._set_state('idling' if idling else 'farming')
            self._stat_note.setText(msg)

    def _confirm_bb_elixir_prioritise(self):
        reply = QMessageBox.warning(self.window(), 'Elixir priority', 'Prioritising Elixir will deplete your trophies.\n\nDo you want to continue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    
    def _build_controls(self):
        wrapper = QWidget()
        btn_row = QHBoxLayout(wrapper)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(SPACING['sm'])
        # One action at a time: Start while idle, Stop while running.
        self._btn_start = primary_button('▶   Start', parent = wrapper)
        self._btn_start.setObjectName('RunAction')
        self._btn_start.setMinimumWidth(132)
        self._btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_start.setToolTip(help_text.START)
        self._btn_start.clicked.connect(self.start_bot)
        btn_row.addWidget(self._btn_start)
        self._btn_stop = danger_button('■   Stop', parent = wrapper)
        self._btn_stop.setObjectName('RunAction')
        self._btn_stop.setMinimumWidth(132)
        self._btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_stop.setToolTip(help_text.STOP)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setVisible(False)
        self._btn_stop.clicked.connect(self._controller.stop)
        btn_row.addWidget(self._btn_stop)
        # Soft glow fades in under the mouse.
        glow = QColor(TOKENS['go'])
        glow.setAlpha(120)
        HoverGlow(self._btn_start, glow)
        glow = QColor(TOKENS['danger'])
        glow.setAlpha(120)
        HoverGlow(self._btn_stop, glow)
        return wrapper

    def _show_running(self, running):
        self._btn_start.setEnabled(not running)
        self._btn_start.setVisible(not running)
        self._btn_stop.setEnabled(running)
        self._btn_stop.setVisible(running)

    
    def _clear_minutes_selection(self):
        editor = self._minutes_spin.lineEdit()
        if not editor is None:
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))
            return None

    
    def _duration_locked(self):
        return self._star_bonus.isChecked() or self._until_maxed.isChecked()

    def _step_minutes(self, delta):
        if self._duration_locked():
            return None
        if delta > 0:
            self._minutes_spin.stepUp()
        else:
            self._minutes_spin.stepDown()
        self._clear_minutes_selection()
        QTimer.singleShot(0, self._clear_minutes_selection)


    def _set_minutes(self, value):
        if self._duration_locked():
            return None
        self._minutes_spin.setValue(value)
        self._clear_minutes_selection()


    def _update_duration_enabled(self):
        enabled = not self._duration_locked()
        duration_widgets = (self._duration_label, self._duration_hint, self._minutes_spin, self._btn_spin_up, self._btn_spin_down, self._minutes_unit, *self._duration_chips)
        for widget in duration_widgets:
            widget.setEnabled(enabled)
        if enabled:
            self._minutes_unit.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
            return None
        self._minutes_unit.setStyleSheet(f'''color: {TOKENS['text_faint']};''')

    def _on_star_bonus_toggle(self, checked):
        if checked and getattr(self, '_until_maxed', None) is not None and self._until_maxed.isChecked():
            self._until_maxed.setChecked(False)
        self._update_duration_enabled()

    def _on_until_maxed_toggle(self, checked):
        if checked and self._star_bonus.isChecked():
            self._star_bonus.setChecked(False)
        self._update_duration_enabled()

    
    def _get_method(self):
        if self._is_builder_base():
            btn = self._bb_strategy_group.checkedButton()
            if btn is None:
                return BUILDER_BASE_ATTACK_STRATEGIES['Baby Dragon']
            return BUILDER_BASE_ATTACK_STRATEGIES.get(btn.text(), 5)
        btn = self._strategy_group.checkedButton()
        if btn is None:
            return ATTACK_STRATEGIES['Valkyries']
        return ATTACK_STRATEGIES.get(btn.text(), 1)

    
    def _get_bb_prioritise(self):
        btn = self._bb_prioritise_group.checkedButton()
        if btn is None:
            return 'both'
        return btn.text().lower()


    def _get_auto_upgrade_mode(self):
        checked_id = self._auto_upgrade_group.checkedId()
        if 0 <= checked_id < len(self._AUTO_UPGRADE_LABELS):
            return self._AUTO_UPGRADE_LABELS[checked_id][1]
        return 'off'

    def _set_auto_upgrade_mode(self, mode):
        for i, (_label, key) in enumerate(self._AUTO_UPGRADE_LABELS):
            if key == mode:
                btn = self._auto_upgrade_group.button(i)
                if btn is not None:
                    btn.setChecked(True)
                return None

    @staticmethod
    def _check_by_text(group, text):
        '''Check the button of ``group`` labelled ``text``; False when there is none.'''
        for btn in group.buttons():
            if btn.text() == text:
                btn.setChecked(True)
                return True
        return False

    @staticmethod
    def _checked_text(group):
        btn = group.checkedButton()
        return '' if btn is None else btn.text()

    def _restore_choices(self):
        '''Bring back the last run's choices across app starts: village, army, Builder Base
        mode, toggles and duration (saved when Start is pressed).'''
        self._check_by_text(self._village_group, str(self._settings.value('run/village', 'Home Village')))
        self._apply_village_ui()
        self._check_by_text(self._strategy_group, str(self._settings.value('run/strategy', 'Valkyries')))
        self._check_by_text(self._bb_strategy_group, str(self._settings.value('run/bbStrategy', 'Baby Dragon')))
        self._check_by_text(self._bb_prioritise_group, str(self._settings.value('run/bbPrioritise', 'Both')))
        self._collect.setChecked(self._settings.value('run/collectResources', False, type = bool))
        self._alchemist.setChecked(self._settings.value('run/alchemist', False, type = bool))
        self._treasury.setChecked(self._settings.value('run/treasury', False, type = bool))
        self._skip_poor.setChecked(self._settings.value('run/skipPoor', False, type = bool))
        self._ranked.setChecked(self._settings.value('run/ranked', False, type = bool))
        self._multi_run.setChecked(self._settings.value('run/multiRun', False, type = bool))
        self._set_auto_upgrade_mode(str(self._settings.value('run/autoUpgrade', 'off')))
        self._upgrade_walls.setChecked(self._settings.value('run/upgradeWalls', False, type = bool))
        self._bb_upgrade_walls.setChecked(self._settings.value('run/bbUpgradeWalls', False, type = bool))
        self._until_maxed.setChecked(self._settings.value('run/untilMaxed', False, type = bool))
        minutes = self._settings.value('run/minutes', 15, type = int)
        if 1 <= minutes <= 999:
            self._minutes_spin.setValue(minutes)
        saved_time = QTime.fromString(str(self._settings.value('run/scheduleTime', '02:00')), 'HH:mm')
        if saved_time.isValid():
            self._schedule_time.setTime(saved_time)
        self._schedule_on.setChecked(self._settings.value('run/scheduleOn', False, type = bool))
        # After "until maxed": the two switches turn each other off.
        if self._settings.value('run/starBonus', False, type = bool):
            self._star_bonus.setChecked(True)

    def _save_choices(self):
        self._settings.setValue('run/village', self._checked_text(self._village_group))
        self._settings.setValue('run/strategy', self._checked_text(self._strategy_group))
        self._settings.setValue('run/bbStrategy', self._checked_text(self._bb_strategy_group))
        self._settings.setValue('run/bbPrioritise', self._checked_text(self._bb_prioritise_group))
        self._settings.setValue('run/starBonus', self._star_bonus.isChecked())
        self._settings.setValue('run/collectResources', self._collect.isChecked())
        self._settings.setValue('run/alchemist', self._alchemist.isChecked())
        self._settings.setValue('run/treasury', self._treasury.isChecked())
        self._settings.setValue('run/skipPoor', self._skip_poor.isChecked())
        self._settings.setValue('run/ranked', self._ranked.isChecked())
        self._settings.setValue('run/multiRun', self._multi_run.isChecked())
        self._settings.setValue('run/autoUpgrade', self._get_auto_upgrade_mode())
        self._settings.setValue('run/upgradeWalls', self._upgrade_walls.isChecked())
        self._settings.setValue('run/bbUpgradeWalls', self._bb_upgrade_walls.isChecked())
        self._settings.setValue('run/untilMaxed', self._until_maxed.isChecked())
        self._settings.setValue('run/minutes', self._minutes_spin.value())

    
    def _get_minutes(self):
        return self._minutes_spin.value()

    
    def _multi_run_players_for_start(self):
        if self._is_builder_base() or not self._multi_run.isChecked():  # [recovered: decompiler inverted both halves — multi-run never engaged on Home Village]
            return None
        players = load_players()
        if not any([ p.enabled and p.name.strip() for p in players ]):
            return []
        return players

    
    def _refuse(self, unattended, title, message):
        '''A start that cannot go ahead: a dialog for a person, a notification for the schedule
        (nobody is there to click a dialog away).'''
        if unattended:
            self.scheduleMessage.emit(message)
        else:
            show_error(self.window(), title, message)

    @staticmethod
    def _game_window_ready():
        '''(ok, reason) without any dialog: the game window exists and is ~16:9 / ~16:10.'''
        from app.config import resolve_aspect_key
        from app.services.window import WindowService
        size = WindowService().get_outer_pixel_size()
        if size is None:
            return (False, 'The Clash of Clans window was not found. Open the game first.')
        if resolve_aspect_key(*size) is None:
            return (False, f'The game window is {size[0]}x{size[1]}: it must be about 16:9.')
        return (True, '')

    def start_bot(self, *_args, unattended = False):
        if self._controller.is_running():
            return None
        if unattended:
            (ok, reason) = self._game_window_ready()
            if not ok:
                self.scheduleMessage.emit(reason)
                return None
        elif not check_game_window_aspect_for_start(parent = self.window(), on_configure = (lambda : self._navigate_to('settings'))):
            return None
        builder_base = self._is_builder_base()
        method = self._get_method()
        multi_arg = self._multi_run_players_for_start()
        if not builder_base and self._multi_run.isChecked() and not multi_arg:  # [recovered: decompiler dropped the `not` — the error fired when players DID exist]
            self._refuse(unattended, 'Multi-run', 'Enable at least one player with Run and a non-empty name.\nOpen Player list… to edit.')
            return None
        star_bonus = self._star_bonus.isChecked()
        # "Run until maxed" = unlimited duration; single runs (either village) only.
        until_maxed = (not star_bonus and multi_arg is None
                       and self._until_maxed.isChecked())
        if star_bonus:
            mins = 5
        elif until_maxed:
            mins = 0
        else:
            mins = self._get_minutes()
            if mins <= 0 or mins > 999:
                self._refuse(unattended, 'Error', 'Invalid time duration. Enter 1-999 minutes.')
                return None
        ranked_fill = False if builder_base else self._ranked.isChecked()
        if ranked_fill:
            if unattended:
                # Ranked attacks need a person's confirmation: never spent by a timer.
                self.scheduleMessage.emit('Not started: "Ranked attack fill" needs your confirmation. Start it by hand.')
                return None
            confirm_mins = self._get_minutes()
            if not RankedAttackConfirmDialog.ask(self.window(), confirm_mins):
                return None
        if builder_base and self._get_bb_prioritise() == 'elixir':
            if unattended:
                self.scheduleMessage.emit('Not started: Builder Base "Elixir" priority lowers your trophies and needs your confirmation.')
                return None
            if not self._confirm_bb_elixir_prioritise():  # [recovered: decompiler inverted both conditions]
                return None
        self._save_choices()
        self._controller.start(method = method, minutes = mins, star_bonus = star_bonus, ranked_fill = ranked_fill, upgrade_walls = self._bb_upgrade_walls.isChecked() if builder_base else self._upgrade_walls.isChecked(), multi_run_players = multi_arg, builder_base = builder_base, loot_prioritise = self._get_bb_prioritise() if builder_base else 'both', auto_upgrade = 'off' if builder_base else self._get_auto_upgrade_mode(), collect_resources = False if builder_base else self._collect.isChecked(), use_alchemist = False if builder_base else self._alchemist.isChecked(), collect_treasury = False if builder_base else self._treasury.isChecked(), skip_poor_bases = False if builder_base else (self._skip_poor.isChecked() and not ranked_fill))

    
    def is_star_bonus_enabled(self):
        return self._star_bonus.isChecked()

    
    def request_start_from_taskbar(self):
        if not self._controller.is_running():
            self.start_bot()
            return None


    def apply_autostart(self, minutes, upgrade_walls, auto_upgrade = 'off', builder_base = False):
        '''CLI ``--autostart``: run with the given duration (``0`` = run until maxed),
        wall toggle, and auto-upgrade mode (off|dry|maxer|rusher); ``builder_base``
        selects the Builder Base (its own wall toggle; auto-upgrade is Home only).'''
        if self._controller.is_running():
            return None
        target = 'Builder Base' if builder_base else 'Home Village'
        for btn in self._village_group.buttons():
            if btn.text() == target:
                btn.setChecked(True)
        self._apply_village_ui()
        self._star_bonus.setChecked(False)
        self._until_maxed.setChecked(minutes <= 0)
        if minutes > 0:
            self._minutes_spin.setValue(minutes)
        if builder_base:
            self._bb_upgrade_walls.setChecked(bool(upgrade_walls))
        else:
            self._upgrade_walls.setChecked(bool(upgrade_walls))
            self._set_auto_upgrade_mode(auto_upgrade)
        self.start_bot()

    
    def request_stop_from_taskbar(self):
        if self._controller.is_running():
            self._controller.stop()
            return None

    
    def _on_bot_started(self):
        self._show_running(True)
        self._set_state('running')
        self._run_started_at = time.monotonic()
        self._stat_runtime.setText(self._fmt_duration(0))
        self._runtime_timer.start()


    def _on_bot_finished_ui(self, _error):
        self._show_running(False)
        self._set_state('idle')
        self._tick_runtime()  # the final value stays on screen
        self._runtime_timer.stop()
        self._run_started_at = None


    def _on_running_changed(self, running):
        self._show_running(running)


