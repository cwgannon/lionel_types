"""The grown-ups' corner: a hold-to-open gate and the parent menu."""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

import pygame

from . import keys
from .settings import Settings
from .style import DIM, LIGHT_BLUE, Style

HOLD_SECONDS = 2.0
MENU_TIMEOUT = 45.0  # close by itself if left open, in case a kid wanders into it
CHORD_TEXT = "Control + Shift + Q" if keys.IS_MAC else "Ctrl + Shift + Q"


class HoldGate:
    """Fires once after a condition has held steadily for ``seconds``."""

    def __init__(self, seconds: float = HOLD_SECONDS) -> None:
        self.seconds = seconds
        self.held_for = 0.0
        self._latched = False  # must let go before it can fire again

    @property
    def progress(self) -> float:
        return min(1.0, self.held_for / self.seconds)

    def update(self, active: bool, dt: float) -> bool:
        if not active:
            self.held_for = 0.0
            self._latched = False
            return False
        if self._latched:
            return False
        self.held_for += dt
        if self.held_for >= self.seconds:
            self._latched = True
            self.held_for = 0.0
            return True
        return False


CHOICE_TEXT = {
    "letter_case": {"upper": "ABC  capitals", "lower": "abc  small letters", "as_typed": "Aa  as typed"},
    "theme": {"rainbow": "Rainbow", "classic": "Classic light blue"},
    "text_size": {"big": "Big", "bigger": "Bigger", "biggest": "Biggest"},
    "mode": {"free": "Free typing", "find": "Find the letter"},
}

# (key, label, setting it changes). Toggles are booleans; others cycle through CHOICES.
MENU_ITEMS: Sequence[Tuple[str, str, str]] = (
    ("1", "Sound", "sound"),
    ("2", "Voice", "voice"),
    ("3", "Letters", "letter_case"),
    ("4", "Colors", "theme"),
    ("5", "Text size", "text_size"),
    ("6", "Activity", "mode"),
)


class ParentMenu:
    """Settings overlay. ``on_change`` is told which setting changed; ``on_command`` gets "clear"/"quit"/"close"."""

    def __init__(self, settings: Settings, on_change: Callable[[str], None],
                 on_command: Callable[[str], None], notes: Sequence[str] = ()) -> None:
        self.settings = settings
        self.on_change = on_change
        self.on_command = on_command
        self.notes = list(notes)
        self.idle = 0.0

    def update(self, dt: float) -> None:
        self.idle += dt
        if self.idle > MENU_TIMEOUT:
            self.on_command("close")

    def key_down(self, key: keys.Key) -> None:
        self.idle = 0.0
        if key.action == keys.ENTER or (key.action == keys.LABEL and key.text == "ESC"):
            self.on_command("close")
            return
        if key.action != keys.CHAR:
            return
        choice = key.text.lower()
        for number, _, name in MENU_ITEMS:
            if choice == number:
                if name in CHOICE_TEXT:
                    self.settings.cycle(name)
                else:
                    setattr(self.settings, name, not getattr(self.settings, name))
                self.on_change(name)
                return
        if choice == "c":
            self.on_command("clear")
        elif choice == "q":
            self.on_command("quit")

    def value_text(self, name: str) -> str:
        value = getattr(self.settings, name)
        if isinstance(value, bool):
            return "On" if value else "Off"
        return CHOICE_TEXT[name][value]

    def draw(self, surface: pygame.Surface, style: Style) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 215))
        surface.blit(shade, (0, 0))

        font, small = style.ui_font, style.small_font
        row = round(font.get_linesize() * 1.35)
        rows: List[Tuple[str, str, Optional[str]]] = [
            (number, label, self.value_text(name)) for number, label, name in MENU_ITEMS
        ]
        rows += [("C", "Clear the screen", None), ("Q", "Quit Lionel Types", None), ("Esc", "Back to typing", None)]

        panel_w = min(style.width - 40, round(style.height * 1.05))
        panel_h = row * (len(rows) + 2) + small.get_linesize() * (len(self.notes) + 1)
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (style.width // 2, style.height // 2)
        pygame.draw.rect(surface, (18, 22, 34), panel, border_radius=24)
        pygame.draw.rect(surface, LIGHT_BLUE, panel, width=3, border_radius=24)

        x = panel.left + row
        y = panel.top + row // 2
        title = font.render("Parent menu", True, LIGHT_BLUE)
        surface.blit(title, (x, y))
        y += row * 1.4
        for number, label, value in rows:
            _draw_keycap(surface, font, number, (x, y), row)
            surface.blit(font.render(label, True, (235, 238, 245)), (x + row * 1.6, y))
            if value is not None:
                text = font.render(value, True, LIGHT_BLUE)
                surface.blit(text, (panel.right - row - text.get_width(), y))
            y += row
        for note in self.notes:
            surface.blit(small.render(note, True, DIM), (x, y))
            y += small.get_linesize()


def _draw_keycap(surface: pygame.Surface, font: pygame.font.Font, text: str, pos: Tuple[float, float], row: int) -> None:
    label = font.render(text, True, LIGHT_BLUE)
    rect = pygame.Rect(int(pos[0]), int(pos[1]), max(row * 1.2, label.get_width() + row * 0.5), font.get_height() * 1.05)
    pygame.draw.rect(surface, (40, 52, 74), rect, border_radius=8)
    pygame.draw.rect(surface, LIGHT_BLUE, rect, width=2, border_radius=8)
    surface.blit(label, label.get_rect(center=rect.center))


def draw_hold_progress(surface: pygame.Surface, style: Style, progress: float) -> None:
    """A ring that fills while the grown-up keeps holding the chord."""
    radius = round(style.height * 0.05)
    center = (style.width // 2, round(style.height * 0.88))
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    pygame.draw.circle(surface, (40, 52, 74), center, radius, width=max(4, radius // 5))
    if progress > 0:
        pygame.draw.arc(surface, LIGHT_BLUE, rect, math.pi / 2 - progress * math.tau, math.pi / 2, width=max(4, radius // 5))
    text = style.small_font.render("Keep holding for the parent menu", True, DIM)
    surface.blit(text, text.get_rect(midtop=(center[0], center[1] + radius + 10)))


def draw_hint(surface: pygame.Surface, style: Style, alpha: float) -> None:
    """A quiet reminder at startup of how grown-ups get to the menu."""
    text = style.small_font.render(f"Grown-ups: hold {CHORD_TEXT} for the parent menu", True, DIM)
    text.set_alpha(round(255 * max(0.0, min(1.0, alpha))))
    surface.blit(text, text.get_rect(midbottom=(style.width // 2, style.height - round(style.height * 0.03))))


def draw_click_to_play(surface: pygame.Surface, style: Style, now: float) -> None:
    """Shown when another window has the keyboard, e.g. if Windows kept focus elsewhere at startup."""
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surface.blit(shade, (0, 0))
    pulse = 1 + 0.05 * math.sin(now * 4)
    text = style.font.render("Click to play!", True, LIGHT_BLUE)
    text = pygame.transform.smoothscale(text, (round(text.get_width() * pulse), round(text.get_height() * pulse)))
    surface.blit(text, text.get_rect(center=(style.width // 2, style.height // 2)))
