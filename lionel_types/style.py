"""Fonts, colors, and how glyphs are drawn."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Tuple

import pygame

from .effects import pick
from .page import Color, Glyph
from .settings import Settings

FONT_PATH = Path(__file__).parent / "assets" / "Andika-Bold.ttf"

BACKGROUND = (0, 0, 0)
LIGHT_BLUE = (173, 216, 230)
DIM = (120, 130, 150)
RAINBOW = (
    (255, 94, 94),  # red
    (255, 154, 60),  # orange
    (255, 214, 64),  # yellow
    (126, 217, 87),  # green
    (64, 220, 200),  # teal
    (90, 170, 255),  # blue
    (180, 130, 255),  # purple
    (255, 120, 200),  # pink
)

# Letter height as a share of screen height. "big" is about 120pt on a 1080p screen.
TEXT_SCALE = {"big": 0.11, "bigger": 0.14, "biggest": 0.18}


def load_font(size: int) -> pygame.font.Font:
    """Andika (made for beginning readers: a and g look like handwriting), or pygame's default."""
    try:
        return pygame.font.Font(FONT_PATH, size)
    except (OSError, pygame.error):
        return pygame.font.Font(None, size)


def shade(color: Color, amount: float) -> Color:
    return (int(color[0] * amount), int(color[1] * amount), int(color[2] * amount))


def pop_scale(t: float) -> float:
    """Grow from small to a little too big and settle back: t runs 0 -> 1."""
    t = min(max(t, 0.0), 1.0)
    overshoot = 2.2
    t -= 1
    return 0.2 + 0.8 * (1 + (overshoot + 1) * t ** 3 + overshoot * t ** 2)


class Style:
    """Everything size-dependent. Rebuilt when the screen or text size changes."""

    def __init__(self, screen_size: Tuple[int, int], settings: Settings) -> None:
        self.width, self.height = screen_size
        self.theme = settings.theme
        self.size = max(24, round(self.height * TEXT_SCALE[settings.text_size]))
        self.font = load_font(self.size)
        self.label_font = load_font(max(12, round(self.size * 0.36)))
        self.hero_font = load_font(max(48, round(self.height * 0.45)))
        self.ui_font = load_font(max(16, round(self.height / 30)))
        self.small_font = load_font(max(12, round(self.height / 46)))

        self.ascent = self.font.get_ascent()
        self.cap_height = self.font.metrics("H")[0][3]
        self.line_height = round(self.size * 1.3)
        self.baseline = round(self.size * 0.98)  # from the top of a row
        self.paragraph_gap = round(self.line_height * 0.75)  # the blank line after Enter
        self.max_line_width = self.width * 0.66
        self.max_text_height = self.height * 0.86
        self.label_gap = max(2, round(self.size * 0.07))

        self._surfaces: Dict[Tuple[str, bool, Color], pygame.Surface] = {}
        self._widths: Dict[Tuple[str, bool], float] = {}
        self._last_color: Color = LIGHT_BLUE

    @property
    def center(self) -> Tuple[float, float]:
        return self.width / 2, self.height / 2

    @property
    def palette(self) -> Tuple[Color, ...]:
        return RAINBOW if self.theme == "rainbow" else (LIGHT_BLUE,)

    def next_color(self) -> Color:
        """A fresh color for each glyph, never the same twice in a row."""
        self._last_color = pick(self.palette, avoid=self._last_color)
        return self._last_color

    def measure(self, glyph: Glyph) -> float:
        key = (glyph.text, glyph.is_label)
        width = self._widths.get(key)
        if width is None:
            if glyph.is_label:
                width = self.label_font.size(glyph.text)[0] + 2 * self._label_padding() + 2 * self.label_gap
            else:
                width = self.font.size(glyph.text)[0]
            self._widths[key] = width
        return width

    def glyph_surface(self, glyph: Glyph) -> pygame.Surface:
        """The glyph drawn in its color, sized to one row: blit it at the row's top."""
        key = (glyph.text, glyph.is_label, glyph.color)
        surface = self._surfaces.get(key)
        if surface is None:
            surface = pygame.Surface((max(1, math.ceil(self.measure(glyph))), self.line_height), pygame.SRCALPHA)
            if glyph.is_label:
                self._draw_keycap(surface, glyph.text, glyph.color)
            else:
                surface.blit(self.font.render(glyph.text, True, glyph.color), (0, self.baseline - self.ascent))
            self._surfaces[key] = surface
        return surface

    def pivot_y(self) -> float:
        """The vertical middle of a capital letter, from the top of a row."""
        return self.baseline - self.cap_height / 2

    def _label_padding(self) -> float:
        return self.size * 0.16

    def _draw_keycap(self, surface: pygame.Surface, text: str, color: Color) -> None:
        """A key name in a little 3D keyboard key."""
        cap_h = self.cap_height * 1.3
        lip = max(3, round(self.size * 0.06))
        bottom = self.baseline + self.cap_height * 0.12
        rect = pygame.Rect(self.label_gap, round(bottom - cap_h - lip / 2),
                           surface.get_width() - 2 * self.label_gap, round(cap_h))
        radius = round(cap_h * 0.22)
        pygame.draw.rect(surface, shade(color, 0.45), rect.move(0, lip), border_radius=radius)
        pygame.draw.rect(surface, shade(color, 0.16), rect, border_radius=radius)
        pygame.draw.rect(surface, color, rect, width=max(2, self.size // 28), border_radius=radius)
        label = self.label_font.render(text, True, color)
        surface.blit(label, label.get_rect(center=rect.center))
