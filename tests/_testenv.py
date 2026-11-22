'''Imported first by every test module: sends the test run's log to
%LOCALAPPDATA%\\EmaahhhPilot\\test_logs instead of the real emaahhhpilot.log. Must run
before any ``app`` import — the logger opens its file on first use.'''
import os
from pathlib import Path

os.environ.setdefault('EMAAHHHPILOT_LOG_DIR', str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'EmaahhhPilot' / 'test_logs'))
