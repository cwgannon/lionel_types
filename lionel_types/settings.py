"""Parent-adjustable settings, remembered between runs."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

CHOICES = {
    "letter_case": ("upper", "lower", "as_typed"),
    "theme": ("rainbow", "classic"),
    "text_size": ("big", "bigger", "biggest"),
    "mode": ("free", "find"),
}


@dataclass
class Settings:
    sound: bool = True
    voice: bool = True
    letter_case: str = "upper"  # capitals match the letters printed on the keys
    theme: str = "rainbow"
    text_size: str = "big"
    mode: str = "free"

    @classmethod
    def from_dict(cls, data: object) -> "Settings":
        """Build settings from saved JSON, ignoring anything unknown or invalid."""
        settings = cls()
        if not isinstance(data, dict):
            return settings
        for field in fields(cls):
            value = data.get(field.name)
            if field.name in CHOICES:
                if value in CHOICES[field.name]:
                    setattr(settings, field.name, value)
            elif isinstance(value, bool):
                setattr(settings, field.name, value)
        return settings

    def cycle(self, name: str) -> None:
        """Advance a multiple-choice setting to its next option."""
        options = CHOICES[name]
        setattr(self, name, options[(options.index(getattr(self, name)) + 1) % len(options)])


def default_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "LionelTypes" / "settings.json"


def load(path: Optional[Path] = None) -> Settings:
    path = path or default_path()
    try:
        return Settings.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Settings()


def save(settings: Settings, path: Optional[Path] = None) -> None:
    path = path or default_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    except OSError:
        pass  # Remembering settings is a nicety; never interrupt a kid over it.
