"""Automatic layout: turns selected instructions into paginated A4 documents."""
from __future__ import annotations

import math

from .models import AutoLayoutParams, Document, Element, Instruction, Page, page_size_mm

AUTO_MAX_PER_PAGE = 6


def grid_for(count: int, page_w: float, page_h: float) -> tuple[int, int]:
    """Choose (cols, rows) for `count` cells that keeps cells close to square-ish/wide."""
    best, best_score = (1, count), float("inf")
    for cols in range(1, count + 1):
        rows = math.ceil(count / cols)
        cell_ratio = (page_w / cols) / (page_h / rows)
        waste = cols * rows - count
        score = abs(math.log(cell_ratio / 1.0)) + waste * 0.35
        if score < best_score:
            best, best_score = (cols, rows), score
    return best


def card_from_instruction(ins: Instruction, x: float, y: float, w: float, h: float) -> Element:
    return Element(x=x, y=y, w=w, h=h, text=ins.printed_text, symbol=ins.symbol, symbol_pos=ins.symbol_pos,
                   font_family=ins.font_family, font_pt=ins.font_pt, bold=ins.bold, italic=ins.italic,
                   align=ins.align, border_mm=ins.border_mm, padding_mm=4.0, auto_fit=True,
                   text_color=ins.text_color, symbol_color=ins.symbol_color, border_color=ins.border_color,
                   bg_color=ins.bg_color)


def build_document(instructions: list[Instruction], params: AutoLayoutParams) -> Document:
    """Arrange instruction cards in a grid, adding pages as needed."""
    doc = Document(orientation=params.orientation, margin_mm=params.margin_mm)
    doc.pages = []
    if not instructions:
        doc.pages.append(Page())
        return doc
    pw, ph = page_size_mm(params.orientation)
    per_page = params.per_page if params.per_page > 0 else min(len(instructions), AUTO_MAX_PER_PAGE)
    m, gap = params.margin_mm, params.gap_mm
    area_w, area_h = pw - 2 * m, ph - 2 * m
    cols, rows = grid_for(per_page, area_w, area_h)
    cell_w = (area_w - gap * (cols - 1)) / cols
    cell_h = (area_h - gap * (rows - 1)) / rows
    for start in range(0, len(instructions), per_page):
        page = Page()
        chunk = instructions[start:start + per_page]
        # Centre a short last row so partly filled pages still look balanced.
        for i, ins in enumerate(chunk):
            r, c = divmod(i, cols)
            in_row = min(cols, len(chunk) - r * cols)
            row_offset = (cols - in_row) * (cell_w + gap) / 2
            page.elements.append(card_from_instruction(
                ins, m + row_offset + c * (cell_w + gap), m + r * (cell_h + gap), cell_w, cell_h))
        doc.pages.append(page)
    return doc
