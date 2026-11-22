'''UI animations: they run, end on the real state, and never leave a widget half-way.'''
import _testenv  # noqa: F401 — must precede the app imports (test log folder)
import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    from PySide6.QtCore import QAbstractAnimation
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QButtonGroup, QWidget, QVBoxLayout
except ImportError:  # pragma: no cover - PySide6 missing
    QApplication = None


def _app():
    app = QApplication.instance() or QApplication([])
    from app.ui.qt.theme import apply_theme
    apply_theme(app)
    return app


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class ToggleSwitchAnimationTests(unittest.TestCase):

    def setUp(self):
        _app()
        from app.ui.qt.widgets import ToggleSwitch
        self.host = QWidget()
        self.switch = ToggleSwitch(parent = self.host)
        self.host.show()
        QTest.qWaitForWindowExposed(self.host)

    def tearDown(self):
        self.host.close()

    def test_knob_slides_and_ends_on(self):
        self.switch.setChecked(True)
        self.assertEqual(self.switch._anim.state(), QAbstractAnimation.State.Running)
        QTest.qWait(self.switch._anim.duration() + 120)
        self.assertEqual(self.switch._pos, 1.0)
        self.switch.setChecked(False)
        QTest.qWait(self.switch._anim.duration() + 120)
        self.assertEqual(self.switch._pos, 0.0)

    def test_hidden_switch_jumps_without_animating(self):
        from app.ui.qt.widgets import ToggleSwitch
        hidden = ToggleSwitch()
        hidden.setChecked(True)
        self.assertNotEqual(hidden._anim.state(), QAbstractAnimation.State.Running)
        self.assertEqual(hidden._pos, 1.0)


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class SegmentedIndicatorTests(unittest.TestCase):

    def test_pill_slides_onto_the_checked_button(self):
        _app()
        from app.ui.qt.widgets import segment_button, segmented
        host = QWidget()
        layout = QVBoxLayout(host)
        buttons = [segment_button(t) for t in ('One', 'Two', 'Three')]
        group = QButtonGroup(host)
        for b in buttons:
            group.addButton(b)
        buttons[0].setChecked(True)
        track = segmented(buttons, stretch = True)
        layout.addWidget(track)
        host.resize(500, 80)
        host.show()
        QTest.qWaitForWindowExposed(host)
        QTest.qWait(50)
        from PySide6.QtCore import QRectF
        self.assertEqual(track.lens_rect(), QRectF(buttons[0].geometry()))
        buttons[2].click()
        QTest.qWait(30)
        self.assertNotEqual(track.lens_rect(), QRectF(buttons[2].geometry()))  # still moving
        # Liquid: half-way the lens is stretched longer than a segment, and thinner.
        track._flow(0.5)
        mid = track.lens_rect()
        self.assertGreater(mid.width(), buttons[0].width())
        self.assertLess(mid.height(), buttons[0].height())
        # Sub-pixel: positions are not rounded to whole pixels.
        track._flow(0.37)
        self.assertNotEqual(track.lens_rect().x(), round(track.lens_rect().x()))
        QTest.qWait(track._anim.duration() + 150)
        self.assertEqual(track.lens_rect(), QRectF(buttons[2].geometry()))
        host.close()


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class FrameRateTests(unittest.TestCase):

    def test_engine_ticks_near_120_fps(self):
        _app()
        from app.ui.qt.motion import FPS, SmoothAnimation, ticker
        anim = SmoothAnimation()
        anim.setDuration(1000)
        before = ticker().frames
        anim.start()
        QTest.qWait(500)
        frames = ticker().frames - before
        anim.stop()
        rate = frames / 0.5
        print(f'\n  measured animation rate: {rate:.0f} fps (target {FPS})')
        self.assertGreater(rate, 0.75 * FPS)

    def test_timer_stops_when_nothing_animates(self):
        _app()
        from app.ui.qt.motion import SmoothAnimation, ticker
        anim = SmoothAnimation()
        anim.setDuration(50)
        anim.start()
        QTest.qWait(150)
        self.assertFalse(ticker()._timer.isActive())
        self.assertFalse(ticker()._hires)


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class CountUpAndPulseTests(unittest.TestCase):

    def test_tile_counts_up_to_the_exact_value(self):
        _app()
        from app.ui.qt.widgets import StatTile
        tile = StatTile('Gold')
        tile.show()
        QTest.qWaitForWindowExposed(tile)
        tile.animate_to(1_234_567, lambda v: f'{int(round(v)):,}')
        QTest.qWait(60)
        self.assertNotEqual(tile.text(), '1,234,567')  # mid-count
        QTest.qWait(tile._count.duration() + 200)
        self.assertEqual(tile.text(), '1,234,567')
        tile.setText('—')  # a plain setText stops any running count
        self.assertEqual(tile.text(), '—')
        tile.close()

    def test_pulse_starts_and_stops_cleanly(self):
        _app()
        from app.ui.qt.widgets import Pulse
        from PySide6.QtWidgets import QLabel
        label = QLabel('●')
        pulse = Pulse(label)
        pulse.start()
        pulse.start()  # idempotent
        self.assertTrue(pulse.is_running())
        self.assertIsNotNone(label.graphicsEffect())
        pulse.stop()
        self.assertFalse(pulse.is_running())
        self.assertIsNone(label.graphicsEffect())

    def test_pulse_wave_is_seamless(self):
        _app()
        from app.ui.qt.widgets import Pulse
        from PySide6.QtWidgets import QLabel
        label = QLabel('●')
        pulse = Pulse(label, low = 0.4)
        pulse.start()
        values = []
        for phase in (0.0, 0.25, 0.5, 0.75, 1.0):
            pulse._apply(phase)
            values.append(round(label.graphicsEffect().opacity(), 3))
        pulse.stop()
        self.assertEqual(values[0], 1.0)
        self.assertEqual(values[2], 0.4)
        self.assertEqual(values[0], values[4])  # loop restart: no jump
        self.assertEqual(values[1], values[3])  # symmetric wave


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class PageTransitionTests(unittest.TestCase):

    def test_transition_runs_then_cleans_up(self):
        _app()
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import QRect
        from app.ui.qt.widgets import PageTransition
        host = QWidget()
        host.resize(300, 200)
        host.show()
        QTest.qWaitForWindowExposed(host)
        (old, new) = (QPixmap(300, 200), QPixmap(300, 200))
        done = []
        overlay = PageTransition(host, old, new, QRect(0, 0, 300, 200), on_done = lambda: done.append(True))
        overlay.start()
        QTest.qWait(40)
        self.assertTrue(overlay.isVisible())
        self.assertTrue(0.0 < overlay._t < 1.0)
        QTest.qWait(overlay._anim.duration() + 150)
        self.assertEqual(done, [True])
        host.close()


if __name__ == '__main__':
    unittest.main()
