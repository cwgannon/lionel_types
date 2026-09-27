"""What each key press means to a kid: something to type, a key name to show, or a command."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import pygame

IS_MAC = sys.platform == "darwin"

# What a key press does.
CHAR = "char"  # type a character: letters, digits, punctuation, space
LABEL = "label"  # show the key's name as a little keycap, like F1 or PRTSC
ENTER = "enter"
BACKSPACE = "backspace"
MOVE = "move"  # arrow keys move the cursor
MODIFIER = "modifier"  # Shift/Ctrl/Alt/...: shown only when tapped on its own
IGNORE = "ignore"


@dataclass(frozen=True)
class Key:
    action: str
    text: str = ""  # the character to type, or the label to show
    speech: str = ""  # what to say out loud
    dx: int = 0  # cursor movement, for MOVE
    dy: int = 0


SYMBOL_NAMES = {
    ".": "dot", ",": "comma", "!": "exclamation mark", "?": "question mark",
    "-": "dash", "_": "underscore", "=": "equals", "+": "plus", "*": "star",
    "/": "slash", "\\": "backslash", "|": "bar", ";": "semicolon", ":": "colon",
    "'": "apostrophe", '"': "quote", "`": "backtick", "~": "tilde",
    "(": "open parenthesis", ")": "close parenthesis", "[": "open bracket",
    "]": "close bracket", "{": "open brace", "}": "close brace",
    "<": "less than", ">": "greater than", "@": "at", "#": "hash",
    "$": "dollar", "%": "percent", "^": "caret", "&": "and",
}


def speech_for_char(ch: str) -> str:
    """How to say a typed character.

    Speech engines say a lone capital letter as its name ("B" -> "bee"),
    while a lowercase "a" can come out as "uh", so letters are spoken as capitals.
    """
    if ch == " ":
        return ""
    if ch.isalpha():
        return ch.upper()
    return SYMBOL_NAMES.get(ch, ch)


if IS_MAC:  # Match what is printed on the keycaps.
    _CTRL, _ALT, _GUI = ("CONTROL", "control"), ("OPTION", "option"), ("COMMAND", "command")
else:
    _CTRL, _ALT, _GUI = ("CTRL", "control"), ("ALT", "alt"), ("WIN", "windows")

MODIFIER_NAMES = {
    pygame.K_LSHIFT: ("SHIFT", "shift"),
    pygame.K_RSHIFT: ("SHIFT", "shift"),
    pygame.K_LCTRL: _CTRL,
    pygame.K_RCTRL: _CTRL,
    pygame.K_LALT: _ALT,
    pygame.K_RALT: _ALT,
    pygame.K_LGUI: _GUI,
    pygame.K_RGUI: _GUI,
    pygame.K_MODE: ("ALT GR", "alt graph"),
}

SPECIAL_NAMES = {
    pygame.K_ESCAPE: ("ESC", "escape"),
    pygame.K_TAB: ("TAB", "tab"),
    pygame.K_CAPSLOCK: ("CAPS", "caps lock"),
    pygame.K_NUMLOCK: ("NUMLK", "num lock"),
    pygame.K_SCROLLLOCK: ("SCRLK", "scroll lock"),
    pygame.K_PRINTSCREEN: ("PRTSC", "print screen"),
    pygame.K_PAUSE: ("PAUSE", "pause"),
    pygame.K_INSERT: ("INS", "insert"),
    pygame.K_DELETE: ("DEL", "delete"),
    pygame.K_HOME: ("HOME", "home"),
    pygame.K_END: ("END", "end"),
    pygame.K_PAGEUP: ("PGUP", "page up"),
    pygame.K_PAGEDOWN: ("PGDN", "page down"),
    pygame.K_MENU: ("MENU", "menu"),
    pygame.K_HELP: ("HELP", "help"),
}
for _n in range(1, 16):
    SPECIAL_NAMES[getattr(pygame, f"K_F{_n}")] = (f"F{_n}", f"F {_n}")

ARROWS = {
    pygame.K_LEFT: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_UP: (0, -1),
    pygame.K_DOWN: (0, 1),
}

# Number-pad keys type their symbol even with Num Lock off.
KEYPAD_CHARS = {
    **{getattr(pygame, f"K_KP{d}"): str(d) for d in range(10)},
    pygame.K_KP_PERIOD: ".",
    pygame.K_KP_DIVIDE: "/",
    pygame.K_KP_MULTIPLY: "*",
    pygame.K_KP_MINUS: "-",
    pygame.K_KP_PLUS: "+",
    pygame.K_KP_EQUALS: "=",
}

LOCK_KEYS = frozenset({pygame.K_CAPSLOCK, pygame.K_NUMLOCK, pygame.K_SCROLLLOCK})
CTRL_KEYS = frozenset({pygame.K_LCTRL, pygame.K_RCTRL})
SHIFT_KEYS = frozenset({pygame.K_LSHIFT, pygame.K_RSHIFT})


def char_key(ch: str) -> Key:
    return Key(CHAR, ch, speech_for_char(ch))


def label_key(text: str, speech: str = "") -> Key:
    return Key(LABEL, text, speech or text.lower())


def modifier_key(text: str, speech: str) -> Key:
    return Key(MODIFIER, text, speech)


def from_pygame(keycode: int, unicode: str = "", mod: int = 0) -> Key:
    """Classify a pygame KEYDOWN/KEYUP."""
    if keycode in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return Key(ENTER)
    if keycode == pygame.K_BACKSPACE:
        return Key(BACKSPACE)
    if keycode in ARROWS:
        dx, dy = ARROWS[keycode]
        return Key(MOVE, dx=dx, dy=dy)
    if keycode in MODIFIER_NAMES:
        return modifier_key(*MODIFIER_NAMES[keycode])
    if keycode in SPECIAL_NAMES:
        return label_key(*SPECIAL_NAMES[keycode])
    if keycode in KEYPAD_CHARS:
        return char_key(KEYPAD_CHARS[keycode])
    if len(unicode) == 1 and unicode.isprintable():
        return char_key(unicode)
    ch = _fallback_char(keycode, mod)
    if ch:
        return char_key(ch)
    name = pygame.key.name(keycode)
    if name and name != "unknown key":
        return label_key(name.upper(), name)
    return Key(IGNORE)


def _fallback_char(keycode: int, mod: int) -> str:
    """The character for a key when pygame gives none, e.g. while Ctrl is held."""
    if not 32 <= keycode < 127:
        return ""
    ch = chr(keycode)
    if ch.isalpha() and bool(mod & pygame.KMOD_SHIFT) != bool(mod & pygame.KMOD_CAPS):
        ch = ch.upper()
    return ch


def apply_case(ch: str, letter_case: str) -> str:
    if letter_case == "upper":
        return ch.upper()
    if letter_case == "lower":
        return ch.lower()
    return ch


def is_parent_chord(held: set) -> bool:
    """Exactly Ctrl + Shift + Q among the ordinary keys - unlikely from a mashing toddler.

    Keys the keyboard lock intercepted (tuple ids) don't count, so a key the OS
    lost track of can never lock grown-ups out of the menu.
    """
    ordinary = {key for key in held if isinstance(key, int)}
    return (
        len(ordinary) == 3
        and pygame.K_q in ordinary
        and bool(ordinary & CTRL_KEYS)
        and bool(ordinary & SHIFT_KEYS)
    )
