"""Find the letter: a big letter appears, the voice asks for it, and the kid hunts for the key."""

from __future__ import annotations

import math
import random
import string
from typing import TYPE_CHECKING, Dict, List, Tuple

import pygame

from . import keys
from .style import DIM, RAINBOW, pop_scale

if TYPE_CHECKING:
    from .app import App

CELEBRATE_SECONDS = 1.6
REMIND_SECONDS = 8.0  # ask again if nobody has found it for a while
STARS_PER_ROUND = 10


class FindTheLetter:
    def __init__(self, app: "App") -> None:
        self.app = app
        self.stars = 0
        self.target = ""
        self.color = app.style.next_color()
        self.shown_at = 0.0
        self.celebrating = 0.0  # seconds left in the current celebration
        self.wiggle = 0.0  # seconds left in a "not that one" wiggle
        self.since_prompt = 0.0
        self.recent: List[str] = []
        self._rendered: Dict[Tuple[str, Tuple[int, int, int], int], pygame.Surface] = {}
        self.next_target()

    def next_target(self) -> None:
        choices = [c for c in string.ascii_lowercase if c not in self.recent]
        self.target = random.choice(choices)
        self.recent = (self.recent + [self.target])[-5:]
        self.color = self.app.style.next_color()
        self.shown_at = self.app.now
        self.prompt()

    def prompt(self) -> None:
        self.since_prompt = 0.0
        self.app.say(f"Find the letter {self.target.upper()}.")

    @property
    def shown_text(self) -> str:
        return keys.apply_case(self.target, self.app.settings.letter_case)

    def key_down(self, key: keys.Key) -> None:
        app = self.app
        if self.celebrating > 0:
            return
        if key.action != keys.CHAR or key.text == " ":
            if key.action in (keys.LABEL, keys.CHAR):
                app.sounds.play("label")
            return
        if key.text.lower() == self.target:
            self.found()
        else:
            app.sounds.note_for(key.text)
            app.say(key.speech)
            self.wiggle = 0.35

    def found(self) -> None:
        app = self.app
        self.celebrating = CELEBRATE_SECONDS
        self.stars += 1
        style = app.style
        app.effects.firework(style.width / 2, style.height / 2, RAINBOW)
        app.sounds.play("cheer")
        if self.stars >= STARS_PER_ROUND:
            app.effects.confetti(style.width, RAINBOW)
            app.say(f"{self.target.upper()}! Wow, {STARS_PER_ROUND} stars!")
        else:
            app.say(f"Yes! {self.target.upper()}!")

    def recolor(self) -> None:
        self.color = self.app.style.next_color()

    def resize(self) -> None:
        pass

    def update(self, dt: float) -> None:
        self.wiggle = max(0.0, self.wiggle - dt)
        if self.celebrating > 0:
            self.celebrating -= dt
            if self.celebrating <= 0:
                if self.stars >= STARS_PER_ROUND:
                    self.stars = 0
                self.next_target()
            return
        self.since_prompt += dt
        if self.since_prompt > REMIND_SECONDS:
            self.prompt()

    def draw(self, surface: pygame.Surface) -> None:
        style = self.app.style
        now = self.app.now
        cx, cy = style.width / 2, style.height * 0.52

        caption = style.ui_font.render("Find the letter", True, DIM)
        surface.blit(caption, caption.get_rect(midtop=(cx, style.height * 0.1)))

        letter = self._letter_image()
        scale = pop_scale((now - self.shown_at) / 0.35)
        if self.celebrating > 0:
            scale *= 1 + 0.25 * math.sin((CELEBRATE_SECONDS - self.celebrating) * math.pi / CELEBRATE_SECONDS)
        else:
            scale *= 1 + 0.03 * math.sin(now * 3)  # a gentle breathing bob
        if abs(scale - 1) > 0.005:
            letter = pygame.transform.smoothscale(
                letter, (max(1, round(letter.get_width() * scale)), max(1, round(letter.get_height() * scale))))
        shake = math.sin(self.wiggle * 45) * style.height * 0.03 * (self.wiggle / 0.35)
        surface.blit(letter, letter.get_rect(center=(cx + shake, cy)))

        self._draw_stars(surface)

    def _letter_image(self) -> pygame.Surface:
        """The target letter cropped to its ink, so "a" and "J" both sit in the middle."""
        style = self.app.style
        key = (self.shown_text, self.color, style.hero_font.get_height())
        image = self._rendered.get(key)
        if image is None:
            rendered = style.hero_font.render(self.shown_text, True, self.color)
            image = rendered.subsurface(rendered.get_bounding_rect()).copy()
            self._rendered = {key: image}  # only the current letter is ever needed
        return image

    def _draw_stars(self, surface: pygame.Surface) -> None:
        style = self.app.style
        r = style.height * 0.028
        gap = r * 2.8
        left = style.width / 2 - gap * (STARS_PER_ROUND - 1) / 2
        y = style.height * 0.9
        for i in range(STARS_PER_ROUND):
            filled = i < self.stars
            color = (255, 214, 64) if filled else (50, 56, 70)
            points = _star_points(left + i * gap, y, r * (1.15 if filled else 1.0))
            pygame.draw.polygon(surface, color, points)


def _star_points(x: float, y: float, r: float) -> List[tuple]:
    points = []
    for k in range(10):
        radius = r if k % 2 == 0 else r * 0.45
        a = -math.pi / 2 + k * math.pi / 5
        points.append((x + math.cos(a) * radius, y + math.sin(a) * radius))
    return points
