'''Regression tests for decompiler leftovers fixed after the 1.1.0 release.'''
import _testenv  # noqa: F401 — must precede the app imports (test log folder)
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


class _TempAppData(unittest.TestCase):
    '''Point LOCALAPPDATA at a temp folder so nothing touches the real settings.'''

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {'LOCALAPPDATA': self._tmp.name})
        self._env.start()
        import app.utils.common as common
        self._mig = mock.patch.object(common, '_migration_checked', True)
        self._mig.start()

    def tearDown(self):
        self._mig.stop()
        self._env.stop()
        self._tmp.cleanup()


class PlayerListStoreTests(_TempAppData):

    def test_load_without_any_file_returns_empty_list(self):
        from app.utils import player_list_store as s
        with mock.patch.object(s, '_legacy_player_list_paths', return_value = [Path(self._tmp.name) / 'missing.json']):
            self.assertEqual(s.load_players(), [])

    def test_save_then_load_round_trip(self):
        from app.utils import player_list_store as s
        with mock.patch.object(s, '_legacy_player_list_paths', return_value = []):
            s.save_players([s.PlayerEntry(name = 'Alpha', enabled = True), s.PlayerEntry(name = 'Beta', enabled = False)])
            loaded = s.load_players()
        self.assertEqual([(p.name, p.enabled) for p in loaded], [('Alpha', True), ('Beta', False)])

    def test_corrupt_file_returns_empty_list(self):
        from app.utils import player_list_store as s
        with mock.patch.object(s, '_legacy_player_list_paths', return_value = []):
            s.get_player_list_path().write_text('{not json', encoding = 'utf-8')
            self.assertEqual(s.load_players(), [])

    def test_legacy_file_is_migrated(self):
        from app.utils import player_list_store as s
        legacy = Path(self._tmp.name) / 'legacy_player_list.json'
        legacy.write_text(json.dumps([{'name': 'Old', 'enabled': True}]), encoding = 'utf-8')
        with mock.patch.object(s, '_legacy_player_list_paths', return_value = [legacy]):
            self.assertEqual([p.name for p in s.load_players()], ['Old'])


class WindowSelectionStoreTests(_TempAppData):

    def test_corrupt_file_falls_back_to_auto_detect(self):
        from app.utils import window_settings_store as s
        s.get_window_selection_path().write_text('[[[', encoding = 'utf-8')
        sel = s.load_window_selection()
        self.assertIsNotNone(sel)
        self.assertFalse(sel.is_set())

    def test_clear_without_file_is_a_no_op(self):
        from app.utils import window_settings_store as s
        s.clear_window_selection()
        self.assertFalse(s.get_window_selection_path().exists())


class VisionFixTests(unittest.TestCase):

    def test_find_all_template_centers_survives_matcher_error(self):
        from app.services.vision import VisionService
        with mock.patch.object(VisionService, '_find_template_matches', return_value = None):
            self.assertEqual(VisionService.find_all_template_centers(np.zeros((10, 10, 3), np.uint8), 'x.png'), [])

    def test_psm10_prefers_expected_glyph_then_highest_confidence(self):
        from app.services import vision
        data = {'level': [5, 5, 5], 'text': ['8', '3', '3'], 'conf': [95, 40, 70]}
        with mock.patch.object(vision.pytesseract, 'image_to_data', return_value = data):
            mono = np.full((30, 30), 255, np.uint8)
            got = vision.VisionService._tesseract_single_glyph_confidence_psm10(mono, 5, 5, 20, 25, expected_char = '3')
        self.assertEqual(got, 70.0)

    def test_find_chars_ocr_with_psm10_confidence(self):
        from app.services import vision
        mono = np.full((40, 40), 255, np.uint8)
        prep = (None, mono, 1.0, 0, 0)
        with mock.patch.object(vision.VisionService, '_preprocess_ocr_region', return_value = prep), \
             mock.patch.object(vision.pytesseract, 'image_to_boxes', return_value = '7 5 5 15 30 0\n'), \
             mock.patch.object(vision.VisionService, '_tesseract_single_glyph_confidence_psm10', return_value = 88.0):
            chars = vision.VisionService.find_chars_ocr(np.zeros((40, 40, 3), np.uint8), psm10_glyph_confidence = True)
        self.assertEqual(len(chars), 1)
        self.assertEqual(chars[0].text, '7')
        self.assertEqual(chars[0].confidence, 88.0)

    def test_ocr_without_tesseract_returns_empty_lists(self):
        from app.services import vision
        prep = (None, np.zeros((10, 10), np.uint8), 1.0, 0, 0)
        err = vision.pytesseract.TesseractNotFoundError()
        with mock.patch.object(vision.VisionService, '_preprocess_ocr_region', return_value = prep), \
             mock.patch.object(vision.pytesseract, 'image_to_boxes', side_effect = err), \
             mock.patch.object(vision.pytesseract, 'image_to_data', side_effect = err), \
             mock.patch.object(vision.VisionService, '_log_tesseract_missing'):
            self.assertEqual(vision.VisionService.find_chars_ocr(np.zeros((10, 10, 3), np.uint8)), [])
            self.assertEqual(vision.VisionService.find_words_ocr(np.zeros((10, 10, 3), np.uint8)), [])
            self.assertTrue(math.isnan(vision.VisionService._tesseract_single_glyph_confidence_psm10(np.full((30, 30), 255, np.uint8), 5, 5, 20, 25)))


if __name__ == '__main__':
    unittest.main()
