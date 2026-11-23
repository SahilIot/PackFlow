"""Filesystem locations (user data directory and bundled resources)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "MachinePackingPrint"


def data_dir() -> Path:
    """Per-user writable data directory (never inside the executable folder).

    Windows: %APPDATA%\\MachinePackingPrint. Override with MPP_DATA_DIR.
    """
    override = os.environ.get("MPP_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "machine_packing_print.db"


def resource_path(*parts: str) -> Path:
    """Path to a bundled read-only resource (works from source and PyInstaller)."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root.joinpath(*parts)
