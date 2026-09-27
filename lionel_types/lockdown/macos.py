"""macOS: kiosk-style presentation options, plus an event tap for Command shortcuts.

Presentation options (no extra permission needed) hide the Dock and menu bar and
switch off Cmd+Tab, Mission Control, Cmd+H and the power-button dialog. The app's
menu shortcuts (Cmd+Q, Cmd+M, ...) are removed.

If the app has Accessibility permission, an event tap also swallows every
Command-key combination (Cmd+Space, screenshots, ...) and media keys. The tap
runs on the main thread, so if the app ever hangs macOS switches the tap off by
itself - and Cmd+Option+Esc (Force Quit) is deliberately left working.

Everything here needs PyObjC; without it the app still runs, just less locked down.
"""

from __future__ import annotations

from typing import List, Optional

from ..keys import char_key, label_key
from . import ForwardedKey, Lockdown

# NSApplicationPresentationOptions
HIDE_DOCK = 1 << 1
HIDE_MENU_BAR = 1 << 3
DISABLE_APPLE_MENU = 1 << 4
DISABLE_PROCESS_SWITCHING = 1 << 5  # Cmd+Tab, Mission Control
DISABLE_SESSION_TERMINATION = 1 << 7  # the power-button / log-out dialog
DISABLE_HIDE_APPLICATION = 1 << 8  # Cmd+H
KIOSK = (HIDE_DOCK | HIDE_MENU_BAR | DISABLE_APPLE_MENU | DISABLE_PROCESS_SWITCHING
         | DISABLE_SESSION_TERMINATION | DISABLE_HIDE_APPLICATION)
KIOSK_FALLBACK = HIDE_DOCK | HIDE_MENU_BAR | DISABLE_PROCESS_SWITCHING

# Quartz event types, flags and fields.
KEY_DOWN, KEY_UP, SYSTEM_DEFINED = 10, 11, 14
TAP_DISABLED_BY_TIMEOUT, TAP_DISABLED_BY_USER_INPUT = 0xFFFFFFFE, 0xFFFFFFFF
FLAG_CONTROL, FLAG_COMMAND = 1 << 18, 1 << 20
KEYCODE_FIELD = 9  # kCGKeyboardEventKeycode
SPACE, LEFT, RIGHT, DOWN, UP = 49, 123, 124, 125, 126
# Top-row keys on recent Apple keyboards: Mission Control, Launchpad, Spotlight, Dictation, Do Not Disturb.
SYSTEM_KEYCODES = frozenset({160, 131, 177, 176, 178})
# Media keys arrive as "system defined" events; data1 carries which key.
MEDIA_KEYS = {0: ("VOL UP", "volume up"), 1: ("VOL DOWN", "volume down"), 7: ("MUTE", "mute"),
              16: ("PLAY", "play"), 17: ("NEXT", "next"), 18: ("PREV", "previous"),
              2: ("BRIGHT UP", "brighter"), 3: ("BRIGHT DOWN", "darker")}
PRESS_AND_HOLD = "ApplePressAndHoldEnabled"

PERMISSION_NOTE = ("For stronger locking (Cmd+Space, screenshots): System Settings > Privacy & Security"
                   " > Accessibility, and allow Terminal (or Lionel Types).")


class MacLockdown(Lockdown):
    def __init__(self) -> None:
        super().__init__()
        self._events: List[ForwardedKey] = []
        self._app = None
        self._tap = None
        self._source = None
        self._presentation_set = False
        self._press_and_hold_set = False

    def prepare(self) -> None:
        # Holding a letter would pop up the accent picker (e -> è é ê). Kids hold keys.
        try:
            from Foundation import NSUserDefaults

            NSUserDefaults.standardUserDefaults().setBool_forKey_(False, PRESS_AND_HOLD)
            self._press_and_hold_set = True
        except Exception:
            pass

    def engage(self, window_id: int) -> None:
        try:
            from AppKit import NSApplication
        except ImportError:
            self.notes.append("Keyboard lock needs PyObjC: pip install -r requirements.txt")
            return
        self._app = NSApplication.sharedApplication()
        for options in (KIOSK, KIOSK_FALLBACK):
            try:
                self._app.setPresentationOptions_(options)
                self._presentation_set = True
                break
            except Exception:
                continue
        if self._presentation_set:
            self.notes.append("Blocked: Cmd+Tab, Mission Control, Dock, menu bar, Cmd+Q, Cmd+H.")
        try:
            _strip_shortcuts(self._app.mainMenu())
        except Exception:
            pass
        if self._start_event_tap():
            self.notes.append("Blocked: all Command-key shortcuts, media keys.")
        else:
            self.notes.append(PERMISSION_NOTE)
        self.notes.append("Emergency exit: Cmd+Option+Esc (Force Quit).")

    def poll(self) -> List[ForwardedKey]:
        events, self._events = self._events, []
        return events

    def release(self) -> None:
        try:
            import Quartz

            if self._tap is not None:
                Quartz.CGEventTapEnable(self._tap, False)
                Quartz.CFRunLoopRemoveSource(Quartz.CFRunLoopGetMain(), self._source, Quartz.kCFRunLoopCommonModes)
        except Exception:
            pass
        self._tap = self._source = None
        if self._presentation_set and self._app is not None:
            try:
                self._app.setPresentationOptions_(0)
            except Exception:
                pass
            self._presentation_set = False
        if self._press_and_hold_set:
            try:
                from Foundation import NSUserDefaults

                NSUserDefaults.standardUserDefaults().removeObjectForKey_(PRESS_AND_HOLD)
            except Exception:
                pass
            self._press_and_hold_set = False

    def _start_event_tap(self) -> bool:
        try:
            import Quartz
        except ImportError:
            return False
        mask = (1 << KEY_DOWN) | (1 << KEY_UP) | (1 << SYSTEM_DEFINED)
        for location in (Quartz.kCGHIDEventTap, Quartz.kCGSessionEventTap):
            try:
                tap = Quartz.CGEventTapCreate(location, Quartz.kCGHeadInsertEventTap,
                                              Quartz.kCGEventTapOptionDefault, mask, self._on_event, None)
            except Exception:
                tap = None
            if tap:
                break
        else:
            return False  # no Accessibility permission
        self._tap = tap
        self._source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        # Main run loop: served whenever pygame pumps events.
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetMain(), self._source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)
        return True

    def _on_event(self, proxy, event_type, event, refcon):
        """Return the event to let it through, or None to swallow it."""
        try:
            import Quartz

            if event_type in (TAP_DISABLED_BY_TIMEOUT, TAP_DISABLED_BY_USER_INPUT):
                if self._tap is not None:
                    Quartz.CGEventTapEnable(self._tap, True)
                return event
            if self._app is None or not self._app.isActive():
                return event  # only ever interfere while we are the app in front
            if event_type == SYSTEM_DEFINED:
                return self._media_key(event)
            keycode = Quartz.CGEventGetIntegerValueField(event, KEYCODE_FIELD)
            flags = Quartz.CGEventGetFlags(event)
            if keycode in SYSTEM_KEYCODES:
                return None
            if flags & FLAG_COMMAND:
                self._forward_typed(event, keycode, event_type == KEY_DOWN)
                return None
            if flags & FLAG_CONTROL and keycode in (SPACE, LEFT, RIGHT, UP, DOWN):
                return None  # input-source switching and Spaces
        except Exception:  # never let a bug here break the keyboard
            pass
        return event

    def _forward_typed(self, event, keycode: int, down: bool) -> None:
        """A palm resting on Command shouldn't make typing vanish: show the letter anyway."""
        from AppKit import NSEvent

        text = NSEvent.eventWithCGEvent_(event).charactersIgnoringModifiers() or ""
        if len(text) == 1 and text.isprintable():
            self._events.append((("mac", keycode), down, char_key(text)))

    def _media_key(self, event) -> Optional[object]:
        from AppKit import NSEvent

        ns_event = NSEvent.eventWithCGEvent_(event)
        if ns_event is None or ns_event.subtype() != 8:
            return event
        data = ns_event.data1()
        which, state = (data & 0xFFFF0000) >> 16, (data & 0xFF00) >> 8
        if which in MEDIA_KEYS:
            self._events.append((("media", which), state == 0xA, label_key(*MEDIA_KEYS[which])))
        return None


def _strip_shortcuts(menu) -> None:
    """Remove every keyboard shortcut from the app's menus (Cmd+Q, Cmd+M, Cmd+W, ...)."""
    if menu is None:
        return
    for item in menu.itemArray():
        item.setKeyEquivalent_("")
        if item.hasSubmenu():
            _strip_shortcuts(item.submenu())
