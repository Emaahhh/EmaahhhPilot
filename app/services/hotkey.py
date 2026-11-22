'''Global hotkey (Windows): a dedicated thread owns RegisterHotKey + a message loop and
emits a Qt signal when the key is pressed.

The registration is only held while the bot runs (start() on run start, stop() on run
end), so F12 is not taken away from other programs the rest of the time.
'''
from __future__ import annotations
import sys
import threading
from PySide6.QtCore import QObject, Signal
from app.utils.logger import setup_logger
logger = setup_logger('Hotkey')

VK_F12 = 0x7B
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
_HOTKEY_ID = 0x4550  # arbitrary, unique to this app


class GlobalHotkey(QObject):
    pressed = Signal()
    registrationFailed = Signal(str)

    def __init__(self, vk = VK_F12, modifiers = 0, label = 'F12', parent = None):
        super().__init__(parent)
        self._vk = vk
        self._modifiers = modifiers
        self.label = label
        self._thread = None
        self._thread_id = 0
        self._registered = False

    def is_active(self):
        return self._thread is not None and self._thread.is_alive() and self._registered

    def start(self):
        '''Register the key. Returns immediately; a refusal is reported by registrationFailed
        (the key is held by another program).'''
        if sys.platform != 'win32' or (self._thread is not None and self._thread.is_alive()):
            return
        ready = threading.Event()
        self._thread = threading.Thread(target = self._run, args = (ready,), daemon = True, name = 'HotkeyThread')
        self._thread.start()
        ready.wait(2.0)
        if not self._registered:
            # Reported from the caller's thread: a signal emitted by a thread that is about
            # to end can be lost, and the caller needs the answer right after start().
            self.registrationFailed.emit(self.label)

    def stop(self):
        thread = self._thread
        if thread is None:
            return
        if sys.platform == 'win32' and self._thread_id:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        thread.join(1.5)
        self._thread = None
        self._thread_id = 0
        self._registered = False

    def _run(self, ready):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # creates this thread's message queue
        self._thread_id = kernel32.GetCurrentThreadId()
        ok = bool(user32.RegisterHotKey(None, _HOTKEY_ID, MOD_NOREPEAT | self._modifiers, self._vk))
        self._registered = ok
        ready.set()
        if not ok:
            logger.warning('Could not register the %s hotkey (already used by another program)', self.label)
            return
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                    self.pressed.emit()
        finally:
            user32.UnregisterHotKey(None, _HOTKEY_ID)
            self._registered = False
