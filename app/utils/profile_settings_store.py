'''Profile preferences (JSON) under LOCALAPPDATA\\EmaahhhPilot, next to ``player_list.json``.'''
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from app.utils.common import ensure_dir, get_user_app_data_dir
EARTHQUAKE_METHOD_CURVE = 'Curve Placement'
EARTHQUAKE_METHOD_RANDOM = 'Random Placement'
EARTHQUAKE_METHOD_OPTIONS = (EARTHQUAKE_METHOD_CURVE, EARTHQUAKE_METHOD_RANDOM)
SETTINGS_FILENAME = 'settings.json'
WALL_UPGRADE_THRESHOLD_M_DEFAULT = 3
WALL_UPGRADE_THRESHOLD_M_MAX = 20
# Builder Base walls: millions like the Home Village, but with one decimal (BB
# storages are small — 1.3M is a real setting).
BB_WALL_UPGRADE_THRESHOLD_M_DEFAULT = 0.0
BB_WALL_UPGRADE_THRESHOLD_M_MAX = 20.0
RESERVE_BUILDERS_DEFAULT = 1
RESERVE_BUILDERS_MAX = 5
SKIP_MIN_LOOT_K_DEFAULT = 600     # thousands of gold + elixir
SKIP_MIN_LOOT_K_MAX = 6000
HERO_KEYS = ('king', 'queen', 'warden', 'champion', 'prince')
HERO_MIN_FREE_DEFAULT = 2   # one builder stays free for walls (the reserve), one goes to the hero
HERO_MIN_FREE_MAX = 6
UPGRADE_ORDER_PRICIEST = 'priciest'
UPGRADE_ORDER_CHEAPEST = 'cheapest'
UPGRADE_ORDER_OPTIONS = (UPGRADE_ORDER_PRICIEST, UPGRADE_ORDER_CHEAPEST)

WALL_ORDER_LOWEST = 'lowest'    # cheapest payable wall level first (default)
WALL_ORDER_HIGHEST = 'highest'  # first payable row from the top of the list
WALL_ORDER_OPTIONS = (WALL_ORDER_LOWEST, WALL_ORDER_HIGHEST)

@dataclass
class ProfileSettings:
    earthquake_method: 'str' = EARTHQUAKE_METHOD_CURVE
    wall_upgrade_threshold_m: 'int' = WALL_UPGRADE_THRESHOLD_M_DEFAULT
    bb_wall_upgrade_threshold_m: 'float' = BB_WALL_UPGRADE_THRESHOLD_M_DEFAULT
    reserve_builders: 'int' = RESERVE_BUILDERS_DEFAULT
    upgrade_order: 'str' = UPGRADE_ORDER_PRICIEST
    wall_order: 'str' = WALL_ORDER_LOWEST
    notifications: 'bool' = True      # Windows notifications: run finished / bot stuck / error
    tray_on_close: 'bool' = False     # closing the window keeps the app in the notification area
    stop_hotkey: 'bool' = True        # F12 stops the bot (only while it runs)
    skip_min_loot_k: 'int' = SKIP_MIN_LOOT_K_DEFAULT  # skip bases whose gold + elixir is below this (thousands)
    hero_upgrade: 'bool' = False      # upgrade heroes by itself (works even with Auto upgrade off)
    hero_selection: 'str' = ','.join(HERO_KEYS)  # which heroes (comma separated keys)
    hero_min_free_builders: 'int' = HERO_MIN_FREE_DEFAULT  # start a hero only with at least this many free builders


def get_settings_path():
    dest = get_user_app_data_dir() / SETTINGS_FILENAME
    ensure_dir(dest.parent)
    return dest


def _normalize_earthquake_method(raw):
    if raw == EARTHQUAKE_METHOD_RANDOM or raw == EARTHQUAKE_METHOD_CURVE:
        return str(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s == 'random placement':
            return EARTHQUAKE_METHOD_RANDOM
        if s == 'curve placement':
            return EARTHQUAKE_METHOD_CURVE
    return EARTHQUAKE_METHOD_CURVE


def _normalize_wall_threshold_m(raw):
    '''Millions of gold/elixir that trigger wall upgrades; 0 = only when storages are full.'''
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return WALL_UPGRADE_THRESHOLD_M_DEFAULT
    return max(0, min(WALL_UPGRADE_THRESHOLD_M_MAX, value))


def _normalize_bb_wall_threshold_m(raw):
    '''Millions (one decimal) of Builder Base gold/elixir that trigger BB wall upgrades;
    0 = as soon as the loot pays two walls of the cheapest level.'''
    try:
        value = round(float(raw), 1)
    except (TypeError, ValueError):
        return BB_WALL_UPGRADE_THRESHOLD_M_DEFAULT
    return max(0.0, min(BB_WALL_UPGRADE_THRESHOLD_M_MAX, value))


def _bb_wall_threshold_from_json(raw):
    '''``bb_wall_upgrade_threshold_m``; older files saved thousands under ``_k``.'''
    if 'bb_wall_upgrade_threshold_m' in raw:
        return _normalize_bb_wall_threshold_m(raw['bb_wall_upgrade_threshold_m'])
    try:
        return _normalize_bb_wall_threshold_m(float(raw.get('bb_wall_upgrade_threshold_k', 0)) / 1000)
    except (TypeError, ValueError):
        return BB_WALL_UPGRADE_THRESHOLD_M_DEFAULT


def _normalize_upgrade_order(raw):
    if isinstance(raw, str) and raw.strip().lower() in UPGRADE_ORDER_OPTIONS:
        return raw.strip().lower()
    return UPGRADE_ORDER_PRICIEST


def _normalize_wall_order(raw):
    if isinstance(raw, str) and raw.strip().lower() in WALL_ORDER_OPTIONS:
        return raw.strip().lower()
    return WALL_ORDER_LOWEST


def _normalize_bool(raw, default):
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str) and raw.strip().lower() in ('true', 'false', '1', '0'):
        return raw.strip().lower() in ('true', '1')
    return default


def _normalize_reserve_builders(raw):
    '''Builders the auto-upgrader must leave free (the wall flow spends through them).
    0 = every free builder may be used; walls-maxed accounts want 0.'''
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return RESERVE_BUILDERS_DEFAULT
    return max(0, min(RESERVE_BUILDERS_MAX, value))


def _normalize_skip_min_loot_k(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return SKIP_MIN_LOOT_K_DEFAULT
    return max(0, min(SKIP_MIN_LOOT_K_MAX, value))


def _normalize_hero_selection(raw):
    '''Known hero keys only, in canonical order, as a comma string. An empty or unknown
    value falls back to every hero.'''
    items = raw if isinstance(raw, (list, tuple)) else str(raw or '').split(',')
    chosen = {str(i).strip().lower() for i in items}
    keys = [k for k in HERO_KEYS if k in chosen]
    return ','.join(keys or HERO_KEYS)


def _normalize_hero_min_free(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return HERO_MIN_FREE_DEFAULT
    return max(1, min(HERO_MIN_FREE_MAX, value))


def load_profile_settings():
    path = get_settings_path()
    if not path.is_file():
        return ProfileSettings()

    try:
        raw = json.loads(path.read_text(encoding = 'utf-8'))
        if not isinstance(raw, dict):
            return ProfileSettings()
        return ProfileSettings(
            earthquake_method = _normalize_earthquake_method(raw.get('earthquake_method')),
            wall_upgrade_threshold_m = _normalize_wall_threshold_m(raw.get('wall_upgrade_threshold_m', WALL_UPGRADE_THRESHOLD_M_DEFAULT)),
            bb_wall_upgrade_threshold_m = _bb_wall_threshold_from_json(raw),
            reserve_builders = _normalize_reserve_builders(raw.get('reserve_builders', RESERVE_BUILDERS_DEFAULT)),
            upgrade_order = _normalize_upgrade_order(raw.get('upgrade_order', UPGRADE_ORDER_PRICIEST)),
            wall_order = _normalize_wall_order(raw.get('wall_order', WALL_ORDER_LOWEST)),
            notifications = _normalize_bool(raw.get('notifications', True), True),
            tray_on_close = _normalize_bool(raw.get('tray_on_close', False), False),
            stop_hotkey = _normalize_bool(raw.get('stop_hotkey', True), True),
            skip_min_loot_k = _normalize_skip_min_loot_k(raw.get('skip_min_loot_k', SKIP_MIN_LOOT_K_DEFAULT)),
            hero_upgrade = _normalize_bool(raw.get('hero_upgrade', False), False),
            hero_selection = _normalize_hero_selection(raw.get('hero_selection')),
            hero_min_free_builders = _normalize_hero_min_free(raw.get('hero_min_free_builders', HERO_MIN_FREE_DEFAULT)))
    except (json.JSONDecodeError, OSError):
        return ProfileSettings()  # [recovered: decompiler turned this into `return None`, crashing every caller on a corrupt settings.json]



def save_profile_settings(settings):
    path = get_settings_path()
    path.parent.mkdir(parents = True, exist_ok = True)
    normalized = ProfileSettings(
        earthquake_method = _normalize_earthquake_method(settings.earthquake_method),
        wall_upgrade_threshold_m = _normalize_wall_threshold_m(getattr(settings, 'wall_upgrade_threshold_m', WALL_UPGRADE_THRESHOLD_M_DEFAULT)),
        bb_wall_upgrade_threshold_m = _normalize_bb_wall_threshold_m(getattr(settings, 'bb_wall_upgrade_threshold_m', BB_WALL_UPGRADE_THRESHOLD_M_DEFAULT)),
        reserve_builders = _normalize_reserve_builders(getattr(settings, 'reserve_builders', RESERVE_BUILDERS_DEFAULT)),
        upgrade_order = _normalize_upgrade_order(getattr(settings, 'upgrade_order', UPGRADE_ORDER_PRICIEST)),
        wall_order = _normalize_wall_order(getattr(settings, 'wall_order', WALL_ORDER_LOWEST)),
        notifications = _normalize_bool(getattr(settings, 'notifications', True), True),
        tray_on_close = _normalize_bool(getattr(settings, 'tray_on_close', False), False),
        stop_hotkey = _normalize_bool(getattr(settings, 'stop_hotkey', True), True),
        skip_min_loot_k = _normalize_skip_min_loot_k(getattr(settings, 'skip_min_loot_k', SKIP_MIN_LOOT_K_DEFAULT)),
        hero_upgrade = _normalize_bool(getattr(settings, 'hero_upgrade', False), False),
        hero_selection = _normalize_hero_selection(getattr(settings, 'hero_selection', None)),
        hero_min_free_builders = _normalize_hero_min_free(getattr(settings, 'hero_min_free_builders', HERO_MIN_FREE_DEFAULT)))
    payload = asdict(normalized)
    path.write_text(json.dumps(payload, indent = 2), encoding = 'utf-8')
