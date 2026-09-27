"""Drive the whole app headlessly with real pygame events."""

import pygame
import pytest

from lionel_types.app import App
from lionel_types.find_letter import FindTheLetter
from lionel_types.free_typing import FreeTyping

FRAME = 1 / 60


@pytest.fixture
def app(tmp_path):
    app = App(windowed=True, voice=False, size=(1280, 720), settings_path=tmp_path / "settings.json")
    app.spoken = []
    app.speaker.say = app.spoken.append
    yield app
    app.close()


def frames(app, count=1):
    for _ in range(count):
        app.step(FRAME)


def down(app, keycode, unicode="", mod=0):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=keycode, unicode=unicode, mod=mod, scancode=0))
    frames(app)


def up(app, keycode):
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=keycode, mod=0, scancode=0))
    frames(app)


def press(app, keycode, unicode=""):
    down(app, keycode, unicode)
    up(app, keycode)


def type_text(app, text):
    for ch in text:
        if ch == "\n":
            press(app, pygame.K_RETURN)
        else:
            press(app, ord(ch.lower()), ch)


def shown(app):
    return "".join(g.text if not g.is_label else f"[{g.text}]" for g in app.mode.page.glyphs())


def open_menu(app):
    down(app, pygame.K_LCTRL)
    down(app, pygame.K_LSHIFT)
    down(app, pygame.K_q, "\x11", pygame.KMOD_CTRL | pygame.KMOD_SHIFT)
    frames(app, 130)  # a bit over two seconds
    for key in (pygame.K_q, pygame.K_LSHIFT, pygame.K_LCTRL):
        up(app, key)
    assert app.menu is not None


def test_typing_shows_capitals_and_says_letters_and_words(app):
    type_text(app, "cat ")
    assert shown(app) == "CAT "
    assert app.spoken[-4:] == ["C", "A", "T", "cat"]


def test_special_keys_show_as_keycaps_and_modifiers_only_when_tapped_alone(app):
    press(app, pygame.K_F1)
    press(app, pygame.K_LSHIFT)
    down(app, pygame.K_LSHIFT)
    press(app, pygame.K_a, "A")
    up(app, pygame.K_LSHIFT)
    assert shown(app) == "[F1][SHIFT]A"


def test_enter_backspace_and_arrows_edit_the_page(app):
    type_text(app, "ab")
    press(app, pygame.K_LEFT)
    type_text(app, "x")
    assert shown(app) == "AXB"
    press(app, pygame.K_BACKSPACE)
    press(app, pygame.K_RETURN)
    assert [["".join(g.text for g in p)] for p in app.mode.page.paragraphs] == [["A"], ["B"]]
    press(app, pygame.K_UP)
    assert app.mode.page.para == 0


def test_a_full_page_celebrates_and_starts_over(app):
    for ch in "the quick brown fox jumps over the lazy dog " * 6:
        type_text(app, ch)
        if "Great job!" in app.spoken:
            break
    else:
        pytest.fail("the page never filled up")
    assert app.effects.flyers  # the old page is tumbling away
    assert shown(app) == ch.upper()  # the new page starts with the key that overflowed


def test_ctrl_shift_does_not_type_and_holding_q_opens_the_parent_menu(app):
    type_text(app, "a")
    open_menu(app)
    assert shown(app) == "A"


def test_parent_menu_changes_settings_saves_them_and_switches_to_the_game(app, tmp_path):
    open_menu(app)
    press(app, pygame.K_4, "4")  # colors
    press(app, pygame.K_6, "6")  # activity
    press(app, pygame.K_RETURN)
    assert app.menu is None
    assert isinstance(app.mode, FindTheLetter)
    saved = (tmp_path / "settings.json").read_text()
    assert '"theme": "classic"' in saved and '"mode": "find"' in saved


def test_find_the_letter_rewards_the_right_key(app):
    app.settings.mode = "find"
    app.setting_changed("mode")
    game = app.mode
    wrong = "b" if game.target != "b" else "c"
    press(app, ord(wrong), wrong)
    assert game.stars == 0 and game.wiggle > 0
    target = game.target
    press(app, ord(target), target)
    assert game.stars == 1
    frames(app, 120)
    assert game.target != target  # moved on to a new letter
    assert app.spoken[-1].startswith("Find the letter")


def test_quit_from_the_menu_stops_the_app(app):
    open_menu(app)
    press(app, pygame.K_q, "q")
    assert not app.running


def test_full_screen_ignores_window_close_requests(app):
    app.windowed = False
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    frames(app)
    assert app.running


def test_the_mouse_makes_sparkles(app):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 100), button=1))
    frames(app)
    assert app.effects.particles


def test_switching_back_to_free_typing_keeps_the_page(app):
    type_text(app, "hi")
    for mode in ("find", "free"):
        app.settings.mode = mode
        app.setting_changed("mode")
    assert isinstance(app.mode, FreeTyping)
    assert shown(app) == "HI"
