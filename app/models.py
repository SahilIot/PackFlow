"""Plain data models shared by the database, layout editor and printing code.

All geometry is in millimetres. Models are JSON serialisable so that templates
can be stored in SQLite and restored exactly.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from typing import Any

A4_W_MM = 210.0
A4_H_MM = 297.0
ALIGNMENTS = ("left", "center", "right")
COLOR_MODES = (("color", "Color"), ("grayscale", "Grayscale"), ("bw", "Black & White"))
PRESET_COLORS = (("Black", "#000000"), ("Red", "#d00000"), ("Blue", "#0057b8"), ("Green", "#1a8f3c"),
                 ("Orange", "#f57c00"), ("Yellow", "#ffd500"), ("White", "#ffffff"))
SYMBOL_POSITIONS = ("top", "bottom", "left", "right")


def page_size_mm(orientation: str) -> tuple[float, float]:
    return (A4_H_MM, A4_W_MM) if orientation == "landscape" else (A4_W_MM, A4_H_MM)


def _from_dict(cls, data: dict[str, Any]):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class Instruction:
    name: str
    text: str = ""
    symbol: str = ""
    font_family: str = "Arial"
    font_pt: float = 72.0
    bold: bool = True
    italic: bool = False
    align: str = "center"
    border_mm: float = 1.5
    symbol_pos: str = "top"
    enabled: bool = True
    sort_order: int = 0
    id: int | None = None
    text_color: str = "#000000"
    symbol_color: str = "#000000"
    border_color: str = "#000000"
    bg_color: str = ""          # "" = no background fill

    @property
    def printed_text(self) -> str:
        return self.text if self.text.strip() else self.name


@dataclass
class Element:
    """A text and/or symbol box placed on a page."""
    x: float = 10.0
    y: float = 10.0
    w: float = 80.0
    h: float = 50.0
    text: str = ""
    symbol: str = ""
    symbol_pos: str = "top"
    symbol_ratio: float = 0.55  # share of the box used by the symbol when text is present
    font_family: str = "Arial"
    font_pt: float = 40.0
    bold: bool = True
    italic: bool = False
    align: str = "center"
    border_mm: float = 0.0
    dashed: bool = False
    padding_mm: float = 2.0
    auto_fit: bool = False
    text_color: str = "#000000"
    symbol_color: str = "#000000"
    border_color: str = "#000000"
    bg_color: str = ""          # "" = no background fill
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Element":
        return _from_dict(cls, data)

    def clone(self) -> "Element":
        d = self.to_dict()
        d["uid"] = uuid.uuid4().hex[:10]
        return Element.from_dict(d)


@dataclass
class Page:
    elements: list[Element] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"elements": [e.to_dict() for e in self.elements]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Page":
        return cls([Element.from_dict(e) for e in data.get("elements", [])])


@dataclass
class Document:
    """One print job: A4 pages sharing an orientation and margin guide."""
    orientation: str = "portrait"
    margin_mm: float = 10.0
    grid_mm: float = 5.0
    pages: list[Page] = field(default_factory=lambda: [Page()])

    def to_dict(self) -> dict[str, Any]:
        return {"orientation": self.orientation, "margin_mm": self.margin_mm,
                "grid_mm": self.grid_mm, "pages": [p.to_dict() for p in self.pages]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        pages = [Page.from_dict(p) for p in data.get("pages", [])] or [Page()]
        return cls(data.get("orientation", "portrait"), float(data.get("margin_mm", 10.0)),
                   float(data.get("grid_mm", 5.0)), pages)

    @property
    def size_mm(self) -> tuple[float, float]:
        return page_size_mm(self.orientation)


@dataclass
class AutoLayoutParams:
    """Settings for generating a document from selected instructions."""
    orientation: str = "portrait"
    per_page: int = 0       # 0 = automatic
    margin_mm: float = 10.0
    gap_mm: float = 6.0
    color_mode: str = ""     # "" = leave the current print-color choice unchanged when the template is loaded

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoLayoutParams":
        return _from_dict(cls, data)


@dataclass
class Template:
    name: str
    instruction_ids: list[int] = field(default_factory=list)
    params: AutoLayoutParams = field(default_factory=AutoLayoutParams)
    document: Document | None = None   # set => custom layout, None => automatic
    id: int | None = None
