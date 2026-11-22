'''Bot orchestration for the Qt UI.'''
from __future__ import annotations
import threading
from PySide6.QtCore import QObject, Signal
from app.core.bot import Bot
from app.ui.qt._constants import ATTACK_STRATEGIES, BUILDER_BASE_ATTACK_STRATEGIES
from app.utils.history_store import append_session
from app.utils.logger import setup_logger
from app.utils.profile_settings_store import load_profile_settings
logger = setup_logger('BotController')
_ARMY_BY_METHOD = {v: k for (k, v) in {**ATTACK_STRATEGIES, **BUILDER_BASE_ATTACK_STRATEGIES}.items()}

class BotController(QObject):
    statusChanged = Signal(str, bool)
    botStarted = Signal()
    botFinished = Signal(object)
    runningChanged = Signal(bool)
    # Live village state from the bot thread: dict with any of
    # state/builders/lab/storages/note (missing keys = unchanged/unknown).
    stateChanged = Signal(dict)
    # Session loot totals: gold, elixir, dark elixir, elapsed seconds.
    lootChanged = Signal(int, int, int, float)
    # End-of-run numbers {gold, elixir, walls, attacks} for the "Last session" card —
    # emitted right before botFinished (the full text report stays in the log).
    runSummary = Signal(dict)
    # A finished run was added to the saved history (the History page reloads).
    historyChanged = Signal()

    def __init__(self, bot_version):
        super().__init__()
        self._bot_version = bot_version
        self._bot = Bot()
        self._bot_thread = None

    @property
    def bot(self):
        return self._bot


    def is_running(self):
        return self._bot_thread is not None and self._bot_thread.is_alive()


    def start(self, *, method, minutes, star_bonus, ranked_fill, upgrade_walls, multi_run_players, builder_base = False, loot_prioritise = 'both', auto_upgrade = 'off', collect_resources = False):
        '''``minutes <= 0`` = unlimited ("run until maxed") — single Home Village runs only.'''
        if self.is_running():
            return None

        def worker():
            error_msg = None

            def on_status(msg):
                self.statusChanged.emit(msg, 'not found' in msg.lower())

            def on_state(payload):
                self.stateChanged.emit(dict(payload))

            def on_loot(gold, elixir, dark, elapsed):
                self.lootChanged.emit(int(gold), int(elixir), int(dark), float(elapsed))


            try:
                profile = load_profile_settings()
                self._bot.start(method, minutes, star_bonus = star_bonus, status_callback = on_status, loot_callback = on_loot, state_callback = on_state, multi_run_players = multi_run_players, ranked_fill = ranked_fill, upgrade_walls = upgrade_walls, earthquake_method = profile.earthquake_method, builder_base = builder_base, loot_prioritise = loot_prioritise, wall_upgrade_threshold = profile.wall_upgrade_threshold_m * 1000000, bb_wall_upgrade_threshold = round(profile.bb_wall_upgrade_threshold_m * 1000000), auto_upgrade = auto_upgrade, reserve_builders = profile.reserve_builders, upgrade_order = profile.upgrade_order, wall_order = profile.wall_order, collect_resources = collect_resources)
            except InterruptedError:
                logger.info('Bot thread stopped by user')
            except Exception as exc:
                error_msg = str(exc)
                logger.exception('Bot thread failed')
            stats = getattr(self._bot, 'last_run_stats', None)
            if stats:
                stats = dict(stats)
                if append_session(stats, _ARMY_BY_METHOD.get(method, str(method))) is not None:
                    self.historyChanged.emit()
                self.runSummary.emit(stats)
            self.botFinished.emit(error_msg)

        self._bot_thread = threading.Thread(target = worker, daemon = True, name = 'BotThread')
        self.runningChanged.emit(True)
        self.botStarted.emit()
        self._bot_thread.start()


    def stop(self):
        self._bot.stop()
        self.statusChanged.emit('Stopping...', False)


    def wait_stopped(self, timeout):
        '''Block up to ``timeout`` s for the bot thread to finish (app close: lets the run
        release the mouse and write its summary before the daemon thread is killed).'''
        thread = self._bot_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout)


    def on_bot_finished(self):
        self.runningChanged.emit(False)
