import pygame
import pytest

from lionel_types import keys


def test_letters_type_themselves_and_say_their_name():
    key = keys.from_pygame(pygame.K_b, "b")
    assert (key.action, key.text, key.speech) == (keys.CHAR, "b", "B")


def test_letters_still_type_when_ctrl_makes_pygame_report_a_control_character():
    key = keys.from_pygame(pygame.K_a, "\x01", pygame.KMOD_CTRL)
    assert (key.action, key.text) == (keys.CHAR, "a")


def test_shift_capitalizes_the_fallback_letter():
    assert keys.from_pygame(pygame.K_a, "", pygame.KMOD_SHIFT).text == "A"


def test_punctuation_is_spoken_by_name():
    assert keys.from_pygame(pygame.K_PERIOD, ".").speech == "dot"


@pytest.mark.parametrize("keycode, label", [
    (pygame.K_F1, "F1"), (pygame.K_F12, "F12"), (pygame.K_PRINTSCREEN, "PRTSC"),
    (pygame.K_SCROLLLOCK, "SCRLK"), (pygame.K_DELETE, "DEL"), (pygame.K_PAGEDOWN, "PGDN"),
    (pygame.K_ESCAPE, "ESC"), (pygame.K_CAPSLOCK, "CAPS"),
])
def test_special_keys_show_their_name_in_capitals(keycode, label):
    key = keys.from_pygame(keycode)
    assert (key.action, key.text) == (keys.LABEL, label)


@pytest.mark.parametrize("keycode, dx, dy", [
    (pygame.K_LEFT, -1, 0), (pygame.K_RIGHT, 1, 0), (pygame.K_UP, 0, -1), (pygame.K_DOWN, 0, 1),
])
def test_arrows_move_the_cursor(keycode, dx, dy):
    key = keys.from_pygame(keycode)
    assert (key.action, key.dx, key.dy) == (keys.MOVE, dx, dy)


def test_enter_backspace_and_modifiers():
    assert keys.from_pygame(pygame.K_RETURN).action == keys.ENTER
    assert keys.from_pygame(pygame.K_KP_ENTER).action == keys.ENTER
    assert keys.from_pygame(pygame.K_BACKSPACE).action == keys.BACKSPACE
    assert keys.from_pygame(pygame.K_LSHIFT).action == keys.MODIFIER


def test_number_pad_types_digits_even_with_num_lock_off():
    key = keys.from_pygame(pygame.K_KP7, "")
    assert (key.action, key.text) == (keys.CHAR, "7")


def test_letter_case_setting():
    assert keys.apply_case("a", "upper") == "A"
    assert keys.apply_case("A", "lower") == "a"
    assert keys.apply_case("A", "as_typed") == "A"


def test_parent_chord_is_exactly_ctrl_shift_q():
    assert keys.is_parent_chord({pygame.K_LCTRL, pygame.K_RSHIFT, pygame.K_q})
    assert not keys.is_parent_chord({pygame.K_LCTRL, pygame.K_LSHIFT})
    assert not keys.is_parent_chord({pygame.K_LCTRL, pygame.K_LSHIFT, pygame.K_q, pygame.K_a})
    assert not keys.is_parent_chord({pygame.K_LCTRL, pygame.K_q, pygame.K_a})
