"""Windowed game (title bar + borders): the capture is cropped to the client area."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import unittest
from ctypes import wintypes
from unittest import mock

from app.services.window import WindowService


def _service(client, origin):
    ws = WindowService.__new__(WindowService)
    ws.user32 = mock.Mock()

    def get_client(hwnd, ref):
        ref._obj.left, ref._obj.top, ref._obj.right, ref._obj.bottom = 0, 0, client[0], client[1]
        return 1

    def to_screen(hwnd, ref):
        ref._obj.x, ref._obj.y = origin
        return 1

    ws.user32.GetClientRect.side_effect = get_client
    ws.user32.ClientToScreen.side_effect = to_screen
    return ws


def _rect(left, top, right, bottom):
    r = wintypes.RECT()
    r.left, r.top, r.right, r.bottom = left, top, right, bottom
    return r


class ClientCropTests(unittest.TestCase):
    def test_title_bar_is_cropped(self):
        # live 22/11: 2388x1380 window, 2388x1343 client below a 37 px title bar
        ws = _service((2388, 1343), (100, 137))
        self.assertEqual(ws._client_crop(1, _rect(100, 100, 2488, 1480), 2388, 1380), (0, 37, 2388, 1343))

    def test_supported_window_untouched(self):
        ws = _service((2560, 1440), (0, 0))
        self.assertIsNone(ws._client_crop(1, _rect(0, 0, 2560, 1440), 2560, 1440))
        ws.user32.GetClientRect.assert_not_called()

    def test_client_not_supported_either(self):
        ws = _service((1000, 1000), (0, 40))
        self.assertIsNone(ws._client_crop(1, _rect(0, 0, 1000, 1040), 1000, 1040))

    def test_client_outside_window_rejected(self):
        ws = _service((2388, 1343), (100, 400))
        self.assertIsNone(ws._client_crop(1, _rect(100, 100, 2488, 1480), 2388, 1380))


if __name__ == '__main__':
    unittest.main()
