"""Sounds, synthesized on the fly so there are no audio files to ship.

Every key plays a note from a pentatonic scale laid out across the keyboard
(left to right, bottom row to top row goes up in pitch), so mashing always
sounds pleasant and each key always sounds the same.
"""

from __future__ import annotations

import math
import threading
from array import array
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

MIDDLE_C = 261.63
PENTATONIC = (0, 2, 4, 7, 9)  # semitones: C D E G A

# Physical key rows, bottom to top (US layout), and what Shift turns keys into.
ROWS = ("zxcvbnm,./", "asdfghjkl;'", "qwertyuiop[]\\", "`1234567890-=")
UNSHIFTED = dict(zip('~!@#$%^&*()_+{}|:"<>?', "`1234567890-=[]\\;',./"))


def pentatonic(step: int) -> float:
    """Frequency of the ``step``-th note of C-major pentatonic, starting at middle C."""
    octave, degree = divmod(step, len(PENTATONIC))
    return MIDDLE_C * 2 ** (octave + PENTATONIC[degree] / 12)


def step_for_char(ch: str) -> int:
    """Which note a typed character plays: its row plus its position along the row."""
    ch = ch.lower()
    ch = UNSHIFTED.get(ch, ch)
    for row, keys in enumerate(ROWS):
        column = keys.find(ch)
        if column >= 0:
            return row + column
    return sum(map(ord, ch)) % 10  # anything else still gets a steady note


Samples = List[float]


def tone(freq: float, duration: float, rate: int, decay: float = 7.0,
         partials: Sequence[Tuple[float, float]] = ((1, 1.0), (2, 0.2), (3.9, 0.1))) -> Samples:
    """A plucked, marimba-like note: a few sine partials with a fast attack and exponential decay."""
    n = int(duration * rate)
    attack = int(0.004 * rate) or 1
    steps = [2 * math.pi * freq * mult / rate for mult, _ in partials]
    amps = [amp for _, amp in partials]
    fall = math.exp(-decay / rate)
    out = [0.0] * n
    env = 1.0
    for i in range(n):
        s = 0.0
        for step, amp in zip(steps, amps):
            s += amp * math.sin(step * i)
        out[i] = s * env * min(1.0, i / attack)
        env *= fall
    return out


def sweep(f0: float, f1: float, duration: float, rate: int, decay: float = 4.0) -> Samples:
    """A sine that glides from ``f0`` to ``f1``: boings, bloops and pops."""
    n = int(duration * rate)
    attack = int(0.004 * rate) or 1
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += 2 * math.pi * (f0 * (f1 / f0) ** t) / rate
        out[i] = (math.sin(phase) + 0.25 * math.sin(2 * phase)) * math.exp(-decay * t) * min(1.0, i / attack)
    return out


def arpeggio(steps: Sequence[int], gap: float, rate: int, duration: float = 0.5) -> Samples:
    """Notes started ``gap`` seconds apart, ringing together."""
    offset = int(gap * rate)
    out = [0.0] * (offset * (len(steps) - 1) + int(duration * rate))
    for k, step in enumerate(steps):
        for i, s in enumerate(tone(pentatonic(step), duration, rate, decay=5.0)):
            out[k * offset + i] += s
    return out


def to_pcm(samples: Samples, volume: float, channels: int) -> bytes:
    """Normalize to ``volume`` (0..1), fade the tail to avoid clicks, and pack as signed 16-bit."""
    n = len(samples)
    peak = max((abs(s) for s in samples), default=0.0) or 1.0
    scale = 32767 * volume / peak
    fade = min(n, 256)
    mono = array("h", (int(s * scale * min(1.0, (n - i) / fade)) for i, s in enumerate(samples)))
    if channels == 1:
        return mono.tobytes()
    interleaved = array("h", bytes(2 * n * channels))
    for c in range(channels):
        interleaved[c::channels] = mono
    return interleaved.tobytes()


NOTE_COUNT = 16  # step_for_char never goes higher
SOUND_NAMES = tuple(f"note{i}" for i in range(NOTE_COUNT)) + ("label", "space", "enter", "backspace", "pop", "cheer")


def synthesize(name: str, rate: int) -> Samples:
    if name.startswith("note"):
        return tone(pentatonic(int(name[4:])), 0.55, rate)
    if name == "label":  # a special key: a springy boing
        return sweep(260, 620, 0.22, rate, decay=2.5)
    if name == "space":
        return tone(pentatonic(10), 0.08, rate, decay=40.0)
    if name == "enter":
        return arpeggio((5, 7, 9), 0.07, rate, 0.4)
    if name == "backspace":
        return sweep(620, 220, 0.16, rate, decay=3.0)
    if name == "pop":  # mouse clicks
        return sweep(900, 300, 0.07, rate, decay=5.0)
    if name == "cheer":
        return arpeggio((5, 7, 9, 10, 12, 15), 0.075, rate, 0.7)
    raise ValueError(f"unknown sound {name!r}")


class Sounds:
    """Plays synthesized sounds; quietly does nothing if there is no audio device.

    Synthesis is slow-ish pure Python, so everything is pre-rendered on a
    background thread at startup rather than on a kid's first key press.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.muted = False
        self._pcm: Dict[str, bytes] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._format: Optional[Tuple[int, int]] = None
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            freq, size, channels = pygame.mixer.get_init()
        except pygame.error:
            return
        if size != -16:
            return
        pygame.mixer.set_num_channels(24)
        self._format = (freq, channels)
        threading.Thread(target=self._prerender, name="sound-synth", daemon=True).start()

    @property
    def available(self) -> bool:
        return self._format is not None

    def note_for(self, ch: str) -> None:
        self.play(f"note{step_for_char(ch)}")

    def play(self, name: str) -> None:
        if self.muted or self._format is None:
            return
        sound = self._sounds.get(name)
        if sound is None:
            pcm = self._pcm.get(name) or self._render(name)
            sound = self._sounds[name] = pygame.mixer.Sound(buffer=pcm)
        sound.play()

    def _render(self, name: str) -> bytes:
        rate, channels = self._format
        pcm = to_pcm(synthesize(name, rate), 0.45 if name.startswith("note") else 0.5, channels)
        self._pcm[name] = pcm
        return pcm

    def _prerender(self) -> None:
        for name in SOUND_NAMES:
            if name not in self._pcm:
                self._render(name)
