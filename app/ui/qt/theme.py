'''EmaahhhPilot theme: "liquid glass" QSS for the PySide6 UI, in the logo's navy & cream.

Design: a deep navy backdrop with soft colour glows (widgets.Backdrop) seen through
translucent glass panels. Every panel has a faint white fill, a hairline border and a
brighter top edge (the light catching the glass). No 3D lips: depth comes from
translucency and highlights. One CREAM accent (navy text on it) for the main action and
the switches; the selected segment is a clear glass lens. Resource colours (gold /
elixir / dark elixir) only where loot is shown, green / amber / red only for live state
and Stop. Every colour lives in TOKENS.

Popups (menus, combo lists, dialogs, tooltips) stay opaque: Windows cannot show what is
behind a separate popup window.
'''
from __future__ import annotations
import os
import tempfile
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

TOKENS = {
    # Backdrop (painted by widgets.Backdrop under every page)
    'bg': '#071023',
    'bg_2': '#0A1631',
    'glow_cream': '#FBF1DC',
    'glow_blue': '#2F5BD8',
    'glow_violet': '#6B4FD8',
    # Glass
    'glass': 'rgba(255, 255, 255, 0.045)',        # panel fill (bottom of its gradient)
    'glass_top': 'rgba(255, 255, 255, 0.085)',    # panel fill (top)
    'glass_border': 'rgba(255, 255, 255, 0.09)',  # hairline
    'glass_edge': 'rgba(255, 255, 255, 0.22)',    # brighter top edge (specular highlight)
    'glass_field': 'rgba(255, 255, 255, 0.06)',   # inputs, tiles
    'glass_hover': 'rgba(255, 255, 255, 0.10)',
    'glass_press': 'rgba(255, 255, 255, 0.15)',
    'sunken': 'rgba(0, 0, 0, 0.22)',              # wells: segment tracks, the log
    'popup': '#0F1B36',                           # opaque popups / dialogs
    # Opaque fallbacks (palette, chevrons)
    'surface': '#0E1A33',
    'surface_hi': '#142343',
    'surface_top': '#1E3159',
    'border': '#1A2A4A',
    # Text
    'text': '#FBF3E3',         # cream
    'text_muted': '#BCAE90',   # warm beige
    'text_faint': '#66708C',   # disabled / de-emphasized
    # Accent
    'primary': '#FBF1DC',      # cream
    'primary_2': '#E8D4AA',    # darker cream
    'primary_hov': '#FFF8EA',
    'primary_tint': 'rgba(251, 241, 220, 0.12)',
    'on_primary': '#0A1630',   # navy text on cream
    'link': '#E8D4AA',
    # State
    'danger': '#F06A6A',
    'go': '#4FD47F',           # Start button green
    'success': '#6FD6A2',
    'warning': '#F2BE5C',      # holding / idling amber
    'gold': '#FFC83D',
    'elixir': '#E36BFF',
    'dark_elixir': '#9D8CFF',
    # Switch (QColor hex with alpha: #AARRGGBB)
    'toggle_off': '#2EFFFFFF',
    'toggle_off_disabled': '#12FFFFFF',
    'knob': '#FFFFFF',
    'log_text': '#E9DFCB' }
SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 14,
    'lg': 24,
    'xl': 32 }
RADIUS = 22          # glass panels
BUTTON_RADIUS = 14
SIDEBAR_WIDTH = 220
WINDOW_DEFAULT = (1040, 740)
WINDOW_MIN = (820, 580)

_SANS_CANDIDATES = ('Segoe UI Variable Text', 'Segoe UI Variable Display', 'Inter', 'SF Pro Text', 'Segoe UI')
_MONO_CANDIDATES = ('Cascadia Mono', 'Cascadia Code', 'SF Mono', 'Consolas')
SANS_FONT = 'Segoe UI'
MONO_FONT = 'Consolas'


def _vgrad(top, bottom):
    return f'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:1 {bottom})'


def _resolve_fonts():
    global SANS_FONT, MONO_FONT
    try:
        families = set(QFontDatabase.families())
    except Exception:
        return
    for name in _SANS_CANDIDATES:
        if name in families:
            SANS_FONT = name
            break
    for name in _MONO_CANDIDATES:
        if name in families:
            MONO_FONT = name
            break


def _arrow_images():
    '''Small chevron PNGs for spin boxes and combo boxes (Qt QSS cannot draw them once the
    sub-controls are restyled). Written to the temp folder; {} before a QApplication exists.'''
    if QApplication.instance() is None:
        return {}
    folder = os.path.join(tempfile.gettempdir(), 'emaahhhpilot_ui')
    os.makedirs(folder, exist_ok = True)
    paths = {}
    for (name, up, color) in (('up', True, TOKENS['text_muted']), ('down', False, TOKENS['text_muted']), ('down_off', False, TOKENS['text_faint']), ('up_off', True, TOKENS['text_faint'])):
        pix = QPixmap(20, 12)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        tip = (10, 2) if up else (10, 10)
        base_y = 10 if up else 2
        painter.drawPolygon(QPolygonF([QPointF(*tip), QPointF(4, base_y), QPointF(16, base_y)]))
        painter.end()
        path = os.path.join(folder, f'arrow_{name}.png')
        pix.save(path)
        paths[name] = path.replace(os.sep, '/')
    # Tick for plain check boxes (navy on the cream box).
    tick = QPixmap(18, 18)
    tick.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tick)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(TOKENS['on_primary']), 2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygonF([QPointF(4.5, 9.5), QPointF(7.8, 12.8), QPointF(13.5, 5.5)]))
    painter.end()
    path = os.path.join(folder, 'check.png')
    tick.save(path)
    paths['check'] = path.replace(os.sep, '/')
    return paths


def _arrow_rules(t):
    arrows = _arrow_images()
    if not arrows:
        return ''
    return f'''
QSpinBox, QDoubleSpinBox {{
    padding-left: 6px;
    padding-right: 22px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border: none;
    background: transparent;
    margin: 3px 3px 0 0;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border: none;
    background: transparent;
    margin: 0 3px 3px 0;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {t['glass_hover']};
    border-radius: 5px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({arrows['up']});
    width: 10px;
    height: 6px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({arrows['down']});
    width: 10px;
    height: 6px;
}}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{
    image: url({arrows['up_off']});
}}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
    image: url({arrows['down_off']});
}}
QComboBox {{
    padding-right: 30px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: none;
}}
QComboBox::down-arrow {{
    image: url({arrows['down']});
    width: 10px;
    height: 6px;
}}
QCheckBox::indicator:checked {{
    image: url({arrows['check']});
}}
QCheckBox#ToggleSwitch::indicator, QCheckBox#ToggleSwitch::indicator:checked {{
    image: none;
}}
'''


def build_stylesheet():
    t = TOKENS
    br = BUTTON_RADIUS
    tile_r = RADIUS - 6
    seg_r = RADIUS - 6
    seg_btn_r = seg_r - 3
    panel = _vgrad(t['glass_top'], t['glass'])
    cream = _vgrad('rgba(253, 246, 230, 0.96)', 'rgba(236, 220, 186, 0.86)')
    cream_hov = _vgrad('rgba(255, 252, 242, 1.0)', 'rgba(244, 231, 203, 0.93)')
    cream_press = _vgrad('rgba(236, 222, 192, 0.92)', 'rgba(222, 202, 162, 0.86)')
    red = _vgrad('rgba(250, 124, 124, 0.88)', 'rgba(222, 80, 90, 0.82)')
    red_hov = _vgrad('rgba(255, 142, 142, 0.94)', 'rgba(234, 96, 106, 0.88)')
    red_press = _vgrad('rgba(226, 98, 102, 0.92)', 'rgba(196, 64, 76, 0.88)')
    green = _vgrad('rgba(118, 228, 152, 0.92)', 'rgba(40, 168, 92, 0.86)')
    green_hov = _vgrad('rgba(140, 240, 170, 0.97)', 'rgba(52, 184, 104, 0.92)')
    green_press = _vgrad('rgba(92, 200, 128, 0.94)', 'rgba(30, 146, 78, 0.90)')
    lens = _vgrad('rgba(255, 255, 255, 0.24)', 'rgba(255, 255, 255, 0.10)')
    return f'''
/* Everything is see-through unless it is a glass panel: the backdrop shows behind. */
QWidget {{
    background-color: transparent;
    color: {t['text']};
    font-family: '{SANS_FONT}';
    font-size: 13px;
}}
QMainWindow {{
    background-color: {t['bg']};
}}
QLabel {{
    padding: 0;
    margin: 0;
}}
QToolTip {{
    background-color: {t['popup']};
    color: {t['text']};
    border: 1px solid {t['glass_border']};
    border-radius: 8px;
    padding: 6px 10px;
}}

/* ---- Glass panels ---- */
QFrame#Card {{
    background-color: {panel};
    border: 1px solid {t['glass_border']};
    border-top-color: {t['glass_edge']};
    border-radius: {RADIUS}px;
}}
QFrame#HeroCard {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(251, 241, 220, 0.11), stop:0.55 rgba(255, 255, 255, 0.05), stop:1 rgba(120, 140, 255, 0.07));
    border: 1px solid {t['glass_border']};
    border-top-color: {t['glass_edge']};
    border-radius: {RADIUS}px;
}}
QFrame#Tile {{
    background-color: {t['glass_field']};
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-top-color: rgba(255, 255, 255, 0.13);
    border-radius: {tile_r}px;
}}
QFrame#Separator {{
    background-color: rgba(255, 255, 255, 0.07);
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* ---- Text styles ---- */
QLabel#PageTitle {{
    font-size: 26px;
    font-weight: 700;
    color: {t['text']};
}}
QLabel#PageSubtitle {{
    font-size: 13px;
    color: {t['text_muted']};
}}
QLabel#SectionTitle {{
    color: {t['text_muted']};
    font-weight: 600;
    font-size: 11px;
}}
QLabel#SectionTitle:disabled, QLabel#RowTitle:disabled, QLabel#DurationUnit:disabled {{
    color: {t['text_faint']};
}}
QLabel#RowTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {t['text']};
}}
QLabel#RowSubtitle, QLabel#Hint {{
    font-size: 12px;
    color: {t['text_muted']};
}}
QLabel#RowSubtitle:disabled {{
    color: {t['text_faint']};
}}
QLabel#StatValue {{
    font-size: 20px;
    font-weight: 700;
    color: {t['text']};
}}
QLabel#StatValueSmall {{
    font-size: 15px;
    font-weight: 600;
    color: {t['text']};
}}
QLabel#StatTitle {{
    color: {t['text_muted']};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#Brand {{
    font-size: 16px;
    font-weight: 700;
}}
QLabel#BrandSub {{
    color: {t['text_faint']};
    font-size: 11px;
}}
QLabel#StatePill {{
    border-radius: 11px;
    padding: 3px 11px;
    font-size: 11px;
    font-weight: 700;
}}

/* ---- Buttons: glass, no 3D lip ---- */
QPushButton {{
    border: 1px solid {t['glass_border']};
    border-top-color: {t['glass_edge']};
    border-radius: {br}px;
    padding: 7px 16px;
    min-height: 26px;
    font-weight: 600;
    background-color: {t['glass_field']};
}}
QPushButton:hover {{
    background-color: {t['glass_hover']};
}}
QPushButton:pressed {{
    background-color: {t['glass_press']};
}}
QPushButton:disabled {{
    color: {t['text_faint']};
    background-color: rgba(255, 255, 255, 0.025);
    border-color: rgba(255, 255, 255, 0.05);
}}
QPushButton[role="primary"] {{
    background-color: {cream};
    color: {t['on_primary']};
    border: 1px solid rgba(255, 255, 255, 0.55);
    border-top-color: rgba(255, 255, 255, 0.95);
}}
QPushButton[role="primary"]:hover {{
    background-color: {cream_hov};
}}
QPushButton[role="primary"]:pressed {{
    background-color: {cream_press};
}}
QPushButton[role="primary"]:disabled {{
    background-color: rgba(251, 241, 220, 0.10);
    color: {t['text_faint']};
    border-color: rgba(255, 255, 255, 0.06);
}}
QPushButton[role="danger"] {{
    background-color: {red};
    color: #FFFFFF;
    border: 1px solid rgba(255, 190, 190, 0.40);
    border-top-color: rgba(255, 220, 220, 0.75);
}}
QPushButton[role="danger"]:hover {{
    background-color: {red_hov};
}}
QPushButton[role="danger"]:disabled {{
    background-color: rgba(240, 106, 106, 0.12);
    color: {t['text_faint']};
    border-color: rgba(255, 255, 255, 0.05);
}}
QPushButton#RunAction {{
    border-radius: 20px;
    min-height: 40px;
    max-height: 40px;
    padding: 0 26px;
    font-size: 14px;
    font-weight: 700;
}}
/* Start = green glass, Stop = red glass. */
QPushButton#RunAction[role="primary"] {{
    background-color: {green};
    color: #FFFFFF;
    border: 1px solid rgba(190, 255, 205, 0.40);
    border-top-color: rgba(225, 255, 232, 0.85);
}}
QPushButton#RunAction[role="primary"]:hover {{
    background-color: {green_hov};
}}
QPushButton#RunAction[role="primary"]:pressed {{
    background-color: {green_press};
}}
QPushButton#RunAction[role="primary"]:disabled {{
    background-color: rgba(79, 212, 127, 0.12);
    color: {t['text_faint']};
    border-color: rgba(255, 255, 255, 0.05);
}}
QPushButton#RunAction[role="danger"]:pressed {{
    background-color: {red_press};
}}
QPushButton[role="link"] {{
    background-color: transparent;
    border: none;
    color: {t['link']};
    padding: 4px 6px;
}}
QPushButton[role="link"]:hover {{
    color: {t['text']};
    background-color: transparent;
}}
QPushButton[role="link"]:disabled {{
    color: {t['text_faint']};
    background-color: transparent;
}}
QPushButton[role="chip"] {{
    color: {t['text_muted']};
    padding: 3px 12px;
    min-height: 22px;
    border-radius: 13px;
    font-size: 12px;
}}
QPushButton[role="chip"]:hover {{
    color: {t['text']};
}}

/* Segmented control: a sunken well with a sliding clear-glass lens (QFrame#SegIndicator). */
QFrame#Segmented {{
    background-color: {t['sunken']};
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-bottom-color: rgba(255, 255, 255, 0.10);
    border-radius: {seg_r}px;
}}
QFrame#Segmented QFrame#SegIndicator {{
    background-color: {lens};
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-top-color: rgba(255, 255, 255, 0.55);
    border-radius: {seg_btn_r}px;
}}
QPushButton[role="segment"] {{
    background-color: transparent;
    border: none;
    color: {t['text_muted']};
    border-radius: {seg_btn_r}px;
    padding: 6px 16px;
    min-height: 24px;
}}
QPushButton[role="segment"]:hover:!checked {{
    color: {t['text']};
    background-color: rgba(255, 255, 255, 0.04);
}}
QPushButton[role="segment"]:checked, QPushButton[role="segment"]:checked:hover {{
    background-color: transparent;
    color: #FFFFFF;
}}
QPushButton[role="segment"][underDevelopment="true"] {{
    background-color: transparent;
    color: {t['text_faint']};
}}

QPushButton[role="stepper"] {{
    padding: 0;
    min-height: 14px;
    max-height: 14px;
    min-width: 24px;
    max-width: 24px;
    border-radius: 5px;
}}
QPushButton[role="help"] {{
    background-color: transparent;
    color: {t['text_muted']};
    padding: 0;
    min-height: 18px;
    min-width: 18px;
    max-height: 18px;
    max-width: 18px;
    border-radius: 9px;
    border: 1px solid {t['text_faint']};
    font-size: 11px;
    font-weight: bold;
}}
QPushButton[role="help"]:hover {{
    color: {t['text']};
    border-color: {t['text']};
}}
QPushButton[role="icon"] {{
    padding: 0;
    min-height: 34px;
    min-width: 34px;
    max-height: 34px;
    max-width: 34px;
    border-radius: 10px;
}}

/* ---- Inputs ---- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background-color: {t['glass_field']};
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: {br}px;
    padding: 6px 10px;
    selection-background-color: rgba(251, 241, 220, 0.35);
    selection-color: #FFFFFF;
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    background-color: {t['glass_hover']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: rgba(251, 241, 220, 0.55);
}}
QComboBoxPrivateContainer {{
    background-color: {t['popup']};
    border: 1px solid {t['glass_border']};
    border-radius: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {t['popup']};
    border: none;
    padding: 4px;
    selection-background-color: {t['primary_tint']};
    selection-color: {t['text']};
    outline: none;
}}
QMenu {{
    background-color: {t['popup']};
    border: 1px solid {t['glass_border']};
    border-radius: 10px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {t['primary_tint']};
}}
QSpinBox#DurationSpin {{
    min-height: 32px;
    max-height: 32px;
    padding: 2px 6px;
    font-size: 15px;
    font-weight: 700;
}}
/* The duration box has its own stepper buttons beside it. Its built-in arrows are
   hidden HERE (zero width) instead of with setButtonSymbols(NoButtons): on Windows,
   NoButtons + a stylesheet collapses the inner text field to 1 px, so the minutes
   were set but never drawn (live repro: empty Duration box). */
QSpinBox#DurationSpin::up-button, QSpinBox#DurationSpin::down-button {{
    width: 0px;
    border: none;
}}
QSpinBox#DurationSpin::up-arrow, QSpinBox#DurationSpin::down-arrow {{
    width: 0px;
    height: 0px;
}}
QSpinBox:disabled, QDoubleSpinBox:disabled, QSpinBox#DurationSpin:disabled {{
    color: {t['text_faint']};
    background-color: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.05);
}}

/* ---- Sidebar: a tall glass pane ---- */
QWidget#SidebarPanel {{
    background-color: rgba(255, 255, 255, 0.03);
    border-right: 1px solid {t['glass_border']};
}}
QListWidget#Sidebar {{
    border: none;
    padding: 0;
    outline: none;
}}
QListWidget#Sidebar::item {{
    padding: 10px 12px;
    margin: 2px 0;
    border-radius: {br}px;
    color: {t['text_muted']};
    border: 1px solid transparent;
}}
QListWidget#Sidebar::item:selected {{
    background-color: {lens};
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-top-color: rgba(255, 255, 255, 0.40);
    color: #FFFFFF;
}}
QListWidget#Sidebar::item:hover:!selected {{
    background-color: rgba(255, 255, 255, 0.05);
    color: {t['text']};
}}
QWidget#SidebarPanel QFrame#SidebarStatus {{
    background-color: {t['glass_field']};
    border: 1px solid {t['glass_border']};
    border-top-color: rgba(255, 255, 255, 0.16);
    border-radius: {tile_r}px;
}}

/* ---- Lists, log ---- */
QListWidget#WindowList, QListWidget#WindowInfoList {{
    background-color: {t['sunken']};
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: {br}px;
    padding: 4px;
    outline: none;
}}
QListWidget#WindowList::item, QListWidget#WindowInfoList::item {{
    padding: 7px 8px;
    border-radius: {br - 4}px;
}}
QListWidget#WindowList::item:hover:!selected {{
    background-color: rgba(255, 255, 255, 0.05);
}}
QListWidget#WindowList::item:selected, QListWidget#WindowInfoList::item:selected {{
    background-color: {t['primary_tint']};
    color: {t['text']};
}}
QPlainTextEdit#LogView {{
    background-color: rgba(0, 0, 0, 0.30);
    border: 1px solid {t['glass_border']};
    border-top-color: rgba(255, 255, 255, 0.16);
    border-radius: {RADIUS}px;
    padding: 12px 14px;
    font-family: '{MONO_FONT}';
    font-size: 12px;
    color: {t['log_text']};
}}

/* ---- Chrome ---- */
QStatusBar {{
    background-color: rgba(0, 0, 0, 0.25);
    border-top: 1px solid {t['glass_border']};
    color: {t['text_muted']};
    font-size: 11px;
}}
QStatusBar::item {{
    border: none;
}}
QScrollArea {{
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.14);
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.24);
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}
QCheckBox {{
    color: {t['text']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid rgba(251, 241, 220, 0.45);
    background: {t['glass_field']};
}}
QCheckBox::indicator:hover {{
    border-color: {t['primary']};
}}
QCheckBox::indicator:checked {{
    background: {t['primary']};
    border-color: {t['primary']};
}}
QCheckBox#ToggleSwitch {{
    spacing: 8px;
}}
QCheckBox#ToggleSwitch::indicator {{
    width: 0;
    height: 0;
    border: none;
}}

/* ---- Dialogs: separate windows, so opaque ---- */
QMessageBox, QDialog {{
    background-color: {t['popup']};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}
QMessageBox QPushButton:default {{
    background-color: {cream};
    color: {t['on_primary']};
    border: 1px solid rgba(255, 255, 255, 0.55);
}}
''' + _arrow_rules(t)


def apply_theme(app):
    app.setStyle('Fusion')
    _resolve_fonts()
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(TOKENS['bg']))
    pal.setColor(QPalette.Base, QColor(TOKENS['surface_hi']))
    pal.setColor(QPalette.AlternateBase, QColor(TOKENS['surface']))
    pal.setColor(QPalette.Text, QColor(TOKENS['text']))
    pal.setColor(QPalette.WindowText, QColor(TOKENS['text']))
    pal.setColor(QPalette.Button, QColor(TOKENS['surface']))
    pal.setColor(QPalette.ButtonText, QColor(TOKENS['text']))
    pal.setColor(QPalette.ToolTipBase, QColor(TOKENS['popup']))
    pal.setColor(QPalette.ToolTipText, QColor(TOKENS['text']))
    pal.setColor(QPalette.Highlight, QColor(TOKENS['primary']))
    pal.setColor(QPalette.HighlightedText, QColor(TOKENS['on_primary']))
    app.setPalette(pal)
    app.setStyleSheet(build_stylesheet())


# Back-compat: some call sites import STYLESHEET directly.
STYLESHEET = build_stylesheet()
