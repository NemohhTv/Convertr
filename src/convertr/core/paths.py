"""Filesystem path helpers.

Centralizes where Convertr looks for resources, user data, settings, and
the bundled FFmpeg install. Works whether running from source or from a
PyInstaller-frozen .exe.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def resource_path(*parts: str) -> Path:
    """Return absolute path to a bundled resource.

    When frozen, PyInstaller extracts data files to ``sys._MEIPASS``.
    When running from source, resources live alongside the package.
    """
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        # convertr/core/paths.py -> convertr/
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def user_data_dir() -> Path:
    """Per-user writable directory for settings, history, and FFmpeg.

    On Windows this is ``%LOCALAPPDATA%\\Convertr``.
    Falls back to ``~/.convertr`` on other platforms (dev/testing).
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = Path(base) / "Convertr"
    else:
        path = Path.home() / ".convertr"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return user_data_dir() / "settings.json"


def history_file() -> Path:
    return user_data_dir() / "history.json"


def ffmpeg_dir() -> Path:
    """Where Convertr installs its private copy of FFmpeg."""
    path = user_data_dir() / "ffmpeg"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ffmpeg_binary() -> Path:
    """Expected path of the ffmpeg executable inside the private install."""
    name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    return ffmpeg_dir() / "bin" / name


def ffprobe_binary() -> Path:
    name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    return ffmpeg_dir() / "bin" / name
