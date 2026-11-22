'''Session history (JSON under %LOCALAPPDATA%\\EmaahhhPilot\\history.json).

One entry per finished run: when it ended, village, army, duration, attacks, loot and walls.
Everything stays on this PC. :func:`summarize` and :func:`by_army` turn the list into the
numbers shown on the History page (loot per attack, attacks per hour, yield per army).
'''
from __future__ import annotations
import json
import threading
from datetime import datetime
from app.utils.common import ensure_dir, get_user_app_data_dir
from app.utils.logger import setup_logger
logger = setup_logger('HistoryStore')

HISTORY_FILENAME = 'history.json'
MAX_SESSIONS = 500
_lock = threading.Lock()
_INT_FIELDS = ('duration_s', 'attacks', 'gold', 'elixir', 'dark', 'walls')


def get_history_path():
    return get_user_app_data_dir() / HISTORY_FILENAME


def _clean(entry):
    '''A well-formed entry from anything dict-like, or None.'''
    if not isinstance(entry, dict):
        return None
    out = {'ended': str(entry.get('ended') or ''), 'village': 'builder' if entry.get('village') == 'builder' else 'home',
           'army': str(entry.get('army') or '—')}
    for key in _INT_FIELDS:
        try:
            out[key] = max(0, int(entry.get(key) or 0))
        except (TypeError, ValueError):
            out[key] = 0
    if not out['ended']:
        return None
    return out


def load_history():
    '''All saved sessions, oldest first. [] when there is no (readable) file.'''
    path = get_history_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding = 'utf-8'))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    return [e for e in (_clean(item) for item in raw) if e is not None]


def _write(sessions):
    path = get_history_path()
    ensure_dir(path.parent)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(sessions[-MAX_SESSIONS:], indent = 1), encoding = 'utf-8')
    tmp.replace(path)  # atomic: a crash mid-write never leaves a half file


def append_session(stats, army):
    '''Save one finished run (the bot's ``last_run_stats`` + the army label). Runs that did
    nothing (no attack, no wall) are not worth a row. Returns the saved entry or None.'''
    entry = _clean(dict(stats, army = army, ended = datetime.now().isoformat(timespec = 'seconds')))
    if entry is None or (entry['attacks'] <= 0 and entry['walls'] <= 0):
        return None
    with _lock:
        try:
            sessions = load_history()
            sessions.append(entry)
            _write(sessions)
        except OSError:
            logger.warning('Could not save the session history', exc_info = True)
            return None
    return entry


def clear_history():
    with _lock:
        try:
            get_history_path().unlink()
        except FileNotFoundError:
            pass
        except OSError:
            _write([])


def _per_hour(total, seconds):
    return (total * 3600.0 / seconds) if seconds > 0 else 0.0


def summarize(sessions):
    '''Totals and averages over ``sessions`` (home village figures; Builder Base runs only
    count in sessions / attacks / time since they record no loot).'''
    attacks = sum(s['attacks'] for s in sessions)
    seconds = sum(s['duration_s'] for s in sessions)
    home = [s for s in sessions if s['village'] == 'home']
    home_attacks = sum(s['attacks'] for s in home)
    gold = sum(s['gold'] for s in home)
    elixir = sum(s['elixir'] for s in home)
    dark = sum(s['dark'] for s in home)
    home_seconds = sum(s['duration_s'] for s in home)
    return {
        'sessions': len(sessions), 'attacks': attacks, 'seconds': seconds, 'walls': sum(s['walls'] for s in sessions),
        'gold': gold, 'elixir': elixir, 'dark': dark,
        'gold_per_attack': gold / home_attacks if home_attacks else 0.0,
        'elixir_per_attack': elixir / home_attacks if home_attacks else 0.0,
        'attacks_per_hour': _per_hour(attacks, seconds),
        'loot_per_hour': _per_hour(gold + elixir, home_seconds)}


def by_army(sessions):
    '''One row per army: sessions, attacks, average gold / elixir per attack and attacks per
    hour, best loot-per-hour first.'''
    groups = {}
    for s in sessions:
        groups.setdefault((s['village'], s['army']), []).append(s)
    rows = []
    for ((village, army), items) in groups.items():
        attacks = sum(s['attacks'] for s in items)
        seconds = sum(s['duration_s'] for s in items)
        gold = sum(s['gold'] for s in items)
        elixir = sum(s['elixir'] for s in items)
        rows.append({'army': army, 'village': village, 'sessions': len(items), 'attacks': attacks,
                     'gold_per_attack': gold / attacks if attacks else 0.0,
                     'elixir_per_attack': elixir / attacks if attacks else 0.0,
                     'attacks_per_hour': _per_hour(attacks, seconds),
                     'loot_per_hour': _per_hour(gold + elixir, seconds)})
    rows.sort(key = lambda r: r['loot_per_hour'], reverse = True)
    return rows


def loot_per_hour_series(sessions, limit = 24):
    '''(label, gold per hour, elixir per hour) for the last ``limit`` Home Village sessions
    that lasted at least a minute (shorter ones give a meaningless rate).'''
    out = []
    for s in sessions:
        if s['village'] != 'home' or s['duration_s'] < 60:
            continue
        try:
            label = datetime.fromisoformat(s['ended']).strftime('%d/%m')
        except ValueError:
            label = '?'
        out.append((label, _per_hour(s['gold'], s['duration_s']), _per_hour(s['elixir'], s['duration_s'])))
    return out[-limit:]
