"""Recovery must press a Continue / Claim Reward that only matches at another UI scale."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import threading
import unittest
from unittest import mock

from app.core import bot as botmod


def _bot(find):
    b = botmod.Bot.__new__(botmod.Bot)
    b.stop_event = threading.Event()
    b.window = mock.Mock()
    b.window.screenshot.return_value = mock.Mock(shape = (1440, 2560, 3))
    b.input = mock.Mock()
    b.vision = mock.Mock()
    b.vision.find_template.side_effect = find
    b.config = mock.Mock()
    b._update_config_size = lambda f: None
    b._check_stop = lambda: None
    b._battle_rewards = mock.Mock()
    b._battle_rewards.handle.return_value = False
    b._dismiss_okay_or_exit_on_frame = lambda f: False
    b._tap_empty_until_chest_continue = lambda: None
    return b


class RecoveryContinueTests(unittest.TestCase):
    def test_continue_found_only_with_sweep_is_pressed(self):
        state = {'pressed': False}

        def find(frame, tpl, *a, **kw):
            if tpl == 'chestcontinue.png' and kw.get('sweep') and not state['pressed']:
                return (1253, 1235)
            return (None, None)

        b = _bot(find)

        def click(x, y, **kw):
            if (x, y) == (1253, 1235):
                state['pressed'] = True
        b.input.click.side_effect = click
        b._find_home_village_builder = lambda frame, roi: (5, 5) if state['pressed'] else (None, None)
        self.assertTrue(b._home_screen_recovery())
        self.assertTrue(state['pressed'])

    def test_return_home_uses_sweep(self):
        seen = []

        def find(frame, tpl, *a, **kw):
            if tpl == 'returnhome.png':
                seen.append(kw.get('sweep'))
            return (None, None)

        b = _bot(find)
        b._find_home_village_builder = lambda frame, roi: (5, 5)
        b._home_screen_recovery()
        self.assertEqual(seen, [True])




class StarChestTests(unittest.TestCase):
    def test_claim_taps_through_the_chest_scene(self):
        def find(frame, tpl, *a, **kw):
            return (1280, 1136) if tpl == 'starbonus_claim.png' else (None, None)

        b = _bot(find)
        b._tap_empty_until_chest_continue = mock.Mock()
        self.assertTrue(b._claim_star_bonus_on_frame(mock.Mock()))
        b._tap_empty_until_chest_continue.assert_called_once()


class StarBonusClaimTests(unittest.TestCase):
    def test_recovery_claims_star_bonus_popup(self):
        state = {'pressed': False}

        def find(frame, tpl, *a, **kw):
            if tpl == 'starbonus_claim.png' and kw.get('sweep') and not state['pressed']:
                return (1280, 1136)
            return (None, None)

        b = _bot(find)

        def click(x, y, **kw):
            if (x, y) == (1280, 1136):
                state['pressed'] = True
        b.input.click.side_effect = click
        b._find_home_village_builder = lambda frame, roi: (5, 5) if state['pressed'] else (None, None)
        self.assertTrue(b._home_screen_recovery())
        self.assertTrue(state['pressed'])

    def test_attack_wait_claims_star_bonus_first(self):
        state = {'pressed': False}

        def find(frame, tpl, *a, **kw):
            if tpl == 'starbonus_claim.png' and not state['pressed']:
                return (1280, 1136)
            if tpl == 'attack.png' and state['pressed']:
                return (141, 1385)
            return (None, None)

        b = _bot(find)
        b._search_region_for_template = lambda *a, **k: None
        b._nudge_view_to_reveal_attack = lambda: None

        def click(x, y, **kw):
            state['pressed'] = True
        b.input.click.side_effect = click
        self.assertEqual(b._wait_for_attack_with_nudge(timeout = 10), (141, 1385))



class AttackWaitRewardTests(unittest.TestCase):
    def test_continue_is_pressed_without_waiting_for_the_timeout(self):
        state = {'pressed': False}

        def find(frame, tpl, *a, **kw):
            if tpl == 'chestcontinue.png' and not state['pressed']:
                return (1253, 1235)
            if tpl == 'attack.png' and state['pressed']:
                return (141, 1385)
            return (None, None)

        b = _bot(find)
        b._search_region_for_template = lambda *a, **k: None
        b._nudge_view_to_reveal_attack = lambda: None
        b._click_further_continues = lambda: None
        calls = []

        def click(x, y, **kw):
            calls.append((x, y))
            state['pressed'] = True
        b.input.click.side_effect = click
        self.assertEqual(b._wait_for_attack_with_nudge(timeout = 10), (141, 1385))
        self.assertEqual(calls, [(1253, 1235)])



class OkayWaitTests(unittest.TestCase):
    def test_returns_at_once_when_continue_is_already_up(self):
        def find(frame, tpl, *a, **kw):
            return (1253, 1235) if tpl == 'chestcontinue.png' else (None, None)

        b = _bot(find)
        import time
        t0 = time.time()
        self.assertEqual(b._wait_for_okay_or_next_screen(timeout = 10), (None, None))
        self.assertLess(time.time() - t0, 1.0)

    def test_okay_is_returned(self):
        def find(frame, tpl, *a, **kw):
            return (700, 800) if tpl == 'okay.png' else (None, None)

        b = _bot(find)
        self.assertEqual(b._wait_for_okay_or_next_screen(timeout = 10), (700, 800))


if __name__ == '__main__':
    unittest.main()
