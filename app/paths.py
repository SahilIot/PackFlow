"""Filesystem locations (user data directory and bundled resources)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "PackFlow"
LEGACY_APP_NAME = "MachinePackingPrint"


def legacy_data_dir() -> Path:
    """Folder used by versions before the rename (its database is copied, never moved or deleted)."""
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / LEGACY_APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / LEGACY_APP_NAME


def data_dir() -> Path:
    """Per-user writable data directory (never inside the executable folder).

    Windows: %APPDATA%\\PackFlow. Override with MPP_DATA_DIR.
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


def adopt_legacy_database() -> bool:
    """First start of PackFlow: if an older version's database exists and there is none yet, COPY it over.

    The original file is left untouched. Returns True when a copy was made.
    """
    import shutil
    new = db_path()
    old = legacy_data_dir() / "machine_packing_print.db"
    if new.exists() or old.resolve() == new.resolve() or not old.exists():
        return False
    try:
        shutil.copy2(old, new)
    except OSError:
        return False
    return True


def resource_path(*parts: str) -> Path:
    """Path to a bundled read-only resource (works from source and PyInstaller)."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root.joinpath(*parts)
