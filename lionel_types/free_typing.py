"""Free typing: every key shows up big, centered and colorful."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

import pygame

from . import keys
from .page import Glyph, Layout, Page, layout, move_vertically
from .style import LIGHT_BLUE, RAINBOW, pop_scale

if TYPE_CHECKING:
    from .app import App

POP_SECONDS = 0.28
BLINK_SECONDS = 0.53
GLIDE_RATE = 14.0  # how quickly glyphs slide to new spots when a row re-centers


class FreeTyping:
    def __init__(self, app: "App") -> None:
        self.app = app
        self.page = Page()
        self._layout: Optional[Layout] = None
        self.cursor_x: Optional[float] = None
        self.cursor_y = 0.0
        self.blink = 0.0

    # --- input ---------------------------------------------------------------

    def key_down(self, key: keys.Key) -> None:
        app = self.app
        self.blink = 0.0
        if key.action == keys.CHAR:
            text = keys.apply_case(key.text, app.settings.letter_case)
            if text == " ":
                self._say_word()
                app.sounds.play("space")
            else:
                app.sounds.note_for(key.text)
                app.say(key.speech)
            self._type(Glyph(text, app.style.next_color(), born=app.now))
        elif key.action == keys.LABEL:
            app.sounds.play("label")
            app.say(key.speech)
            self._type(Glyph(key.text, app.style.next_color(), is_label=True, born=app.now))
        elif key.action == keys.ENTER:
            self._say_word()
            app.sounds.play("enter")
            self.page.new_paragraph()
            self._relayout()
            if self._overflowing():
                self.new_page(celebrate=any(True for _ in self.page.glyphs()))
        elif key.action == keys.BACKSPACE:
            self._backspace()
        elif key.action == keys.MOVE:
            if key.dx < 0:
                self.page.move_left()
            elif key.dx > 0:
                self.page.move_right()
            else:
                move_vertically(self.page, self.layout, key.dy)

    def _type(self, glyph: Glyph) -> None:
        self.page.insert(glyph)
        self._relayout()
        if self._overflowing():
            # The page is full: celebrate, clear it, and start fresh with this glyph.
            self.page.backspace()
            self.new_page(celebrate=True)
            self.page.insert(glyph)
            self._relayout()
        self._sparkle(glyph)

    def _backspace(self) -> None:
        glyph = self.page.backspace()
        self._relayout()
        if glyph is not None:
            self.app.sounds.play("backspace")
            if glyph.x is not None:
                self.app.effects.sparkle(glyph.x + self.app.style.measure(glyph) / 2,
                                         glyph.y + self.app.style.pivot_y(), glyph.color, count=8, speed=160)

    def _say_word(self) -> None:
        word = self.page.word_before_cursor()
        if len(word) >= 2:
            self.app.say(word.lower())  # lowercase so "CAT" is read as a word, not spelled

    def _sparkle(self, glyph: Glyph) -> None:
        """Burst from where the new glyph lands (the cursor may have wrapped to the next row)."""
        index = self.page.index - 1
        line = self.layout.lines[self.layout.line_of(self.page.para, index)]
        style = self.app.style
        self.app.effects.sparkle(line.x_at(index) + style.measure(glyph) / 2, line.top + style.pivot_y(), glyph.color)

    def new_page(self, celebrate: bool = False) -> None:
        """Send everything on the page tumbling away and start with a clean screen."""
        app = self.app
        style = app.style
        for glyph in self.page.glyphs():
            if glyph.x is not None and not glyph.is_space:
                surface = style.glyph_surface(glyph)
                app.effects.fling(surface, glyph.x + surface.get_width() / 2, glyph.y + style.pivot_y())
        if celebrate:
            app.effects.confetti(style.width, RAINBOW)  # celebrations are always rainbow
            app.sounds.play("cheer")
            app.say("Great job!")
        self.page = Page()
        self._relayout()

    def recolor(self) -> None:
        for glyph in self.page.glyphs():
            glyph.color = self.app.style.next_color()

    def resize(self) -> None:
        """The text size or window changed: re-flow, starting over if it no longer fits."""
        self._relayout()
        if self._overflowing():
            self.new_page()

    # --- layout --------------------------------------------------------------

    @property
    def layout(self) -> Layout:
        if self._layout is None:
            style = self.app.style
            self._layout = layout(self.page, style.measure, style.max_line_width,
                                  style.line_height, style.paragraph_gap, style.center)
        return self._layout

    def _relayout(self) -> None:
        self._layout = None

    def _overflowing(self) -> bool:
        return self.layout.height > self.app.style.max_text_height

    # --- frame ---------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.blink += dt
        glide = 1 - math.exp(-GLIDE_RATE * dt)
        for line in self.layout.lines:
            for k, glyph in enumerate(self.page.paragraphs[line.para][line.start:line.end]):
                x, y = line.left + line.offsets[k], line.top
                if glyph.x is None:
                    glyph.x, glyph.y = x, y
                else:
                    glyph.x += (x - glyph.x) * glide
                    glyph.y += (y - glyph.y) * glide
        x, y = self.layout.cursor_position(self.page.para, self.page.index)
        if self.cursor_x is None:
            self.cursor_x, self.cursor_y = x, y
        else:
            snap = 1 - math.exp(-GLIDE_RATE * 2 * dt)
            self.cursor_x += (x - self.cursor_x) * snap
            self.cursor_y += (y - self.cursor_y) * snap

    def draw(self, surface: pygame.Surface) -> None:
        style = self.app.style
        pivot_y = style.pivot_y()
        for glyph in self.page.glyphs():
            if glyph.x is None or glyph.is_space:
                continue
            image = style.glyph_surface(glyph)
            age = self.app.now - glyph.born
            if age < POP_SECONDS:
                scale = pop_scale(age / POP_SECONDS)
                w, h = image.get_size()
                scaled = pygame.transform.smoothscale(image, (max(1, round(w * scale)), max(1, round(h * scale))))
                surface.blit(scaled, (glyph.x + w / 2 * (1 - scale), glyph.y + pivot_y * (1 - scale)))
            else:
                surface.blit(image, (glyph.x, glyph.y))

        # The blinking light-blue cursor: solid while typing, blinking when idle.
        if self.blink < 0.6 or (self.blink // BLINK_SECONDS) % 2 == 0:
            width = max(4, style.size // 12)
            height = style.cap_height * 1.35
            top = self.cursor_y + style.baseline - style.cap_height * 1.2
            rect = pygame.Rect(round(self.cursor_x - width / 2), round(top), width, round(height))
            pygame.draw.rect(surface, LIGHT_BLUE, rect, border_radius=width // 2)
