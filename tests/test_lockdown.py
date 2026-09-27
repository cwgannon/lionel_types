import ctypes
import sys

import pytest

from lionel_types import keys, lockdown

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows keyboard lock")


def test_disabled_lockdown_blocks_nothing():
    lock = lockdown.create(enabled=False)
    lock.prepare()
    lock.engage(0)
    assert lock.poll() == []
    lock.release()


@windows_only
def test_the_keys_that_escape_an_app_are_swallowed_and_shown():
    from lionel_types.lockdown.windows import SWALLOWED

    for vk, text in ((0x5B, "WIN"), (0x5C, "WIN"), (0xA4, "ALT"), (0x1B, "ESC"), (0x2C, "PRTSC")):
        assert SWALLOWED[vk].text == text
    assert SWALLOWED[0x5B].action == keys.MODIFIER  # shown only when tapped on its own


@windows_only
def test_hook_swallows_escape_keys_only_while_our_window_is_in_front(monkeypatch):
    from lionel_types.lockdown import windows

    class FakeUser32:
        foreground = 111

        def GetForegroundWindow(self):
            return self.foreground

        def CallNextHookEx(self, hook, code, w_param, l_param):
            return 0  # "let it through"

    fake = FakeUser32()
    monkeypatch.setattr(windows, "user32", fake)
    lock = windows.WindowsLockdown()
    lock._hwnd = 111

    def send(vk, message=windows.WM_KEYDOWN):
        info = windows.KBDLLHOOKSTRUCT(vkCode=vk)
        return lock._callback(windows.HC_ACTION, message, ctypes.addressof(info))

    assert send(0x5B) == 1  # Windows key: swallowed...
    assert send(0x5B, message=0x0101) == 1
    assert [(down, key.text) for _, down, key in lock.poll()] == [(True, "WIN"), (False, "WIN")]  # ...and forwarded
    assert send(0xA4, message=windows.WM_SYSKEYDOWN) == 1  # Alt
    assert send(0x41) == 0  # the letter A goes through normally
    fake.foreground = 222  # another window is in front: hands off
    assert send(0x5B) == 0


@windows_only
def test_accessibility_structs_match_the_windows_sizes():
    from lionel_types.lockdown.windows import _FilterKeys, _ToggleKeys

    assert ctypes.sizeof(_ToggleKeys) == 8
    assert ctypes.sizeof(_FilterKeys) == 24


@windows_only
def test_sticky_keys_shortcut_is_switched_off_and_then_restored():
    from lionel_types.lockdown.windows import (
        _ACCESSIBILITY, FEATURE_ON, HOTKEY_ACTIVE, disable_accessibility_shortcuts,
        restore_accessibility_shortcuts, user32,
    )

    def read_flags():
        flags = []
        for struct_type, get_action, _ in _ACCESSIBILITY:
            value = struct_type()
            value.cbSize = ctypes.sizeof(struct_type)
            assert user32.SystemParametersInfoW(get_action, value.cbSize, ctypes.byref(value), 0)
            flags.append(value.dwFlags)
        return flags

    before = read_flags()
    saved = disable_accessibility_shortcuts()
    try:
        during = read_flags()
        for was, now in zip(before, during):
            if not was & FEATURE_ON:
                assert not now & HOTKEY_ACTIVE
    finally:
        restore_accessibility_shortcuts(saved)
    assert read_flags() == before
