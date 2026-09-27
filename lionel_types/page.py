"""The text on screen: paragraphs of glyphs, a cursor, and a centered, word-wrapped layout.

Pure Python (no pygame) so it is easy to test. Widths come from a ``measure`` callback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int]


@dataclass(eq=False)
class Glyph:
    """One thing typed: a character, or a key name drawn as a little keycap."""

    text: str
    color: Color
    is_label: bool = False
    born: float = 0.0
    # Where the glyph is drawn right now; it glides toward its spot in the layout.
    x: Optional[float] = None
    y: Optional[float] = None

    @property
    def is_space(self) -> bool:
        return not self.is_label and self.text == " "

    @property
    def is_letter(self) -> bool:
        return not self.is_label and self.text.isalpha()


class Page:
    """Paragraphs of glyphs plus a cursor. Enter starts a new paragraph."""

    def __init__(self) -> None:
        self.paragraphs: List[List[Glyph]] = [[]]
        self.para = 0
        self.index = 0

    def is_empty(self) -> bool:
        return len(self.paragraphs) == 1 and not self.paragraphs[0]

    def glyphs(self) -> Iterator[Glyph]:
        for paragraph in self.paragraphs:
            yield from paragraph

    def set_cursor(self, para: int, index: int) -> None:
        self.para = para
        self.index = index

    def insert(self, glyph: Glyph) -> None:
        self.paragraphs[self.para].insert(self.index, glyph)
        self.index += 1

    def new_paragraph(self) -> None:
        current = self.paragraphs[self.para]
        tail = current[self.index:]
        del current[self.index:]
        self.paragraphs.insert(self.para + 1, tail)
        self.para += 1
        self.index = 0

    def backspace(self) -> Optional[Glyph]:
        """Delete before the cursor, joining paragraphs at a paragraph start.

        Returns the deleted glyph, if a glyph (not a paragraph break) was deleted.
        """
        if self.index > 0:
            self.index -= 1
            return self.paragraphs[self.para].pop(self.index)
        if self.para > 0:
            previous = self.paragraphs[self.para - 1]
            self.index = len(previous)
            previous.extend(self.paragraphs.pop(self.para))
            self.para -= 1
        return None

    def move_left(self) -> None:
        if self.index > 0:
            self.index -= 1
        elif self.para > 0:
            self.para -= 1
            self.index = len(self.paragraphs[self.para])

    def move_right(self) -> None:
        if self.index < len(self.paragraphs[self.para]):
            self.index += 1
        elif self.para < len(self.paragraphs) - 1:
            self.para += 1
            self.index = 0

    def move_to_end(self) -> None:
        self.para = len(self.paragraphs) - 1
        self.index = len(self.paragraphs[self.para])

    def word_before_cursor(self) -> str:
        letters = []
        for glyph in reversed(self.paragraphs[self.para][: self.index]):
            if not glyph.is_letter:
                break
            letters.append(glyph.text)
        return "".join(reversed(letters))


@dataclass
class Line:
    """One row on screen: glyphs ``start:end`` of paragraph ``para``."""

    para: int
    start: int
    end: int
    is_last: bool  # the last row of its paragraph
    left: float
    top: float
    offsets: List[float]  # x of each glyph boundary from ``left``; len == end - start + 1

    @property
    def width(self) -> float:
        return self.offsets[-1]

    def x_at(self, index: int) -> float:
        return self.left + self.offsets[index - self.start]

    def holds(self, para: int, index: int) -> bool:
        """Whether the cursor position sits on this row.

        The position between two wrapped rows belongs to the lower row.
        """
        if para != self.para:
            return False
        return self.start <= index < self.end or (self.is_last and index == self.end)


@dataclass
class Layout:
    lines: List[Line]
    height: float

    def line_of(self, para: int, index: int) -> int:
        for i, line in enumerate(self.lines):
            if line.holds(para, index):
                return i
        raise ValueError(f"cursor {para}:{index} is not on the page")

    def cursor_position(self, para: int, index: int) -> Tuple[float, float]:
        """Screen x of the cursor and the top of its row."""
        line = self.lines[self.line_of(para, index)]
        return line.x_at(index), line.top


def wrap(widths: Sequence[float], spaces: Sequence[bool], max_width: float) -> List[Tuple[int, int]]:
    """Split a paragraph into rows no wider than ``max_width``.

    Breaks after the last space that fits; a word too long for a row is split.
    Always returns at least one row, so an empty paragraph still gets a line.
    """
    rows = []
    start = 0
    x = 0.0
    last_space = -1
    i = 0
    while i < len(widths):
        if x + widths[i] > max_width and i > start:
            end = last_space + 1 if last_space >= start else i
            rows.append((start, end))
            start = end
            x = sum(widths[start:i])
            last_space = -1
            continue
        if spaces[i]:
            last_space = i
        x += widths[i]
        i += 1
    rows.append((start, len(widths)))
    return rows


def layout(
    page: Page,
    measure: Callable[[Glyph], float],
    max_width: float,
    line_height: float,
    paragraph_gap: float,
    center: Tuple[float, float],
) -> Layout:
    """Center every row horizontally and the whole block vertically."""
    center_x, center_y = center
    lines = []
    y = 0.0
    for p, glyphs in enumerate(page.paragraphs):
        if p:
            y += paragraph_gap
        widths = [measure(g) for g in glyphs]
        rows = wrap(widths, [g.is_space for g in glyphs], max_width)
        for r, (start, end) in enumerate(rows):
            offsets = [0.0]
            for w in widths[start:end]:
                offsets.append(offsets[-1] + w)
            lines.append(Line(p, start, end, r == len(rows) - 1, center_x - offsets[-1] / 2, y, offsets))
            y += line_height
    top = center_y - y / 2
    for line in lines:
        line.top += top
    return Layout(lines, y)


def move_vertically(page: Page, lay: Layout, direction: int) -> None:
    """Move the cursor to the row above/below, to the spot closest to where it is now."""
    current = lay.line_of(page.para, page.index)
    x = lay.lines[current].x_at(page.index)
    target = current + direction
    if target < 0:
        page.set_cursor(0, 0)
        return
    if target >= len(lay.lines):
        page.move_to_end()
        return
    line = lay.lines[target]
    last = line.end if line.is_last else max(line.start, line.end - 1)
    best = min(range(line.start, last + 1), key=lambda k: abs(line.x_at(k) - x))
    page.set_cursor(line.para, best)
