'''Reusable Qt widgets for the EmaahhhPilot UI.'''
from __future__ import annotations
import math
from collections.abc import Callable
from typing import Optional
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QTimer, Qt, QRectF, QSize, QPointF
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QCheckBox, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from app.ui.qt.motion import SmoothAnimation
from app.ui.qt.theme import SPACING, TOKENS

# Animation timings (ms) and curves: long enough to read as motion, short enough to
# never slow the user down. In-out curves start and stop gently (no snap at either end).
ANIM_FAST = 240
ANIM_MEDIUM = 340
ANIM_COUNT = 900
EASE_MOVE = QEasingCurve.Type.InOutCubic   # things that travel (knob, pill)
EASE_FADE = QEasingCurve.Type.OutQuart     # fades / glows / counters: fast start, long soft landing
# "Liquid glass": travelling lenses stretch along the motion and settle back round.
LIQUID_DURATION = 420
LIQUID_STRETCH = 0.22   # extra length mid-travel, as a share of the distance covered


def _mix(a, b, t):
    '''Colour between ``a`` (t=0) and ``b`` (t=1).'''
    (a, b) = (QColor(a), QColor(b))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t))

class Backdrop(QWidget):
    '''Window background seen through the glass panels: deep navy with large, soft colour
    glows (cream top-right, blue bottom-left, violet low centre). Rendered once per size
    into a pixmap, so repaints during animations only copy pixels.'''

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._cache = None

    def resizeEvent(self, event):
        self._cache = None
        super().resizeEvent(event)

    def _render(self):
        (w, h) = (max(1, self.width()), max(1, self.height()))
        ratio = self.devicePixelRatioF()
        pix = QPixmap(int(w * ratio), int(h * ratio))
        pix.setDevicePixelRatio(ratio)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QLinearGradient(0, 0, w, h)
        base.setColorAt(0, QColor(TOKENS['bg']))
        base.setColorAt(1, QColor(TOKENS['bg_2']))
        p.fillRect(0, 0, w, h, base)
        for (cx, cy, rad, color, alpha) in (
                (0.86 * w, 0.06 * h, 0.55 * max(w, h), TOKENS['glow_cream'], 60),
                (0.18 * w, 0.96 * h, 0.62 * max(w, h), TOKENS['glow_blue'], 92),
                (0.62 * w, 0.72 * h, 0.42 * max(w, h), TOKENS['glow_violet'], 62)):
            c = QColor(color)
            glow = QRadialGradient(QPointF(cx, cy), rad)
            c.setAlpha(alpha)
            glow.setColorAt(0, c)
            c.setAlpha(alpha // 3)
            glow.setColorAt(0.45, c)
            c.setAlpha(0)
            glow.setColorAt(1, c)
            p.fillRect(0, 0, w, h, glow)
        p.end()
        return pix

    def paintEvent(self, event):
        if self._cache is None or self._cache.deviceIndependentSize().toSize() != self.size():
            self._cache = self._render()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)  # clipped by Qt to the region being repainted
        p.end()


class Card(QFrame):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setObjectName('Card')
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 20)
        self._layout.setSpacing(12)

    
    @property
    def card_layout(self):
        return self._layout



class SectionTitle(QLabel):
    '''Instrument-panel micro-label: uppercase + letter-spaced (QSS cannot express
    either, so the widget owns them; color/size stay in the stylesheet).'''

    def __init__(self, text, parent = None):
        super().__init__(text.upper(), parent)
        self.setObjectName('SectionTitle')
        self.setAutoFillBackground(False)
        font = self.font()
        font.setLetterSpacing(font.SpacingType.PercentageSpacing, 108)
        self.setFont(font)



class PageTitle(QLabel):

    def __init__(self, text, parent = None):
        super().__init__(text, parent)
        self.setObjectName('PageTitle')


def page_header(title, subtitle = None, right = None):
    '''Page title with an optional grey subtitle under it and a widget on the right.'''
    row = QHBoxLayout()
    row.setSpacing(SPACING['sm'])
    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(PageTitle(title))
    if subtitle:
        sub = QLabel(subtitle)
        sub.setObjectName('PageSubtitle')
        col.addWidget(sub)
    row.addLayout(col)
    row.addStretch()
    if right is not None:
        row.addWidget(right, alignment = Qt.AlignmentFlag.AlignVCenter)
    return row


class SegmentedTrack(QFrame):
    '''iOS-style segmented control: a rounded track holding ``role="segment"`` buttons and
    one clear-glass lens behind them that flows to the checked button.

    The lens is painted by the track itself in floating-point coordinates (sub-pixel,
    antialiased), so it glides instead of stepping a whole pixel at a time.'''

    LENS_RADIUS = 13

    def __init__(self, buttons, *, stretch = False, parent = None):
        super().__init__(parent)
        self.setObjectName('Segmented')
        self._lens = QRectF()
        self._lens_on = False
        self._buttons = list(buttons)
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        for btn in self._buttons:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(btn, 1 if stretch else 0)
            btn.toggled.connect(self._on_toggled)
        if not stretch:
            self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        # Progress 0→1; the lens rectangle is computed per frame so it can "flow":
        # it stretches along the travel and thins a little mid-way, like a droplet.
        self._from = QRectF()
        self._to = QRectF()
        self._anim = SmoothAnimation(self)
        self._anim.setDuration(LIQUID_DURATION)
        self._anim.setEasingCurve(EASE_MOVE)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._flow)
        self._anim.finished.connect(lambda: self._set_lens(self._to))

    def lens_rect(self):
        '''Where the lens is now (QRectF, track coordinates); empty when hidden.'''
        return QRectF(self._lens) if self._lens_on else QRectF()

    def _set_lens(self, rect):
        self._lens = QRectF(rect)
        self._lens_on = True
        self.update()

    def _flow(self, value):
        t = float(value)
        (a, b) = (self._from, self._to)
        x = a.x() + (b.x() - a.x()) * t
        w = a.width() + (b.width() - a.width()) * t
        y = a.y() + (b.y() - a.y()) * t
        h = a.height() + (b.height() - a.height()) * t
        bulge = math.sin(math.pi * t)
        stretch = abs(b.center().x() - a.center().x()) * LIQUID_STRETCH * bulge
        thin = min(4.0, h * 0.12) * bulge
        self._set_lens(QRectF(x - stretch / 2, y + thin / 2, w + stretch, h - thin))

    def paintEvent(self, event):
        super().paintEvent(event)  # the track itself (stylesheet)
        if not self._lens_on or self._lens.isEmpty():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._lens.adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(self.LENS_RADIUS, rect.height() / 2)
        body = QLinearGradient(0, rect.top(), 0, rect.bottom())
        body.setColorAt(0, QColor(255, 255, 255, 62))
        body.setColorAt(1, QColor(255, 255, 255, 26))
        p.setBrush(body)
        p.setPen(QPen(QColor(255, 255, 255, 58), 1))
        p.drawRoundedRect(rect, radius, radius)
        # Specular highlight along the top edge.
        p.setClipRect(QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.45))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 140), 1))
        p.drawRoundedRect(rect, radius, radius)
        p.end()

    def _checked(self):
        for btn in self._buttons:
            if btn.isCheckable() and btn.isChecked():
                return btn
        return None

    def _on_toggled(self, on):
        if on:
            self._move(animated = True)

    def _move(self, animated):
        btn = self._checked()
        if btn is None:
            self._anim.stop()
            self._lens_on = False
            self.update()
            return
        target = QRectF(btn.geometry())
        if not animated or not self.isVisible() or not self._lens_on or target.isEmpty():
            self._anim.stop()
            self._set_lens(target)
            return
        self._anim.stop()
        self._from = QRectF(self._lens)
        self._to = target
        self._anim.start()

    def _snap(self):
        if self._anim.state() != SmoothAnimation.State.Running:
            self._move(animated = False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Button geometry is settled once the layout has run.
        QTimer.singleShot(0, self._snap)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._snap)


def segmented(buttons, *, stretch = False, parent = None):
    '''iOS-style segmented control (see :class:`SegmentedTrack`).
    ``stretch`` makes the segments share the full width.'''
    return SegmentedTrack(buttons, stretch = stretch, parent = parent)


def bind_descriptions(buttons, descriptions, label = None):
    '''Give every button of a selector its description as a tooltip and, when ``label`` is
    given, keep that label showing the description of the CHOSEN option.
    ``descriptions`` maps the button text to its description.'''
    for btn in buttons:
        text = descriptions.get(btn.text(), '')
        if text:
            btn.setToolTip(text)
    if label is None:
        return

    def refresh(*_args):
        for btn in buttons:
            if btn.isCheckable() and btn.isChecked():
                label.setText(descriptions.get(btn.text(), ''))
                return

    for btn in buttons:
        btn.toggled.connect(refresh)
    refresh()


def set_tip(widget, text):
    '''Tooltip + accessible description (screen readers) in one call.'''
    widget.setToolTip(text)
    widget.setAccessibleDescription(text)
    return widget


class SettingRow(QWidget):
    '''One row of a grouped card: bold title, optional grey description, control on the right.'''

    def __init__(self, title, subtitle = None, control = None, parent = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(SPACING['md'])
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName('RowTitle')
        text.addWidget(self.title)
        self.subtitle = None
        if subtitle:
            self.subtitle = QLabel(subtitle)
            self.subtitle.setObjectName('RowSubtitle')
            self.subtitle.setWordWrap(True)
            text.addWidget(self.subtitle)
        row.addLayout(text, 1)
        if control is not None:
            row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
            # The row's description doubles as the tooltip of its control and title.
            if subtitle and not control.toolTip():
                set_tip(control, subtitle)
        if subtitle:
            set_tip(self.title, subtitle)

    def set_subtitle(self, text):
        if self.subtitle is not None:
            self.subtitle.setText(text)


class StatTile(QFrame):
    '''Rounded tile: small coloured dot + uppercase title, big value under it.'''

    def __init__(self, title, *, dot = None, small = False, parent = None):
        super().__init__(parent)
        self.setObjectName('Tile')
        col = QVBoxLayout(self)
        col.setContentsMargins(14, 11, 14, 12)
        col.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(6)
        if dot:
            mark = QLabel()
            mark.setFixedSize(8, 8)
            mark.setStyleSheet(f'background-color: {dot}; border-radius: 4px;')
            head.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
        label = QLabel(title.upper())
        label.setObjectName('StatTitle')
        font = label.font()
        font.setLetterSpacing(font.SpacingType.PercentageSpacing, 108)
        label.setFont(font)
        head.addWidget(label)
        head.addStretch()
        col.addLayout(head)
        self.value = QLabel('—')
        self.value.setObjectName('StatValueSmall' if small else 'StatValue')
        # Word-wrap keeps a long readout from inflating the tile past the viewport.
        self.value.setWordWrap(True)
        col.addWidget(self.value)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._num = None
        self._fmt = str
        self._count = SmoothAnimation(self)
        self._count.setDuration(ANIM_COUNT)
        self._count.setEasingCurve(EASE_FADE)
        self._count.valueChanged.connect(lambda v: self.value.setText(self._fmt(v)))

    def animate_to(self, number, fmt = None):
        '''Count the shown number up (or down) to ``number``, formatted with ``fmt``.
        The first value counts up from 0; hidden tiles just jump to the value.'''
        self._fmt = fmt or (lambda v: str(int(round(v))))
        start = 0.0 if self._num is None else float(self._num)
        self._num = float(number)
        self._count.stop()
        if not self.isVisible() or start == self._num:
            self.value.setText(self._fmt(self._num))
            return
        self._count.setStartValue(start)
        self._count.setEndValue(self._num)
        self._count.start()

    def setText(self, text):
        self._count.stop()
        self.value.setText(text)

    def text(self):
        return self.value.text()

    def setStyleSheet(self, css):
        # Callers colour the value (e.g. the state); the tile itself keeps the theme.
        self.value.setStyleSheet(css)


def set_state_pill(label, text, color):
    '''Pill label with a tinted background in ``color`` ("● FARMING").'''
    c = QColor(color)
    label.setText(f'●  {text}')
    label.setStyleSheet(f'color: {color}; background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.14); '
                        f'border: 1px solid rgba({c.red()}, {c.green()}, {c.blue()}, 0.28); border-radius: 12px; padding: 4px 12px;')


def state_pill(text = 'IDLE', color = None, parent = None):
    label = QLabel(parent)
    label.setObjectName('StatePill')
    set_state_pill(label, text, color or TOKENS['text_muted'])
    return label


class Pulse(QObject):
    '''Slow "breathing" opacity loop on a widget (live state). start() / stop().'''

    def __init__(self, widget, *, low = 0.35, period = 2200):
        super().__init__(widget)
        self._widget = widget
        self._low = low
        self._effect = None
        # Linear phase 0→1 mapped through a cosine: one seamless wave per loop, with no
        # speed jump at the turning points or where the loop restarts.
        self._anim = SmoothAnimation(self)
        self._anim.setDuration(period)
        self._anim.setLoopCount(-1)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._apply)

    def _apply(self, phase):
        if self._effect is not None:
            wave = 0.5 + 0.5 * math.cos(2 * math.pi * float(phase))
            self._effect.setOpacity(self._low + (1.0 - self._low) * wave)

    def is_running(self):
        return self._anim.state() == SmoothAnimation.State.Running

    def start(self):
        if self.is_running():
            return
        self._effect = QGraphicsOpacityEffect(self._widget)
        self._widget.setGraphicsEffect(self._effect)
        self._anim.start()

    def stop(self):
        self._anim.stop()
        if self._effect is not None:
            self._widget.setGraphicsEffect(None)  # Qt deletes the effect
            self._effect = None


class PageTransition(QWidget):
    '''Cross-fade between two page snapshots, painted directly (no graphics effects, no
    relayout of the real pages): the old page fades out while the new one fades in and
    glides up a few pixels. Deletes itself and calls ``on_done`` at the end.'''

    LIFT = 14  # px the new page rises

    def __init__(self, parent, old_pixmap, new_pixmap, rect, on_done = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setGeometry(rect)
        self._old = old_pixmap
        self._new = new_pixmap
        self._t = 0.0
        self._on_done = on_done
        self._anim = SmoothAnimation(self)
        self._anim.setDuration(ANIM_MEDIUM)
        self._anim.setEasingCurve(EASE_FADE)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._step)
        self._anim.finished.connect(self.finish)

    def start(self):
        self.show()
        self.raise_()
        self._anim.start()

    def _step(self, value):
        self._t = float(value)
        self.update()

    def finish(self):
        self._anim.stop()
        if self._on_done is not None:
            (callback, self._on_done) = (self._on_done, None)
            callback()
        self.hide()
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(TOKENS['bg']))
        painter.setOpacity(1.0 - self._t)
        painter.drawPixmap(0, 0, self._old)
        painter.setOpacity(self._t)
        painter.drawPixmap(QPointF(0, self.LIFT * (1.0 - self._t)), self._new)
        painter.end()


class HoverGlow(QObject):
    '''Soft coloured glow that fades in while the mouse is over a button.'''

    def __init__(self, button, color, *, radius = 24):
        super().__init__(button)
        self._button = button
        self._radius = radius
        self._effect = QGraphicsDropShadowEffect(button)
        self._effect.setOffset(0, 3)
        self._effect.setColor(QColor(color))
        self._effect.setBlurRadius(0)
        button.setGraphicsEffect(self._effect)
        self._anim = SmoothAnimation(self)
        self._anim.setDuration(ANIM_MEDIUM)
        self._anim.setEasingCurve(EASE_FADE)
        self._anim.valueChanged.connect(self._effect.setBlurRadius)
        button.installEventFilter(self)

    def set_color(self, color):
        self._effect.setColor(QColor(color))

    def _to(self, value):
        self._anim.stop()
        self._anim.setStartValue(self._effect.blurRadius())
        self._anim.setEndValue(float(value))
        self._anim.start()

    def eventFilter(self, obj, event):
        if obj is self._button:
            kind = event.type()
            if kind == QEvent.Type.Enter and self._button.isEnabled():
                self._to(self._radius)
            elif kind in (QEvent.Type.Leave, QEvent.Type.Hide, QEvent.Type.EnabledChange):
                self._to(0)
        return False



class ToggleSwitch(QCheckBox):
    
    def __init__(self, text = '', *, parent = None, danger = False, under_development = False):
        super().__init__(text, parent)
        self.setObjectName('ToggleSwitch')
        self._danger = danger
        self._under_development = under_development
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 0.0 = off, 1.0 = on; animated between the two so the knob slides.
        self._pos = 0.0
        self._anim = SmoothAnimation(self)
        self._anim.setDuration(LIQUID_DURATION - 80)
        self._anim.setEasingCurve(EASE_MOVE)
        self._anim.valueChanged.connect(self._set_pos)
        self.toggled.connect(self._animate)
        if under_development:
            self.setChecked(False)
            return None


    TRACK_W = 42
    TRACK_H = 24

    def _set_pos(self, value):
        self._pos = float(value)
        self.update()

    def _animate(self, checked):
        target = 1.0 if checked and not self._under_development else 0.0
        self._anim.stop()
        if not self.isVisible():
            # Restored choices at start-up: no animation, just the final state.
            self._set_pos(target)
            return
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        (track_w, track_h) = (self.TRACK_W, self.TRACK_H)
        # Without a label the switch sits at the right edge of its box (setting rows).
        x0 = 0 if self.text() else self.width() - track_w
        y0 = (self.height() - track_h) / 2
        enabled = self.isEnabled() and not self._under_development
        t = self._pos if enabled else 0.0
        if self._anim.state() != SmoothAnimation.State.Running:
            t = 1.0 if (self.isChecked() and enabled) else 0.0  # always end on the real state
        off = TOKENS['toggle_off'] if enabled else TOKENS['toggle_off_disabled']
        on_top = TOKENS['danger'] if self._danger else TOKENS['primary']
        on_bottom = TOKENS['danger'] if self._danger else TOKENS['primary_2']
        track = QRectF(x0, y0, track_w, track_h)
        # Glass track: vertical fill (lighter on top), hairline rim, bright top highlight.
        grad = QLinearGradient(0, y0, 0, y0 + track_h)
        grad.setColorAt(0, _mix(off, on_top, t))
        grad.setColorAt(1, _mix(off, on_bottom, t))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(grad)
        painter.drawRoundedRect(track.adjusted(0.5, 0.5, -0.5, -0.5), track_h / 2, track_h / 2)
        shine = QLinearGradient(0, y0, 0, y0 + track_h / 2)
        shine.setColorAt(0, QColor(255, 255, 255, 46))
        shine.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(shine)
        painter.drawRoundedRect(QRectF(x0 + 3, y0 + 1.5, track_w - 6, track_h / 2), track_h / 4, track_h / 4)
        # Liquid knob: stretches along the travel mid-way, round again at either end.
        knob_d = track_h - 4
        bulge = math.sin(math.pi * t) if self._anim.state() == SmoothAnimation.State.Running else 0.0
        stretch = 8.0 * bulge
        knob_x = x0 + 2 + (track_w - knob_d - 4 - stretch) * t
        knob_y = y0 + 2
        knob = QRectF(knob_x, knob_y, knob_d + stretch, knob_d)
        painter.setBrush(QColor(0, 0, 0, 55))
        painter.drawRoundedRect(knob.translated(0, 1.2), knob_d / 2, knob_d / 2)
        if enabled:
            body = QLinearGradient(0, knob_y, 0, knob_y + knob_d)
            body.setColorAt(0, QColor(255, 255, 255))
            body.setColorAt(1, QColor(234, 236, 242))
            painter.setBrush(body)
        else:
            painter.setBrush(QColor(TOKENS['text_faint']))
        painter.drawRoundedRect(knob, knob_d / 2, knob_d / 2)
        if self.text():
            painter.setPen(QColor(TOKENS['text'] if enabled else TOKENS['text_faint']))
            text_rect = QRectF(track_w + 12, 0, self.width() - track_w - 12, self.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())
        painter.end()

    
    def mousePressEvent(self, event):
        if self._under_development:
            from app.ui.qt.dialogs import show_under_development
            show_under_development(self.window())
            return None
        super().mousePressEvent(event)

    
    def sizeHint(self):
        if not self.text():
            return QSize(self.TRACK_W, 30)
        text_w = self.fontMetrics().horizontalAdvance(self.text()) + 8
        return QSize(self.TRACK_W + text_w + 12, 30)

    
    def hitButton(self, pos):
        return self.rect().contains(pos)



def _styled_button(text, role, parent = None):
    btn = QPushButton(text, parent)
    btn.setProperty('role', role)
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    return btn


def primary_button(text, *, parent = None):
    return _styled_button(text, 'primary', parent)


def danger_button(text, *, parent = None):
    return _styled_button(text, 'danger', parent)


def neutral_button(text, *, parent = None):
    return _styled_button(text, 'neutral', parent)


def chip_button(text, *, parent = None):
    return _styled_button(text, 'chip', parent)


def link_button(text, *, parent = None):
    '''Borderless blue text button ("Edit player list ›").'''
    btn = _styled_button(text, 'link', parent)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def hint_label(text, parent = None):
    '''Small grey explanatory text under a control.'''
    label = QLabel(text, parent)
    label.setObjectName('Hint')
    label.setWordWrap(True)
    return label


class Separator(QFrame):
    '''1 px inset line between rows of a grouped card.'''

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setObjectName('Separator')
        self.setFixedHeight(1)


def segment_button(text, *, parent = None, under_development = False):
    btn = _styled_button(text, 'segment', parent)
    if under_development:
        btn.setCheckable(False)
        btn.setProperty('underDevelopment', True)
    else:
        btn.setCheckable(True)
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    btn.setMinimumWidth(int(btn.sizeHint().width() * 1.05))
    return btn


class StepperButton(QPushButton):
    '''Compact up/down arrow for numeric steppers.'''
    
    def __init__(self, *, up, parent = None):
        super().__init__(parent)
        self._up = up
        self.setProperty('role', 'stepper')
        self.setFixedSize(24, 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style().unpolish(self)
        self.style().polish(self)

    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(TOKENS['text'] if self.isEnabled() else TOKENS['text_faint']))
        cx = self.width() / 2
        cy = self.height() / 2
        if self._up:
            points = [
                QPointF(cx, cy - 3),
                QPointF(cx - 4, cy + 2),
                QPointF(cx + 4, cy + 2)]
        else:
            points = [
                QPointF(cx, cy + 3),
                QPointF(cx - 4, cy - 2),
                QPointF(cx + 4, cy - 2)]
        painter.drawPolygon(QPolygonF(points))



class HelpButton(QPushButton):
    '''Compact ? button that opens a help popup when clicked.'''
    
    def __init__(self, on_click, *, parent = None):
        super().__init__('?', parent)
        self.setProperty('role', 'help')
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip('What does each option do?')
        self.style().unpolish(self)
        self.style().polish(self)
        self.clicked.connect(on_click)



class VisibilityToggleButton(QPushButton):
    '''Minimal line-art eye toggle for password fields.'''
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setProperty('role', 'icon')
        self.setCheckable(True)
        self.setFixedSize(34, 34)
        self.setToolTip('Show password')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style().unpolish(self)
        self.style().polish(self)
        self.toggled.connect((lambda _: self.update()))

    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(TOKENS['text'])
        pen = QPen(color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx = self.width() / 2
        cy = self.height() / 2
        painter.drawEllipse(QRectF(cx - 9, cy - 6, 18, 12))
        if self.isChecked():
            painter.drawLine(int(cx - 8), int(cy + 6), int(cx + 8), int(cy - 6))
            return None
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - 2.5, cy - 2.5, 5, 5))




def _paint_sidebar_glyph(painter, kind, size):
    s = size / 24.0
    if kind == 'run':
        painter.setBrush(painter.pen().color())
        painter.drawPolygon(QPolygonF([QPointF(7 * s, 5 * s), QPointF(19 * s, 12 * s), QPointF(7 * s, 19 * s)]))
    elif kind == 'settings':
        painter.drawEllipse(QPointF(12 * s, 12 * s), 3.2 * s, 3.2 * s)
        painter.drawEllipse(QPointF(12 * s, 12 * s), 8 * s, 8 * s)
        for (x1, y1, x2, y2) in ((12, 1.5, 12, 4), (12, 20, 12, 22.5), (1.5, 12, 4, 12), (20, 12, 22.5, 12)):
            painter.drawLine(QPointF(x1 * s, y1 * s), QPointF(x2 * s, y2 * s))
    elif kind == 'players':
        painter.drawEllipse(QPointF(9 * s, 8 * s), 3.5 * s, 3.5 * s)
        path = QPainterPath()
        path.moveTo(2.5 * s, 20 * s)
        path.cubicTo(2.5 * s, 14 * s, 15.5 * s, 14 * s, 15.5 * s, 20 * s)
        painter.drawPath(path)
        painter.drawArc(int(14 * s), int(4.5 * s), int(7 * s), int(7 * s), -90 * 16, 180 * 16)
        painter.drawLine(QPointF(18 * s, 15 * s), QPointF(21.5 * s, 20 * s))
    elif kind == 'history':
        painter.drawEllipse(QPointF(12 * s, 12 * s), 8.5 * s, 8.5 * s)
        painter.drawLine(QPointF(12 * s, 7 * s), QPointF(12 * s, 12 * s))
        painter.drawLine(QPointF(12 * s, 12 * s), QPointF(15.5 * s, 14.5 * s))
    elif kind == 'logs':
        painter.drawRoundedRect(QRectF(5 * s, 3 * s, 14 * s, 18 * s), 2.5 * s, 2.5 * s)
        for y in (8.5, 12.5, 16.5):
            painter.drawLine(QPointF(8.5 * s, y * s), QPointF(15.5 * s, y * s))


def sidebar_icon(kind, size = 18):
    """Line-art sidebar glyph (run / settings / players / logs): grey normally, blue when
    the item is selected (QIcon.Selected)."""
    icon = QIcon()
    for (mode, color) in ((QIcon.Mode.Normal, TOKENS['text_muted']), (QIcon.Mode.Selected, TOKENS['primary_hov']), (QIcon.Mode.Active, TOKENS['text'])):
        pix = QPixmap(size * 2, size * 2)
        pix.setDevicePixelRatio(2)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _paint_sidebar_glyph(painter, kind, size)
        painter.end()
        icon.addPixmap(pix, mode)
    return icon
