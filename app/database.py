"""Local SQLite storage: instructions, templates and settings for this computer.

The file lives in %APPDATA%\\PackFlow and is created on first start. Schema upgrades are versioned (PRAGMA user_version),
make a .bak-vN copy first and never erase data. A damaged file is set aside, not deleted.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

from .errors import DatabaseError
from .models import AutoLayoutParams, Document, Instruction, Template
from .symbols import SYMBOLS

RED, BLUE, GREEN, ORANGE, BLACK = "#d00000", "#0057b8", "#1a8f3c", "#f57c00", "#000000"
DEFAULT_INSTRUCTIONS: list[tuple[str, str, float, str, str, str]] = [
    # name, symbol, max font size (pt; text shrinks to fit), text colour, symbol colour, border colour
    ("FRONT", "", 110, BLUE, BLACK, BLUE),
    ("TOP", "arrow_up", 90, BLACK, BLUE, BLACK),
    ("HANDLE WITH CARE", "handle_with_care", 60, RED, RED, RED),
    ("FRAGILE", "fragile", 80, RED, RED, RED),
    ("DO NOT STACK", "do_not_stack", 60, RED, RED, RED),
    ("THIS SIDE UP", "this_side_up", 60, BLACK, BLUE, BLACK),
    ("KEEP DRY", "keep_dry", 80, BLUE, BLUE, BLUE),
    ("HEAVY MATERIAL", "heavy_material", 60, BLACK, ORANGE, BLACK),
    ("LIFT HERE", "lift_here", 80, BLACK, BLACK, BLACK),
    ("CENTER OF GRAVITY", "center_of_gravity", 50, BLACK, BLACK, BLACK),
]

DEFAULT_TEMPLATES: dict[str, list[str]] = {
    "Standard Machine Packing": ["FRONT", "TOP", "THIS SIDE UP", "HANDLE WITH CARE", "KEEP DRY", "FRAGILE"],
    "Export Packing": ["FRONT", "TOP", "THIS SIDE UP", "KEEP DRY", "HANDLE WITH CARE", "DO NOT STACK"],
    "Heavy Machine Packing": ["FRONT", "TOP", "HEAVY MATERIAL", "LIFT HERE", "CENTER OF GRAVITY", "DO NOT STACK"],
    "Fragile Machine Packing": ["FRONT", "TOP", "FRAGILE", "HANDLE WITH CARE", "THIS SIDE UP", "DO NOT STACK"],
    "Custom Packing": [],
}


def _migrate_v1(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            text TEXT NOT NULL DEFAULT '',
            symbol TEXT NOT NULL DEFAULT '',
            font_family TEXT NOT NULL DEFAULT 'Arial',
            font_pt REAL NOT NULL DEFAULT 72,
            bold INTEGER NOT NULL DEFAULT 1,
            italic INTEGER NOT NULL DEFAULT 0,
            align TEXT NOT NULL DEFAULT 'center',
            border_mm REAL NOT NULL DEFAULT 1.5,
            symbol_pos TEXT NOT NULL DEFAULT 'top',
            enabled INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            instruction_ids TEXT NOT NULL DEFAULT '[]',
            params TEXT NOT NULL DEFAULT '{}',
            document TEXT
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE symbol_config (
            key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
    """)


def _migrate_v2(db: sqlite3.Connection) -> None:
    """Colour support. Adds colour columns (default black / no background = the old look) and gives the
    built-in instructions their example colours - only if they still have the untouched defaults."""
    for col, default in (("text_color", "#000000"), ("symbol_color", "#000000"),
                         ("border_color", "#000000"), ("bg_color", "")):
        db.execute(f"ALTER TABLE instructions ADD COLUMN {col} TEXT NOT NULL DEFAULT '{default}'")
    for name, _sym, _pt, text, symbol, border in DEFAULT_INSTRUCTIONS:
        db.execute("UPDATE instructions SET text_color=?, symbol_color=?, border_color=? "
                   "WHERE name=? COLLATE NOCASE AND text_color='#000000' AND symbol_color='#000000' "
                   "AND border_color='#000000'", (text, symbol, border, name))


# Append future migrations here; never edit an existing one.
MIGRATIONS = [_migrate_v1, _migrate_v2]


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.recovered_from: Path | None = None  # set if a corrupt file was set aside
        self.conn = self._open()
        self._migrate()
        self._seed_defaults()

    # ---- connection / migration ----
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA user_version").fetchone()  # raises if not a database
        return conn

    def _open(self) -> sqlite3.Connection:
        try:
            return self._connect()
        except sqlite3.DatabaseError:
            # Corrupt or unreadable file: keep it for inspection and start fresh.
            bad = self.path.with_suffix(f".corrupt-{int(time.time())}")
            try:
                self.path.replace(bad)
            except OSError as exc:
                raise DatabaseError(f"Cannot open or recover database {self.path}: {exc}") from exc
            self.recovered_from = bad
            return self._connect()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version > len(MIGRATIONS):
            raise DatabaseError("The data file was created by a newer version of Machine Packing Print.")
        if version == len(MIGRATIONS):
            return
        if version > 0 and self.path.exists():
            shutil.copy2(self.path, self.path.with_suffix(f".bak-v{version}"))
        try:
            self.conn.execute("BEGIN")
            for i in range(version, len(MIGRATIONS)):
                MIGRATIONS[i](self.conn)
            self.conn.execute(f"PRAGMA user_version={len(MIGRATIONS)}")
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            raise DatabaseError(f"Database upgrade failed: {exc}") from exc

    def _seed_defaults(self) -> None:
        if self.get_setting("defaults_seeded") == "1":
            return
        with self.conn:
            for i, (name, symbol, pt, text_c, symbol_c, border_c) in enumerate(DEFAULT_INSTRUCTIONS):
                self.conn.execute(
                    "INSERT OR IGNORE INTO instructions(name,text,symbol,font_pt,sort_order,text_color,symbol_color,"
                    "border_color) VALUES(?,?,?,?,?,?,?,?)", (name, name, symbol, pt, i, text_c, symbol_c, border_c))
            for i, (key, (label, _)) in enumerate(SYMBOLS.items()):
                self.conn.execute("INSERT OR IGNORE INTO symbol_config(key,label,sort_order) VALUES(?,?,?)",
                                  (key, label, i))
            ids = {r["name"]: r["id"] for r in self.conn.execute("SELECT id,name FROM instructions")}
            for tname, names in DEFAULT_TEMPLATES.items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO templates(name,instruction_ids,params) VALUES(?,?,?)",
                    (tname, json.dumps([ids[n] for n in names if n in ids]),
                     json.dumps(AutoLayoutParams().to_dict())))
            self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('defaults_seeded','1')")

    def close(self) -> None:
        self.conn.close()

    # ---- settings ----
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: Any) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))

    # ---- instructions ----
    @staticmethod
    def _to_instruction(r: sqlite3.Row) -> Instruction:
        return Instruction(id=r["id"], name=r["name"], text=r["text"], symbol=r["symbol"],
                           font_family=r["font_family"], font_pt=r["font_pt"], bold=bool(r["bold"]),
                           italic=bool(r["italic"]), align=r["align"], border_mm=r["border_mm"],
                           symbol_pos=r["symbol_pos"], enabled=bool(r["enabled"]), sort_order=r["sort_order"],
                           text_color=r["text_color"], symbol_color=r["symbol_color"],
                           border_color=r["border_color"], bg_color=r["bg_color"])

    def list_instructions(self) -> list[Instruction]:
        rows = self.conn.execute("SELECT * FROM instructions ORDER BY sort_order, id").fetchall()
        return [self._to_instruction(r) for r in rows]

    def save_instruction(self, ins: Instruction) -> int:
        vals = (ins.name.strip(), ins.text, ins.symbol, ins.font_family, ins.font_pt, int(ins.bold),
                int(ins.italic), ins.align, ins.border_mm, ins.symbol_pos, int(ins.enabled), ins.text_color,
                ins.symbol_color, ins.border_color, ins.bg_color)
        try:
            with self.conn:
                if ins.id is None:
                    order = self.conn.execute("SELECT COALESCE(MAX(sort_order),-1)+1 FROM instructions").fetchone()[0]
                    cur = self.conn.execute(
                        "INSERT INTO instructions(name,text,symbol,font_family,font_pt,bold,italic,align,"
                        "border_mm,symbol_pos,enabled,text_color,symbol_color,border_color,bg_color,sort_order) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", vals + (order,))
                    ins.id = cur.lastrowid
                else:
                    self.conn.execute(
                        "UPDATE instructions SET name=?,text=?,symbol=?,font_family=?,font_pt=?,bold=?,italic=?,"
                        "align=?,border_mm=?,symbol_pos=?,enabled=?,text_color=?,symbol_color=?,border_color=?,bg_color=? "
                        "WHERE id=?", vals + (ins.id,))
        except sqlite3.IntegrityError as exc:
            raise DatabaseError(f"An instruction named '{ins.name}' already exists.") from exc
        return ins.id  # type: ignore[return-value]

    def set_instruction_enabled(self, ins_id: int, enabled: bool) -> None:
        with self.conn:
            self.conn.execute("UPDATE instructions SET enabled=? WHERE id=?", (int(enabled), ins_id))

    def delete_instruction(self, ins_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM instructions WHERE id=?", (ins_id,))
            for t in self.list_templates():  # keep templates free of dangling ids
                if ins_id in t.instruction_ids:
                    t.instruction_ids.remove(ins_id)
                    self.conn.execute("UPDATE templates SET instruction_ids=? WHERE id=?",
                                      (json.dumps(t.instruction_ids), t.id))

    # ---- symbols ----
    def symbol_config(self) -> list[tuple[str, str]]:
        """Enabled symbols as (key, label), in the configured order."""
        rows = self.conn.execute("SELECT key,label FROM symbol_config WHERE enabled=1 ORDER BY sort_order").fetchall()
        return [(r["key"], r["label"]) for r in rows if r["key"] in SYMBOLS]

    # ---- templates ----
    @staticmethod
    def _to_template(r: sqlite3.Row) -> Template:
        doc = Document.from_dict(json.loads(r["document"])) if r["document"] else None
        return Template(id=r["id"], name=r["name"], instruction_ids=json.loads(r["instruction_ids"]),
                        params=AutoLayoutParams.from_dict(json.loads(r["params"])), document=doc)

    def list_templates(self) -> list[Template]:
        return [self._to_template(r) for r in self.conn.execute("SELECT * FROM templates ORDER BY id")]

    def get_template(self, tid: int) -> Template | None:
        r = self.conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
        return self._to_template(r) if r else None

    def save_template(self, t: Template) -> int:
        vals = (t.name.strip(), json.dumps(t.instruction_ids), json.dumps(t.params.to_dict()),
                json.dumps(t.document.to_dict()) if t.document else None)
        try:
            with self.conn:
                if t.id is None:
                    t.id = self.conn.execute(
                        "INSERT INTO templates(name,instruction_ids,params,document) VALUES(?,?,?,?)", vals).lastrowid
                else:
                    self.conn.execute("UPDATE templates SET name=?,instruction_ids=?,params=?,document=? WHERE id=?",
                                      vals + (t.id,))
        except sqlite3.IntegrityError as exc:
            raise DatabaseError(f"A template named '{t.name}' already exists.") from exc
        return t.id  # type: ignore[return-value]

    def delete_template(self, tid: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM templates WHERE id=?", (tid,))
