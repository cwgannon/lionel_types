"""Keep little hands inside the app: block the OS shortcuts that would switch away or close it.

Each platform module does what its OS allows. ``Lockdown`` itself blocks nothing and
is used on other platforms and in windowed mode.
"""

from __future__ import annotations

import sys
from typing import Hashable, List, Tuple

from ..keys import Key

# A key the OS would have swallowed, handed to the app instead: (key id, is down, key).
ForwardedKey = Tuple[Hashable, bool, Key]


class Lockdown:
    def __init__(self) -> None:
        self.notes: List[str] = []  # what is (or is not) protected, shown in the parent menu

    def prepare(self) -> None:
        """Called before the window is created."""

    def engage(self, window_id: int) -> None:
        """Called once the full-screen window exists."""

    def poll(self) -> List[ForwardedKey]:
        """Keys intercepted since the last call, so the app can still show them."""
        return []

    def release(self) -> None:
        """Undo everything. Safe to call more than once."""


def create(enabled: bool) -> Lockdown:
    if enabled and sys.platform == "win32":
        from .windows import WindowsLockdown

        return WindowsLockdown()
    if enabled and sys.platform == "darwin":
        from .macos import MacLockdown

        return MacLockdown()
    lockdown = Lockdown()
    if enabled:
        lockdown.notes.append("Keyboard lock is not available on this system.")
    return lockdown
