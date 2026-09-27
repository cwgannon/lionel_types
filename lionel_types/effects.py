"""Sparkles, fireworks, confetti, and letters tumbling off a finished page."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

import pygame

Color = Tuple[int, int, int]

GRAVITY = 900.0  # pixels per second squared
MAX_PARTICLES = 2500


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "ttl", "size", "color", "shape", "angle", "spin", "gravity", "drag")

    def __init__(self, x, y, vx, vy, ttl, size, color, shape, gravity=0.0, drag=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.age = 0.0
        self.ttl = ttl
        self.size = size
        self.color = color
        self.shape = shape  # "dot", "star" or "confetti"
        self.angle = random.uniform(0, math.tau)
        self.spin = random.uniform(-8, 8)
        self.gravity = gravity
        self.drag = drag  # fraction of speed lost per second


class Flyer:
    """A whole glyph image flung off the screen, spinning."""

    __slots__ = ("surface", "x", "y", "vx", "vy", "angle", "spin")

    def __init__(self, surface: pygame.Surface, x: float, y: float) -> None:
        self.surface = surface
        self.x, self.y = x, y
        self.vx = random.uniform(-260, 260)
        self.vy = random.uniform(-650, -250)
        self.angle = 0.0
        self.spin = random.uniform(-280, 280)


class Effects:
    def __init__(self) -> None:
        self.particles: List[Particle] = []
        self.flyers: List[Flyer] = []

    def _add(self, particle: Particle) -> None:
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)

    def sparkle(self, x: float, y: float, color: Color, count: int = 12, speed: float = 240, size: float = 7) -> None:
        """A small puff of stars, e.g. when a letter appears."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            v = speed * random.uniform(0.4, 1.0)
            self._add(Particle(x, y, math.cos(angle) * v, math.sin(angle) * v,
                               random.uniform(0.35, 0.7), size * random.uniform(0.6, 1.2), color, "star", drag=2.5))

    def firework(self, x: float, y: float, colors: Sequence[Color], count: int = 70, speed: float = 520) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            v = speed * random.uniform(0.3, 1.0)
            self._add(Particle(x, y, math.cos(angle) * v, math.sin(angle) * v,
                               random.uniform(0.7, 1.4), random.uniform(4, 9), random.choice(colors),
                               random.choice(("dot", "star")), gravity=GRAVITY * 0.35, drag=1.2))

    def confetti(self, width: float, colors: Sequence[Color], count: int = 180) -> None:
        """Confetti raining down from above the top of the screen."""
        for _ in range(count):
            self._add(Particle(random.uniform(0, width), random.uniform(-400, -10),
                               random.uniform(-80, 80), random.uniform(150, 420),
                               random.uniform(2.2, 3.4), random.uniform(8, 16), random.choice(colors),
                               "confetti", gravity=GRAVITY * 0.15))

    def trail(self, x: float, y: float, color: Color) -> None:
        """Glitter left behind by the moving mouse."""
        self._add(Particle(x + random.uniform(-6, 6), y + random.uniform(-6, 6),
                           random.uniform(-30, 30), random.uniform(-30, 30),
                           random.uniform(0.4, 0.8), random.uniform(3, 7), color, "star", gravity=GRAVITY * 0.1, drag=1.0))

    def fling(self, surface: pygame.Surface, x: float, y: float) -> None:
        if len(self.flyers) < 400:
            self.flyers.append(Flyer(surface, x, y))

    def clear(self) -> None:
        self.particles.clear()
        self.flyers.clear()

    def update(self, dt: float, screen_height: float) -> None:
        alive = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue
            slow = max(0.0, 1.0 - p.drag * dt)
            p.vx *= slow
            p.vy = p.vy * slow + p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.angle += p.spin * dt
            alive.append(p)
        self.particles = alive

        flying = []
        for f in self.flyers:
            f.vy += GRAVITY * dt
            f.x += f.vx * dt
            f.y += f.vy * dt
            f.angle += f.spin * dt
            if f.y < screen_height + 200:
                flying.append(f)
        self.flyers = flying

    def draw(self, surface: pygame.Surface) -> None:
        for f in self.flyers:
            image = pygame.transform.rotate(f.surface, f.angle)
            surface.blit(image, image.get_rect(center=(int(f.x), int(f.y))))
        for p in self.particles:
            # Twinkle out by shrinking, not darkening: a darkened sparkle over a letter looks like a smudge.
            size = p.size * min(1.0, (1.0 - p.age / p.ttl) / 0.4)
            if size < 0.5:
                continue
            if p.shape == "dot":
                pygame.draw.circle(surface, p.color, (int(p.x), int(p.y)), max(1, round(size)))
            elif p.shape == "star":
                pygame.draw.polygon(surface, p.color, _star(p.x, p.y, size, p.angle))
            else:
                pygame.draw.polygon(surface, p.color, _rect(p.x, p.y, size, size * 0.55, p.angle))


def _star(x: float, y: float, r: float, angle: float) -> List[Tuple[float, float]]:
    """A four-pointed twinkle."""
    points = []
    for k in range(8):
        radius = r if k % 2 == 0 else r * 0.32
        a = angle + k * math.pi / 4
        points.append((x + math.cos(a) * radius, y + math.sin(a) * radius))
    return points


def _rect(x: float, y: float, w: float, h: float, angle: float) -> List[Tuple[float, float]]:
    c, s = math.cos(angle), math.sin(angle)
    corners = ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))
    # Squash with the spin so confetti looks like it flutters.
    flutter = abs(math.cos(angle * 1.7)) * 0.8 + 0.2
    return [(x + cx * c - cy * flutter * s, y + cx * s + cy * flutter * c) for cx, cy in corners]


def pick(colors: Sequence[Color], avoid: Optional[Color] = None) -> Color:
    choices = [c for c in colors if c != avoid] or list(colors)
    return random.choice(choices)
