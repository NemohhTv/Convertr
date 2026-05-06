"""Convenience entry point for running from a source checkout.

Usage:
    python app.py

This just delegates to ``convertr.app.main`` after putting ``src/`` on
``sys.path``. PyInstaller uses this file as its entry script.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make ``src/`` importable when running from a checkout.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from convertr.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
