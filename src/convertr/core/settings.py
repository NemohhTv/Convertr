"""Settings storage.

Simple JSON-backed settings with sensible defaults. Settings include the
default output folder, conversion mode, theme, and a few toggles.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import settings_file


@dataclass
class Settings:
    output_folder: str = ""  # empty = same folder as input
    mode: str = "smart_fast"  # or "max_compat"
    overwrite: bool = False
    auto_check_updates: bool = True
    minimize_to_tray: bool = True
    notify_on_complete: bool = True
    last_input_folder: str = ""

    @classmethod
    def load(cls) -> "Settings":
        path: Path = settings_file()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        # Drop unknown keys so old settings files don't crash newer builds.
        valid = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in valid}
        return cls(**clean)

    def save(self) -> None:
        path = settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


@dataclass
class HistoryEntry:
    source: str
    output: str
    target_format: str
    mode_used: str  # "remux" or "encode"
    duration_seconds: float
    timestamp: str  # ISO 8601


def load_history() -> list[HistoryEntry]:
    from .paths import history_file
    path = history_file()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out: list[HistoryEntry] = []
    for item in raw[-200:]:  # cap so the file can't grow forever
        try:
            out.append(HistoryEntry(**item))
        except TypeError:
            continue
    return out


def append_history(entry: HistoryEntry) -> None:
    from .paths import history_file
    existing = load_history()
    existing.append(entry)
    existing = existing[-200:]
    path = history_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(e) for e in existing], indent=2), encoding="utf-8"
    )


def clear_history() -> None:
    from .paths import history_file
    p = history_file()
    if p.exists():
        p.unlink()
