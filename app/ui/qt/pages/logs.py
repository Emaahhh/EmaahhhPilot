'''Logs page — tail emaahhhpilot.log in the UI, with a level filter and a search box.'''
from __future__ import annotations
import os
import re
import subprocess
import sys
from collections import deque
from typing import Optional
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from app.ui.qt import help_text
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import neutral_button, page_header, segment_button, segmented
from app.utils.common import get_autoloot_log_path

_LEVEL_RE = re.compile(r' - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - ')
_STAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
_ISSUE_LEVELS = ('WARNING', 'ERROR', 'CRITICAL')


class _LogHighlighter(QSyntaxHighlighter):
    '''Faint timestamps, amber WARNING lines, red ERROR / CRITICAL lines.'''

    def __init__(self, document):
        super().__init__(document)
        self._stamp = QTextCharFormat()
        self._stamp.setForeground(QColor(TOKENS['text_faint']))
        self._warn = QTextCharFormat()
        self._warn.setForeground(QColor(TOKENS['warning']))
        self._err = QTextCharFormat()
        self._err.setForeground(QColor(TOKENS['danger']))

    def highlightBlock(self, text):
        # A wrapped continuation line keeps the colour of the line it belongs to.
        level = self.previousBlockState()
        match = _LEVEL_RE.search(text)
        if match:
            level = 2 if match.group(1) in ('ERROR', 'CRITICAL') else 1 if match.group(1) == 'WARNING' else 0
        elif _STAMP_RE.match(text):
            level = 0
        self.setCurrentBlockState(max(level, 0))
        if level == 1:
            self.setFormat(0, len(text), self._warn)
        elif level == 2:
            self.setFormat(0, len(text), self._err)
        stamp = _STAMP_RE.match(text)
        if stamp:
            self.setFormat(0, stamp.end(), self._stamp)


def parse_log_lines(lines, current_level = 'INFO'):
    '''[(level, text)] for log lines; a line without its own level (a traceback line)
    belongs to the previous record. Returns (records, level of the last record).'''
    records = []
    for line in lines:
        match = _LEVEL_RE.search(line)
        if match:
            current_level = match.group(1)
        records.append((current_level, line))
    return (records, current_level)


def filter_records(records, issues_only = False, query = ''):
    '''Records passing the level filter and containing ``query`` (case-insensitive).'''
    needle = (query or '').strip().lower()
    out = []
    for (level, line) in records:
        if issues_only and level not in _ISSUE_LEVELS:
            continue
        if needle and needle not in line.lower():
            continue
        out.append((level, line))
    return out


class LogsPage(QWidget):

    _MAX_RECORDS = 5000
    # On show only the end of the file is loaded: the view keeps 5000 lines anyway, and
    # re-reading a multi-MB log froze the UI (and appended it all again on every show).
    _SHOW_TAIL_BYTES = 512 * 1024

    def __init__(self, parent = None):
        super().__init__(parent)
        self._pos = 0
        self._skip_partial_line = False
        self._records = deque(maxlen = self._MAX_RECORDS)
        self._last_level = 'INFO'
        self._issues_only = False
        self._query = ''
        self._tail_timer = QTimer(self)
        self._tail_timer.setInterval(1000)
        self._tail_timer.timeout.connect(self._tail_log)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        layout.setSpacing(SPACING['md'])
        actions = QWidget()
        btn_row = QHBoxLayout(actions)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(SPACING['sm'])
        clear_btn = neutral_button('Clear view')
        clear_btn.clicked.connect(self._clear_view)
        btn_row.addWidget(clear_btn)
        open_btn = neutral_button('Open folder')
        open_btn.clicked.connect(self._open_in_explorer)
        btn_row.addWidget(open_btn)
        clear_btn.setToolTip(help_text.LOGS['clear'])
        open_btn.setToolTip(help_text.LOGS['open'])
        layout.addLayout(page_header('Logs', 'What the bot is doing, live.', actions))
        # Filters: level + search
        filters = QHBoxLayout()
        filters.setSpacing(SPACING['md'])
        self._level_group = QButtonGroup(self)
        self._level_group.setExclusive(True)
        buttons = []
        for (i, label) in enumerate(('All', 'Warnings and errors')):  # no "&": Qt reads it as a shortcut marker
            btn = segment_button(label)
            btn.setChecked(i == 0)
            self._level_group.addButton(btn, i)
            buttons.append(btn)
        self._level_group.idClicked.connect(self._on_level_changed)
        buttons[0].setToolTip(help_text.LOGS['all'])
        buttons[1].setToolTip(help_text.LOGS['issues'])
        filters.addWidget(segmented(buttons))
        self._search = QLineEdit()
        self._search.setPlaceholderText('Search the log…')
        self._search.setClearButtonEnabled(True)
        self._search.setToolTip(help_text.LOGS['search'])
        self._search.textChanged.connect(self._on_query_changed)
        filters.addWidget(self._search, 1)
        self._count = QLabel('')
        self._count.setObjectName('Hint')
        filters.addWidget(self._count)
        layout.addLayout(filters)
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(self._MAX_RECORDS)
        self._log_view.setObjectName('LogView')  # monospace + panel look come from the theme
        self._highlighter = _LogHighlighter(self._log_view.document())
        layout.addWidget(self._log_view, stretch = 1)

    # ---- filtering ----
    def _on_level_changed(self, button_id):
        self._issues_only = button_id == 1
        self._render()

    def _on_query_changed(self, text):
        self._query = text
        self._render()

    def _visible(self):
        return filter_records(self._records, self._issues_only, self._query)

    def _render(self):
        visible = self._visible()
        self._log_view.setUpdatesEnabled(False)
        self._log_view.setPlainText('\n'.join(line for (_lvl, line) in visible))
        self._log_view.moveCursor(QTextCursor.MoveOperation.End)
        self._log_view.setUpdatesEnabled(True)
        self._update_count(len(visible))

    def _update_count(self, shown):
        total = len(self._records)
        filtered = self._issues_only or bool(self._query.strip())
        self._count.setText(f'{shown} of {total} lines' if filtered else f'{total} lines')

    # ---- loading / tailing ----
    def showEvent(self, event):
        super().showEvent(event)
        self._records.clear()
        self._last_level = 'INFO'
        try:
            size = get_autoloot_log_path().stat().st_size
        except OSError:
            size = 0
        self._pos = max(0, size - self._SHOW_TAIL_BYTES)
        self._skip_partial_line = self._pos > 0
        self._log_view.clear()
        self._tail_log()
        self._tail_timer.start()

    def hideEvent(self, event):
        self._tail_timer.stop()
        super().hideEvent(event)

    def _tail_log(self):
        path = get_autoloot_log_path()
        try:
            path.parent.mkdir(parents = True, exist_ok = True)
            if not path.is_file():
                path.touch()
            if path.stat().st_size < self._pos:
                self._pos = 0  # the log rotated: follow the new file from its start
            with path.open('rb') as fh:
                fh.seek(self._pos)
                chunk = fh.read()
            # Only whole lines: a read in the middle of a write could split a UTF-8 character.
            cut = chunk.rfind(b'\n') + 1
            chunk = chunk[:cut]
            self._pos += cut
            if chunk and self._skip_partial_line:
                self._skip_partial_line = False
                chunk = chunk[chunk.find(b'\n') + 1:]
            if not chunk:
                return None
            lines = chunk.decode('utf-8', errors = 'replace').splitlines()
            (records, self._last_level) = parse_log_lines(lines, self._last_level)
            self._records.extend(records)
            shown = filter_records(records, self._issues_only, self._query)
            if shown:
                self._log_view.moveCursor(QTextCursor.MoveOperation.End)
                prefix = '\n' if self._log_view.document().characterCount() > 1 else ''
                self._log_view.insertPlainText(prefix + '\n'.join(line for (_lvl, line) in shown))
                self._log_view.moveCursor(QTextCursor.MoveOperation.End)
            self._update_count(len(self._visible()))
            return None
        except OSError:
            return None

    def _clear_view(self):
        self._records.clear()
        self._log_view.clear()
        self._update_count(0)

    def _open_in_explorer(self):
        path = get_autoloot_log_path()
        try:
            path.parent.mkdir(parents = True, exist_ok = True)
            if not path.is_file():
                path.touch()
            if sys.platform == 'win32':
                os.startfile(path.parent)
                return None
            if sys.platform == 'darwin':
                subprocess.run(['open', str(path.parent)], check = False)
                return None
            subprocess.run(['xdg-open', str(path.parent)], check = False)
            return None
        except OSError:
            return None
