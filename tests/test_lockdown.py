import ctypes
import sys

import pytest

from lionel_types import keys, lockdown

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows keyboard lock")
KEY_UP = 0x0101


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
    assert send(0x5B, message=KEY_UP) == 1
    assert [(down, key.text) for _, down, key in lock.poll()] == [(True, "WIN"), (False, "WIN")]  # ...and forwarded
    assert send(0x41) == 0  # the letter A goes through normally

    assert send(0xA4, message=windows.WM_SYSKEYDOWN) == 1  # Alt pressed while we're in front...
    fake.foreground = 222
    assert send(0xA4, message=KEY_UP) == 1  # ...is released to us too, even after focus moved
    assert send(0x5B) == 0  # another window is in front: hands off...
    fake.foreground = 111
    assert send(0x5B, message=KEY_UP) == 0  # ...including the release Windows is waiting for
    assert [(down, key.text) for _, down, key in lock.poll()] == [(True, "ALT"), (False, "ALT")]


class FakeQuartz:
    """Just enough of PyObjC's Quartz for the Mac event tap's decisions."""

    def CGEventGetIntegerValueField(self, event, field):
        return event["keycode"]

    def CGEventGetFlags(self, event):
        return event["flags"]

    def CGEventTapEnable(self, tap, enabled):
        pass


def test_mac_tap_releases_follow_presses_even_if_command_is_let_go_first(monkeypatch):
    import types

    from lionel_types.lockdown import macos

    appkit = types.SimpleNamespace(NSEvent=types.SimpleNamespace(
        eventWithCGEvent_=lambda event: types.SimpleNamespace(charactersIgnoringModifiers=lambda: event["chars"])))
    monkeypatch.setitem(sys.modules, "Quartz", FakeQuartz())
    monkeypatch.setitem(sys.modules, "AppKit", appkit)
    lock = macos.MacLockdown()
    lock._app = types.SimpleNamespace(isActive=lambda: True)

    def event(kind, keycode, flags=0, chars=""):
        e = {"keycode": keycode, "flags": flags, "chars": chars}
        return lock._on_event(None, kind, e, None) is not None  # True = let through

    cmd = macos.FLAG_COMMAND
    assert not event(macos.KEY_DOWN, 0, cmd, "a")  # Cmd+A: swallowed, "a" forwarded
    assert not event(macos.KEY_DOWN, 0, cmd, "a")  # auto-repeat
    assert not event(macos.KEY_UP, 0, 0, "a")  # released after Cmd: still ours
    assert event(macos.KEY_DOWN, 7, 0, "x")  # plain x goes to the app normally...
    assert event(macos.KEY_UP, 7, cmd, "x")  # ...and so does its release, even with Cmd down now
    assert event(macos.KEY_DOWN, macos.ESCAPE, cmd | macos.FLAG_OPTION)  # Force Quit stays available
    assert [(key_id, down, key.text) for key_id, down, key in lock.poll()] == [
        (("mac", 0), True, "a"), (("mac", 0), False, "")]


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
