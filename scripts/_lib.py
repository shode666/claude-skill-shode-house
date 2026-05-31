"""Shared helpers for shode-house maintainer Python scripts.

Cross-platform (Mac/Linux/Windows). Stdlib only.
Python 3.9+ required — fails with clear message if older.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 9):
    sys.stderr.write(
        f"ERROR: Python 3.9+ required, you have {sys.version_info.major}.{sys.version_info.minor}\n"
        "Install Python 3.9+:\n"
        "  macOS:   https://www.python.org/downloads/macos/  (or `brew install python@3.12`)\n"
        "  Linux:   apt/yum/dnf install python3.11 (varies by distro)\n"
        "  Windows: https://www.python.org/downloads/windows/  (or Microsoft Store)\n"
    )
    sys.exit(1)

from pathlib import Path


def repo_root() -> Path:
    """Return the shode-house repo root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def red(msg: str) -> None:
    print(f"\033[0;31m{msg}\033[0m")


def green(msg: str) -> None:
    print(f"\033[0;32m{msg}\033[0m")


def yellow(msg: str) -> None:
    print(f"\033[0;33m{msg}\033[0m")
