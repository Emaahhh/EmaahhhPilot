'''History page — every finished run: totals, loot per hour chart, yield per army.'''
from __future__ import annotations
from datetime import datetime
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from app.ui.qt import help_text
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QMessageBox, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import Card, SectionTitle, StatTile, hint_label, neutral_button, page_header
from app.utils.history_store import by_army, clear_history, load_history, loot_per_hour_series, summarize


def fmt_amount(value):
    value = float(value)
    if value >= 1_000_000:
        return f'{value / 1_000_000:.1f}M'
    if value >= 10_000:
        return f'{value / 1000:.0f}k'
    return f'{value:,.0f}'


def fmt_duration(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 3600}h {seconds % 3600 // 60:02d}m' if seconds >= 3600 else f'{seconds // 60}m {seconds % 60:02d}s'


class LootChart(QWidget):
    '''Stacked bars: gold + elixir per hour for each session (oldest → newest).'''

    def __init__(self, parent = None):
        super().__init__(parent)
        self._series = []
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_series(self, series):
        self._series = list(series)
        self.update()

    def sizeHint(self):
        return QSize(420, 190)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        (w, h) = (self.width(), self.height())
        (left, right, top, bottom) = (44, 6, 10, 24)
        plot = QRectF(left, top, max(1, w - left - right), max(1, h - top - bottom))
        muted = QColor(TOKENS['text_muted'])
        if not self._series:
            p.setPen(muted)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'No sessions yet — finish a run to see the trend.')
            return
        peak = max(g + e for (_l, g, e) in self._series) or 1.0
        top_val = peak * 1.1
        font = QFont(self.font())
        font.setPointSizeF(max(7.5, font.pointSizeF() - 1.5))
        p.setFont(font)
        for frac in (0.0, 0.5, 1.0):
            y = plot.bottom() - plot.height() * frac
            p.setPen(QPen(QColor(255, 255, 255, 22), 1))
            p.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))
            p.setPen(muted)
            p.drawText(QRectF(0, y - 8, left - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt_amount(top_val * frac))
        n = len(self._series)
        slot = plot.width() / n
        bar_w = max(3.0, min(34.0, slot * 0.62))
        step = max(1, int(round(34 / max(slot, 1))))
        for (i, (label, gold, elixir)) in enumerate(self._series):
            cx = plot.left() + slot * (i + 0.5)
            gh = plot.height() * gold / top_val
            eh = plot.height() * elixir / top_val
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(TOKENS['gold']))
            p.drawRoundedRect(QRectF(cx - bar_w / 2, plot.bottom() - gh, bar_w, gh), 3, 3)
            p.setBrush(QColor(TOKENS['elixir']))
            p.drawRoundedRect(QRectF(cx - bar_w / 2, plot.bottom() - gh - eh, bar_w, eh), 3, 3)
            if i % step == 0 or i == n - 1:
                p.setPen(muted)
                p.drawText(QRectF(cx - 22, plot.bottom() + 4, 44, 16), Qt.AlignmentFlag.AlignCenter, label)
        p.end()


class HistoryPage(QWidget):

    RECENT_ROWS = 12

    def __init__(self, controller = None, parent = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'] - 8, 0)
        outer.setSpacing(SPACING['md'])
        clear_btn = neutral_button('Clear history')
        clear_btn.clicked.connect(self._on_clear)
        clear_btn.setToolTip(help_text.HISTORY['clear'])
        outer.addLayout(page_header('History', 'Every finished run, saved on this PC.', clear_btn))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 2, 8, SPACING['lg'])
        layout.setSpacing(SPACING['md'])
        # Totals
        self._summary = hint_label('')
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)
        self._t_gold = StatTile('Total gold', dot = TOKENS['gold'])
        self._t_elixir = StatTile('Total elixir', dot = TOKENS['elixir'])
        self._t_time = StatTile('Time played')
        self._t_sessions = StatTile('Sessions')
        self._t_attacks = StatTile('Attacks')
        self._t_att_hour = StatTile('Attacks / hour')
        for group in ((self._t_gold, self._t_elixir, self._t_time), (self._t_sessions, self._t_attacks, self._t_att_hour)):
            tiles = QHBoxLayout()
            tiles.setSpacing(10)
            for tile in group:
                tiles.addWidget(tile, 1)
            layout.addLayout(tiles)
        # Chart
        chart_card = Card()
        chart_card.card_layout.addWidget(SectionTitle('Earnings per hour, run by run'))
        self._chart = LootChart()
        chart_card.card_layout.addWidget(self._chart)
        legend = QLabel(f'<span style="color:{TOKENS["gold"]}">●</span> gold &nbsp;&nbsp; <span style="color:{TOKENS["elixir"]}">●</span> elixir')
        legend.setObjectName('Hint')
        chart_card.card_layout.addWidget(legend)
        layout.addWidget(chart_card)
        # Army yield
        self._army_card = Card()
        self._army_card.card_layout.addWidget(SectionTitle('Which army earns more'))
        self._army_grid = QGridLayout()
        self._army_grid.setHorizontalSpacing(SPACING['lg'])
        self._army_grid.setVerticalSpacing(8)
        self._army_card.card_layout.addLayout(self._army_grid)
        self._army_hint = hint_label('')
        self._army_card.card_layout.addWidget(self._army_hint)
        layout.addWidget(self._army_card)
        # Recent sessions
        self._recent_card = Card()
        self._recent_card.card_layout.addWidget(SectionTitle(f'Last {self.RECENT_ROWS} runs, newest first'))
        self._recent_grid = QGridLayout()
        self._recent_grid.setHorizontalSpacing(SPACING['lg'])
        self._recent_grid.setVerticalSpacing(8)
        self._recent_card.card_layout.addLayout(self._recent_grid)
        layout.addWidget(self._recent_card)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        if controller is not None:
            controller.historyChanged.connect(self.reload)
        self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        self.reload()

    # ---- data ----
    @staticmethod
    def _clear_grid(grid):
        while grid.count():
            item = grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    @staticmethod
    def _cell(text, *, header = False, align = Qt.AlignmentFlag.AlignLeft, color = None, bold = False):
        label = QLabel(text.upper() if header else text)
        label.setObjectName('StatTitle' if header else 'Hint')
        if not header:
            weight = 'font-weight: 600;' if bold else ''
            label.setStyleSheet(f"color: {color or TOKENS['text']}; font-size: 13px; {weight}")
        label.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _fill_table(self, grid, headers, rows, colors = None, empty = 'Nothing here yet.'):
        '''``colors`` maps a column index to a colour; the first column is shown in bold.'''
        self._clear_grid(grid)
        colors = colors or {}
        right = Qt.AlignmentFlag.AlignRight
        if not rows:
            grid.addWidget(self._cell(empty), 0, 0, 1, max(1, len(headers)))
            return
        for (c, head) in enumerate(headers):
            grid.addWidget(self._cell(head, header = True, align = Qt.AlignmentFlag.AlignLeft if c == 0 else right), 0, c)
            grid.setColumnStretch(c, 2 if c == 0 else 1)
        for (r, row) in enumerate(rows, start = 1):
            for (c, text) in enumerate(row):
                grid.addWidget(self._cell(text, align = Qt.AlignmentFlag.AlignLeft if c == 0 else right,
                                          color = colors.get(c) if text != '—' else TOKENS['text_muted'], bold = c == 0), r, c)

    @staticmethod
    def _when(iso):
        '''"Today 14:32", "Yesterday 09:10" or "12 Nov 18:05".'''
        try:
            dt = datetime.fromisoformat(iso)
        except ValueError:
            return str(iso)
        days = (datetime.now().date() - dt.date()).days
        if days == 0:
            return dt.strftime('Today %H:%M')
        if days == 1:
            return dt.strftime('Yesterday %H:%M')
        return dt.strftime('%d %b %H:%M')

    def reload(self):
        sessions = load_history()
        total = summarize(sessions)
        self._t_sessions.setText(str(total['sessions']))
        self._t_attacks.setText(f"{total['attacks']:,}")
        self._t_gold.setText(fmt_amount(total['gold']) if sessions else '—')
        self._t_elixir.setText(fmt_amount(total['elixir']) if sessions else '—')
        self._t_time.setText(fmt_duration(sum(s['duration_s'] for s in sessions)) if sessions else '—')
        self._t_att_hour.setText(f"{total['attacks_per_hour']:.0f}" if total['attacks_per_hour'] else '—')
        if sessions:
            last = sessions[-1]
            what = f"{last['attacks']} attacks" + (f", {fmt_amount(last['gold'])} gold, {fmt_amount(last['elixir'])} elixir" if last['village'] == 'home' else f", {last['walls']} walls")
            self._summary.setText(f"Last run — {self._when(last['ended'])}: {what} in {fmt_duration(last['duration_s'])}.")
        else:
            self._summary.setText('No runs yet. Start the bot and every finished run will appear here.')
        self._chart.set_series(loot_per_hour_series(sessions))
        armies = by_army(sessions)
        self._fill_table(self._army_grid, ('Army', 'Attacks', 'Gold / att.', 'Elixir / att.', 'Att. / hour', 'Loot / hour'),
                         [(f"{a['army']}{' (BB)' if a['village'] == 'builder' else ''}", f"{a['attacks']:,}",
                           fmt_amount(a['gold_per_attack']) if a['village'] == 'home' else '—',
                           fmt_amount(a['elixir_per_attack']) if a['village'] == 'home' else '—',
                           f"{a['attacks_per_hour']:.0f}",
                           fmt_amount(a['loot_per_hour']) if a['village'] == 'home' else '—') for a in armies],
                         colors = {2: TOKENS['gold'], 3: TOKENS['elixir']}, empty = 'No army data yet — finish a run first.')
        if len(armies) >= 2 and armies[0]['loot_per_hour'] > 0:
            self._army_hint.setText(f"Best loot per hour so far: {armies[0]['army']}. Runs under a minute are ignored by the chart.")
        else:
            self._army_hint.setText('Run more than one army to compare them here.' if sessions else 'Nothing to compare yet.')
        recent = list(reversed(sessions[-self.RECENT_ROWS:]))
        rows = []
        for s in recent:
            when = self._when(s['ended'])
            home = s['village'] == 'home'
            rows.append((when, s['army'], fmt_duration(s['duration_s']), f"{s['attacks']}",
                         fmt_amount(s['gold']) if home else '—', fmt_amount(s['elixir']) if home else '—', f"{s['walls']}"))
        self._fill_table(self._recent_grid, ('When', 'Army', 'Duration', 'Attacks', 'Gold', 'Elixir', 'Walls'), rows,
                         colors = {4: TOKENS['gold'], 5: TOKENS['elixir']}, empty = 'No sessions yet.')

    def _on_clear(self):
        reply = QMessageBox.question(self.window(), 'Clear history', 'Delete every saved session? This cannot be undone.',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            clear_history()
            self.reload()
