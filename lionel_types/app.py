"""Lionel Types: a full-screen, kid-proof typing playground."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Hashable, List, Optional, Sequence, Set, Tuple, Union

# SDL reads these when pygame starts.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")  # real pixels on scaled displays
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
os.environ.setdefault("SDL_VIDEO_MAC_FULLSCREEN_SPACES", "0")  # plain full screen, not its own Space

import pygame  # noqa: E402

from . import keys, lockdown, speech  # noqa: E402
from . import settings as settings_store  # noqa: E402
from .effects import Effects, pick  # noqa: E402
from .find_letter import FindTheLetter  # noqa: E402
from .free_typing import FreeTyping  # noqa: E402
from .parent import HoldGate, ParentMenu, draw_click_to_play, draw_hint, draw_hold_progress  # noqa: E402
from .sound import Sounds  # noqa: E402
from .style import BACKGROUND, LIGHT_BLUE, RAINBOW, Style, load_font  # noqa: E402

FPS = 60
HINT_SECONDS = 8.0

Mode = Union[FreeTyping, FindTheLetter]


class App:
    def __init__(
        self,
        windowed: bool = False,
        lock: bool = True,
        audio: bool = True,
        voice: bool = True,
        size: Optional[Tuple[int, int]] = None,
        settings_path: Optional[Path] = None,
    ) -> None:
        pygame.display.init()
        pygame.font.init()  # sound starts up in Sounds, and only if wanted: it can be slow without a sound card
        self.windowed = windowed
        self.settings_path = settings_path
        self.settings = settings_store.load(settings_path)
        self.lockdown = lockdown.create(enabled=lock and not windowed)
        self.lockdown.prepare()

        pygame.display.set_caption("Lionel Types")
        pygame.display.set_icon(_icon())
        if windowed:
            self.screen = pygame.display.set_mode(size or (1280, 800), pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode(size or (0, 0), pygame.FULLSCREEN)
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)  # keep the mouse on this screen, even with two monitors
        self.lockdown.engage(pygame.display.get_wm_info().get("window", 0))

        self.style = Style(self.screen.get_size(), self.settings)
        self.effects = Effects()
        self.sounds = Sounds(enabled=audio)
        self.sounds.muted = not self.settings.sound
        self.speaker = speech.create() if voice else speech.Speaker()

        self.now = 0.0
        self.running = True
        self.held: Set[Hashable] = set()
        self.tapped: Optional[Hashable] = None  # a modifier pressed alone: shown if released alone
        self.gate = HoldGate()
        self.menu: Optional[ParentMenu] = None
        self.intercepted: List[str] = []  # keys the lock took from the OS, for --self-test
        self.modes: Dict[str, Mode] = {}
        self.mode = self._mode(self.settings.mode)
        if self.settings.mode == "free":
            self.say("Let's type!")
        self._closed = False

    # --- main loop -----------------------------------------------------------

    def run(self, self_test: Optional[float] = None) -> None:
        clock = pygame.time.Clock()
        try:
            while self.running:
                self.step(min(clock.tick(FPS) / 1000, 0.1))
                pygame.display.flip()
                if self_test is not None and self.now >= self_test:
                    self.running = False
        finally:
            self.close()
        if self_test is not None:
            print("Lionel Types self-test finished.")
            for note in self.lockdown.notes:
                print(" -", note)
            print(" - Keys intercepted:", ", ".join(dict.fromkeys(self.intercepted)) or "none")
            free = self.modes.get("free")
            if isinstance(free, FreeTyping):
                print(" - On screen:", " ".join(g.text for g in free.page.glyphs() if not g.is_space) or "nothing")

    def step(self, dt: float) -> None:
        """One frame: input, animation, drawing."""
        self.now += dt
        for event in pygame.event.get():
            self.handle_event(event)
        for key_id, down, key in self.lockdown.poll():
            if down:
                self.intercepted.append(key.text)
            self.on_key(key_id, down, key)
        self.update(dt)
        self.draw()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.lockdown.release()
        self.speaker.close()
        pygame.quit()

    # --- input ---------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        kind = event.type
        if kind == pygame.QUIT:
            if self.windowed:  # full screen ignores Alt+F4, Cmd+Q and friends
                self.running = False
        elif kind in (pygame.KEYDOWN, pygame.KEYUP):
            key = keys.from_pygame(event.key, getattr(event, "unicode", ""), event.mod)
            if event.key in keys.LOCK_KEYS:
                # Not tracked as held: on a Mac, Caps Lock stays "down" for as long as it is on.
                # There, turning it off arrives as a key-up, which should show CAPS too.
                if kind == pygame.KEYDOWN or keys.IS_MAC:
                    self.press(key)
            else:
                self.on_key(event.key, kind == pygame.KEYDOWN, key)
        elif kind == pygame.MOUSEMOTION and self.menu is None:
            self.effects.trail(*event.pos, color=pick(self.style.palette))
        elif kind == pygame.MOUSEBUTTONDOWN and self.menu is None and event.button in (1, 2, 3):
            self.effects.firework(*event.pos, colors=self.style.palette, count=40, speed=380)
            self.sounds.play("pop")
        elif kind in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
            self.held.clear()  # key releases may have gone to another window
            self.tapped = None
        elif kind == pygame.WINDOWSIZECHANGED:
            self.screen = pygame.display.get_surface()
            self.restyle()

    def on_key(self, key_id: Hashable, down: bool, key: keys.Key) -> None:
        if not down:
            self.held.discard(key_id)
            if self.tapped == key_id:
                self.tapped = None
                if self.menu is None:
                    self.mode.key_down(keys.label_key(key.text, key.speech))
            return
        if key_id in self.held:
            return  # the OS repeating a held key
        self.tapped = key_id if key.action == keys.MODIFIER and not self.held else None
        self.held.add(key_id)
        if key.action != keys.MODIFIER:
            self.press(key)

    def press(self, key: keys.Key) -> None:
        """A key press for the menu or the current activity."""
        if self.menu is not None:
            self.menu.key_down(key)
        elif not self._grown_up_chord():
            self.mode.key_down(key)

    def _grown_up_chord(self) -> bool:
        """Ctrl and Shift together means a grown-up is reaching for the menu: don't type."""
        return bool(self.held & keys.CTRL_KEYS) and bool(self.held & keys.SHIFT_KEYS)

    # --- parent menu ---------------------------------------------------------

    def open_menu(self) -> None:
        notes: List[str] = list(self.lockdown.notes)
        if self.windowed:
            notes.append("Window mode: the keyboard lock is off.")
        if not self.sounds.available:
            notes.append("No sound device was found.")
        self.menu = ParentMenu(self.settings, self.setting_changed, self.menu_command, notes)
        self.sounds.play("enter")

    def setting_changed(self, name: str) -> None:
        settings_store.save(self.settings, self.settings_path)
        if name == "sound":
            self.sounds.muted = not self.settings.sound
            self.sounds.play("enter")
        elif name == "voice":
            self.say("Voice on")
        elif name in ("theme", "text_size"):
            self.restyle(recolor=name == "theme")
        elif name == "mode":
            existed = self.settings.mode in self.modes
            self.mode = self._mode(self.settings.mode)
            if isinstance(self.mode, FreeTyping):
                self.say("Let's type!")
            elif existed:
                self.mode.prompt()

    def menu_command(self, command: str) -> None:
        if command == "quit":
            self.running = False
            return
        self.menu = None
        if command == "clear":
            if isinstance(self.mode, FreeTyping):
                self.mode.new_page()
            self.effects.clear()

    # --- frame ---------------------------------------------------------------

    def say(self, text: str) -> None:
        if text and self.settings.voice:
            self.speaker.say(text)

    def restyle(self, recolor: bool = False) -> None:
        self.style = Style(self.screen.get_size(), self.settings)
        for mode in self.modes.values():
            if recolor:
                mode.recolor()
            mode.resize()

    def update(self, dt: float) -> None:
        if self.gate.update(keys.is_parent_chord(self.held), dt) and self.menu is None:
            self.open_menu()
        if self.menu is not None:
            self.menu.update(dt)
        self.mode.update(dt)
        self.effects.update(dt, self.style.height)

    def draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self.mode.draw(self.screen)
        self.effects.draw(self.screen)
        if not self.windowed and not pygame.key.get_focused():
            draw_click_to_play(self.screen, self.style, self.now)
        elif self.menu is not None:
            self.menu.draw(self.screen, self.style)
        elif self.gate.progress > 0.1:
            draw_hold_progress(self.screen, self.style, self.gate.progress)
        elif self.now < HINT_SECONDS:
            draw_hint(self.screen, self.style, min(1.0, (HINT_SECONDS - self.now) / 2))

    def _mode(self, name: str) -> Mode:
        if name not in self.modes:
            self.modes[name] = FindTheLetter(self) if name == "find" else FreeTyping(self)
        return self.modes[name]


def _icon() -> pygame.Surface:
    """A little rainbow "Aa" for the window and taskbar."""
    icon = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.rect(icon, (18, 22, 34), icon.get_rect(), border_radius=14)
    pygame.draw.rect(icon, LIGHT_BLUE, icon.get_rect(), width=3, border_radius=14)
    font = load_font(40)
    big, small = font.render("A", True, RAINBOW[0]), font.render("a", True, RAINBOW[5])
    icon.blit(big, big.get_rect(midright=(33, 34)))
    icon.blit(small, small.get_rect(midleft=(33, 36)))
    return icon


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="lionel_types", description="A full-screen typing playground for kids.")
    parser.add_argument("--windowed", action="store_true",
                        help="run in a normal window with no keyboard lock (for grown-ups trying it out)")
    parser.add_argument("--no-lock", action="store_true", help="full screen, but leave the OS shortcuts alone")
    parser.add_argument("--mute", action="store_true", help="no sounds or voice this time")
    parser.add_argument("--self-test", type=float, metavar="SECONDS",
                        help="run for SECONDS, then quit and report what the keyboard lock did")
    args = parser.parse_args(argv)
    app = App(windowed=args.windowed, lock=not args.no_lock, audio=not args.mute, voice=not args.mute)
    app.run(self_test=args.self_test)
