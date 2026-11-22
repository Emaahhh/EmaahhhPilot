'''Popup / post-battle buttons drawn a few % off the authored size are still found.
Live: "Claim Reward" at 0.97x scored 0.76 at 1.0x (threshold 0.8) — the bot never
pressed it and the attack loop stalled on the Victory screen.'''
import _testenv  # noqa: F401 — must precede the app imports (test log folder)
import unittest

import cv2
import numpy as np


def _frame_with(template_name, scale, at = (1300, 1250)):
    '''A 2560x1440 dark frame with ``template_name`` pasted at ``scale``.'''
    from app.utils.common import get_resource_path
    tpl = cv2.imread(str(get_resource_path(f'templates/16_9/{template_name}')))
    (h, w) = tpl.shape[:2]
    tpl = cv2.resize(tpl, (round(w * scale), round(h * scale)), interpolation = cv2.INTER_AREA)
    frame = np.full((1440, 2560, 3), (40, 30, 20), np.uint8)
    noise = np.random.default_rng(7).integers(0, 25, frame.shape, dtype = np.uint8)
    frame = cv2.add(frame, noise)
    (th, tw) = tpl.shape[:2]
    (x, y) = (at[0] - tw // 2, at[1] - th // 2)
    frame[y:y + th, x:x + tw] = tpl
    return frame


class PopupScaleTests(unittest.TestCase):

    def setUp(self):
        from app.config import Config
        from app.services.vision import VisionService
        Config().set_target_size(2560, 1440)
        VisionService._popup_scale = 1.0
        VisionService._popup_scales = {}
        self.vision = VisionService

    def test_each_button_keeps_its_own_scale(self):
        # Live: Okay matched at 1.04x, Return Home at 1.00x — one shared scale flip-flopped.
        self.vision.find_template(_frame_with('chestclaim.png', 0.97), 'chestclaim.png')
        claim_scale = self.vision._popup_scales['chestclaim.png']
        self.assertIsNotNone(self.vision.find_template(_frame_with('returnhome.png', 1.0), 'returnhome.png')[0])
        self.assertLessEqual(abs(self.vision._popup_scales['returnhome.png'] - 1.0), 0.03)
        self.assertEqual(self.vision._popup_scales['chestclaim.png'], claim_scale)  # untouched

    def test_claim_reward_found_when_drawn_smaller(self):
        frame = _frame_with('chestclaim.png', 0.97)
        (x, y) = self.vision.find_template(frame, 'chestclaim.png')
        self.assertIsNotNone(x)
        self.assertLess(abs(x - 1300), 8)
        self.assertLess(abs(y - 1250), 8)
        self.assertNotEqual(self.vision._popup_scale, 1.0)  # the working scale is remembered

    def test_learned_scale_is_used_for_the_other_buttons(self):
        self.vision.find_template(_frame_with('chestclaim.png', 0.97), 'chestclaim.png')
        learned = self.vision._popup_scale
        frame = _frame_with('returnhome.png', learned)
        self.assertIsNotNone(self.vision.find_template(frame, 'returnhome.png')[0])

    def test_continue_drawn_ten_percent_bigger_is_found_when_expected(self):
        # Live: "Continue" matched the reference only at 1.10x. Without a near miss at
        # 1.0x the normal search gives up; the expected-button sweep finds it.
        frame = _frame_with('chestcontinue.png', 1.10)
        (x, y) = self.vision.find_template(frame, 'chestcontinue.png', sweep = True)
        self.assertIsNotNone(x)
        self.assertLess(abs(x - 1300), 10)
        self.assertLess(abs(y - 1250), 10)

    def test_sweep_does_not_invent_absent_buttons(self):
        frame = _frame_with('chestcontinue.png', 1.10)
        self.assertEqual(self.vision.find_template(frame, 'chestclaim.png', sweep = True), (None, None))
        self.assertEqual(self.vision.find_template(frame, 'returnhome.png', sweep = True), (None, None))

    def test_absent_button_is_not_invented(self):
        frame = _frame_with('chestclaim.png', 0.97)
        self.assertEqual(self.vision.find_template(frame, 'returnhome.png'), (None, None))
        self.assertEqual(self.vision.find_template(frame, 'okay.png'), (None, None))

    def test_other_templates_keep_exact_matching(self):
        # Only the popup buttons get the scale search; everything else is unchanged.
        self.assertNotIn('attack.png', self.vision._SCALE_TOLERANT)


if __name__ == '__main__':
    unittest.main()
