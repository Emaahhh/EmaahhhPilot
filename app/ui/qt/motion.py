'''120 fps animation engine for the UI.

Qt's own animations tick at ~60 Hz and PySide6 does not expose QAnimationDriver to change
that, so the UI's animations use :class:`SmoothAnimation`, driven by one shared precise
timer at ``FPS``. Values are computed from the real elapsed time (not by counting ticks),
so a late frame never slows an animation down — it just lands where it should be.

On Windows the system timer resolution is raised to 1 ms only while something is
animating (``timeBeginPeriod``), so 8 ms frames are actually 8 ms; it is released as soon
as the last animation ends.
'''
from __future__ import annotations
import sys
from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QElapsedTimer, QObject, QTimer, Qt, Signal

FPS = 120
FRAME_MS = max(1, round(1000 / FPS))


def _set_hires_timer(on):
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        (winmm.timeBeginPeriod if on else winmm.timeEndPeriod)(1)
    except Exception:
        pass


class _Ticker(QObject):
    '''One precise timer shared by every running SmoothAnimation.'''

    def __init__(self):
        super().__init__()
        self._clock = QElapsedTimer()
        self._clock.start()
        # Single-shot timer re-armed every frame against a fixed schedule (frame N is due
        # at start + N * period): a late frame shortens the next wait instead of pushing
        # every following frame back, so the average stays on FPS.
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)
        self._period = 1000.0 / FPS
        self._next_due = 0.0
        self._anims = []
        self._hires = False
        self.frames = 0  # frames rendered (for measuring the real rate)

    def now(self):
        return self._clock.nsecsElapsed() / 1e6  # ms, sub-millisecond precision

    def add(self, anim):
        if anim not in self._anims:
            self._anims.append(anim)
        if not self._timer.isActive():
            if not self._hires:
                _set_hires_timer(True)
                self._hires = True
            self._next_due = self.now() + self._period
            self._arm()

    def _arm(self):
        now = self.now()
        if self._next_due < now - self._period:
            # Fell more than a frame behind (busy UI): resync instead of bursting.
            self._next_due = now + self._period
        self._timer.start(max(0, int(self._next_due - now)))

    def remove(self, anim):
        if anim in self._anims:
            self._anims.remove(anim)
        if not self._anims:
            self._timer.stop()
            if self._hires:
                _set_hires_timer(False)
                self._hires = False

    def _tick(self):
        now = self.now()
        if now < self._next_due - 0.5:
            # Woke up early (timer rounding): wait for the frame's real time.
            self._arm()
            return
        self.frames += 1
        self._next_due += self._period
        for anim in list(self._anims):
            try:
                anim._advance(now)
            except RuntimeError:
                # Its widget was deleted mid-animation.
                self.remove(anim)
        if self._anims:
            self._arm()
        elif self._hires:
            _set_hires_timer(False)
            self._hires = False


_TICKER = None


def ticker():
    global _TICKER
    if _TICKER is None:
        _TICKER = _Ticker()
    return _TICKER


class SmoothAnimation(QObject):
    '''Float animation from ``startValue`` to ``endValue`` at FPS frames per second.
    Same calls as the QVariantAnimation subset the UI uses.'''

    valueChanged = Signal(float)
    finished = Signal()
    State = QAbstractAnimation.State

    def __init__(self, parent = None):
        super().__init__(parent)
        self._duration = 250
        self._curve = QEasingCurve(QEasingCurve.Type.Linear)  # same default as Qt
        self._start = 0.0
        self._end = 1.0
        self._loops = 1
        self._t0 = 0.0
        self._running = False
        self._value = 0.0

    # --- configuration -------------------------------------------------------
    def setDuration(self, ms):
        self._duration = max(1, int(ms))

    def duration(self):
        return self._duration

    def setEasingCurve(self, curve):
        self._curve = QEasingCurve(curve)

    def setStartValue(self, value):
        self._start = float(value)

    def setEndValue(self, value):
        self._end = float(value)

    def setLoopCount(self, loops):
        self._loops = loops

    def currentValue(self):
        return self._value

    # --- control ------------------------------------------------------------
    def state(self):
        return self.State.Running if self._running else self.State.Stopped

    def start(self):
        self.stop()
        self._t0 = ticker().now()
        self._running = True
        ticker().add(self)
        self._emit(self._start)

    def stop(self):
        if self._running:
            self._running = False
            ticker().remove(self)

    def _emit(self, value):
        self._value = value
        self.valueChanged.emit(value)

    def _advance(self, now):
        if not self._running:
            return
        elapsed = now - self._t0
        if self._loops == -1:
            progress = (elapsed % self._duration) / self._duration
        else:
            progress = min(1.0, elapsed / self._duration)
        eased = self._curve.valueForProgress(progress)
        self._emit(self._start + (self._end - self._start) * eased)
        if self._loops != -1 and progress >= 1.0:
            self.stop()
            self.finished.emit()
