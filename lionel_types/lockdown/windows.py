"""Windows: a low-level keyboard hook, plus switching off the Sticky Keys pop-ups.

The hook runs on its own thread and swallows the keys that would take a kid out of
the app (Windows key, Alt, Esc, Print Screen, media/launch keys) - but only while
our window is in front. Swallowed keys are forwarded so the app can still show them.

Ctrl+Alt+Del cannot be blocked by any app, which makes it the grown-ups' emergency exit.
"""

from __future__ import annotations

import atexit
import ctypes
import queue
import threading
import time
from ctypes import wintypes
from typing import Dict, List, Optional, Set, Tuple

from ..keys import Key, label_key, modifier_key
from . import ForwardedKey, Lockdown

# Private handles so our argtypes never clash with anyone else's use of ctypes.windll.
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104
WM_QUIT = 0x0012

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = (wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
user32.GetMessageW.restype = ctypes.c_int
user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = (wintypes.HWND,)
user32.BringWindowToTop.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.SystemParametersInfoW.argtypes = (wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT)
user32.SystemParametersInfoW.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.argtypes = ()
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

# Virtual-key codes the hook takes away from Windows, and how the app shows them instead.
SWALLOWED: Dict[int, Key] = {
    0x5B: modifier_key("WIN", "windows"),  # Start menu, Win+D, Win+Tab, ...
    0x5C: modifier_key("WIN", "windows"),
    0xA4: modifier_key("ALT", "alt"),  # Alt+Tab, Alt+F4, Alt+Esc, Alt+Space
    0xA5: modifier_key("ALT", "alt"),
    0x1B: label_key("ESC", "escape"),  # Ctrl+Esc, Ctrl+Shift+Esc
    0x2C: label_key("PRTSC", "print screen"),  # the Snipping Tool
    0x5D: label_key("MENU", "menu"),
    0x5F: label_key("SLEEP", "sleep"),
    0xA6: label_key("BACK", "back"),
    0xA7: label_key("FORWARD", "forward"),
    0xA8: label_key("REFRESH", "refresh"),
    0xA9: label_key("STOP", "stop"),
    0xAA: label_key("SEARCH", "search"),
    0xAB: label_key("FAVORITES", "favorites"),
    0xAC: label_key("WEB", "web"),
    0xAD: label_key("MUTE", "mute"),
    0xAE: label_key("VOL DOWN", "volume down"),
    0xAF: label_key("VOL UP", "volume up"),
    0xB0: label_key("NEXT", "next"),
    0xB1: label_key("PREV", "previous"),
    0xB2: label_key("STOP", "stop"),
    0xB3: label_key("PLAY", "play"),
    0xB4: label_key("MAIL", "mail"),
    0xB5: label_key("MEDIA", "media"),
    0xB6: label_key("APP", "app"),
    0xB7: label_key("CALC", "calculator"),
}


class _ToggleKeys(ctypes.Structure):  # also the shape of STICKYKEYS
    _fields_ = [("cbSize", wintypes.UINT), ("dwFlags", wintypes.DWORD)]


class _FilterKeys(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwFlags", wintypes.DWORD),
        ("iWaitMSec", wintypes.DWORD),
        ("iDelayMSec", wintypes.DWORD),
        ("iRepeatMSec", wintypes.DWORD),
        ("iBounceMSec", wintypes.DWORD),
    ]


# (struct, SPI_GET..., SPI_SET...) for Sticky Keys (Shift five times),
# Toggle Keys (hold Num Lock) and Filter Keys (hold right Shift).
_ACCESSIBILITY = (
    (_ToggleKeys, 0x003A, 0x003B),
    (_ToggleKeys, 0x0034, 0x0035),
    (_FilterKeys, 0x0032, 0x0033),
)
FEATURE_ON, HOTKEY_ACTIVE, CONFIRM_HOTKEY = 0x1, 0x4, 0x8
FOCUS_GRACE_SECONDS = 5.0


def bring_to_front(hwnd: int) -> bool:
    """Ask for the keyboard. Windows may say no if we were started from the background;
    then the app shows "Click to play!" until someone clicks it."""
    if user32.GetForegroundWindow() != hwnd:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    return user32.GetForegroundWindow() == hwnd


def disable_accessibility_shortcuts() -> List[Tuple[int, ctypes.Structure]]:
    """Stop Shift-mashing from popping up the Sticky Keys dialog.

    Only the keyboard shortcuts are switched off, and only for features that are
    not in use. Changes are not saved to the user profile (fWinIni=0), so even a
    crash is undone by signing out. Returns what to pass to ``restore_accessibility_shortcuts``.
    """
    saved = []
    for struct_type, get_action, set_action in _ACCESSIBILITY:
        current = struct_type()
        current.cbSize = ctypes.sizeof(struct_type)
        if not user32.SystemParametersInfoW(get_action, current.cbSize, ctypes.byref(current), 0):
            continue
        if current.dwFlags & FEATURE_ON:
            continue  # someone relies on this feature; leave it alone
        original = struct_type.from_buffer_copy(current)
        current.dwFlags &= ~(HOTKEY_ACTIVE | CONFIRM_HOTKEY)
        if user32.SystemParametersInfoW(set_action, current.cbSize, ctypes.byref(current), 0):
            saved.append((set_action, original))
    return saved


def restore_accessibility_shortcuts(saved: List[Tuple[int, ctypes.Structure]]) -> None:
    for set_action, original in saved:
        user32.SystemParametersInfoW(set_action, ctypes.sizeof(original), ctypes.byref(original), 0)


class WindowsLockdown(Lockdown):
    def __init__(self) -> None:
        super().__init__()
        self._events: "queue.SimpleQueue[ForwardedKey]" = queue.SimpleQueue()
        self._hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id = 0
        self._hooked = threading.Event()
        self._hook_error = 0
        self._proc = HOOKPROC(self._callback)  # must outlive the hook
        self._down_before_hook: Set[int] = set()
        self._saved_accessibility: List[Tuple[int, ctypes.Structure]] = []
        self._claim_focus_until = 0.0
        self._next_focus_try = 0.0

    def engage(self, window_id: int) -> None:
        self._hwnd = window_id
        # Only insist on the foreground while starting up, so we never fight a
        # grown-up who has opened Task Manager.
        self._claim_focus_until = time.monotonic() + FOCUS_GRACE_SECONDS
        if window_id:
            bring_to_front(window_id)
        self._saved_accessibility = disable_accessibility_shortcuts()
        self._down_before_hook = {vk for vk in SWALLOWED if user32.GetAsyncKeyState(vk) & 0x8000}
        atexit.register(self.release)
        self._thread = threading.Thread(target=self._run, name="keyboard-lock", daemon=True)
        self._thread.start()
        if self._hooked.wait(2) and not self._hook_error:
            self.notes.append("Blocked: Windows key, Alt+Tab, Alt+F4, Esc combos, Print Screen, media keys.")
        else:
            self.notes.append(f"Could not block the Windows key (error {self._hook_error}).")
        if self._saved_accessibility:
            self.notes.append("Sticky Keys pop-ups are off until Lionel Types closes.")
        self.notes.append("Emergency exit: Ctrl+Alt+Del, then Task Manager.")

    def poll(self) -> List[ForwardedKey]:
        now = time.monotonic()
        if self._hwnd and now < self._claim_focus_until and now >= self._next_focus_try:
            self._next_focus_try = now + 0.25
            if bring_to_front(self._hwnd):
                self._claim_focus_until = 0.0
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def release(self) -> None:
        thread, self._thread = self._thread, None
        if thread is not None and self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            thread.join(2)
        saved, self._saved_accessibility = self._saved_accessibility, []
        restore_accessibility_shortcuts(saved)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        if not hook:
            self._hook_error = ctypes.get_last_error() or -1
        self._hooked.set()
        if not hook:
            return
        msg = wintypes.MSG()
        try:
            # The hook is called from inside GetMessageW; WM_QUIT ends the loop.
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                pass
        finally:
            user32.UnhookWindowsHookEx(hook)

    def _callback(self, n_code: int, w_param: int, l_param: int) -> int:
        try:
            if n_code == HC_ACTION and self._hwnd and user32.GetForegroundWindow() == self._hwnd:
                info = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                key = SWALLOWED.get(info.vkCode)
                if key is not None:
                    down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    if not down and info.vkCode in self._down_before_hook:
                        # Windows saw this key go down before we started; let it see it come up.
                        self._down_before_hook.discard(info.vkCode)
                    else:
                        self._events.put((("vk", info.vkCode), down, key))
                        return 1
        except Exception:  # never let a bug here break the whole keyboard
            pass
        return user32.CallNextHookEx(None, n_code, w_param, l_param)
