"""Single rendering path used by the editor, the preview and the printer.
Coordinates: one painter unit = 0.1 mm (UNIT units per millimetre). Because the
exact same functions paint the editor canvas, the preview and the printout,
what you see is what is printed.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from .models import Document, Element, Page
from .symbols import draw_symbol

UNIT = 10.0                      # painter units per millimetre
PT_TO_UNITS = UNIT * 25.4 / 72.0  # points -> painter units


def make_font(family: str, pt: float, bold: bool, italic: bool) -> QFont:
    f = QFont(family)
    f.setPixelSize(max(1, round(pt * PT_TO_UNITS)))
    f.setBold(bold)
    f.setItalic(italic)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def convert_color(value: str | QColor, mode: str) -> QColor:
    # Map a configured colour to what is printed in `mode` ("color", "grayscale" or "bw").
    # This one function is used by the preview, the PDF export and the printer, so they always agree.
    
    c = QColor(value) if not isinstance(value, QColor) else QColor(value)
    if not c.isValid():
        c = QColor(0, 0, 0)
    if mode == "color":
        return c
    lum = round(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
    if mode == "grayscale":
        return QColor(lum, lum, lum)
    return QColor(0, 0, 0) if lum < 160 else QColor(255, 255, 255)   # "bw": no intermediate shades

def _readable(fg: QColor, bg: QColor, mode: str) -> QColor:
    # In black & white, never print a foreground in the same colour as what is behind it.
    if mode == "bw" and fg == bg:
        return QColor(0, 0, 0) if bg == QColor(255, 255, 255) else QColor(255, 255, 255)
    return fg

_ALIGN = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight}

def _text_flags(el: Element) -> int:
    return int(_ALIGN.get(el.align, Qt.AlignHCenter) | Qt.AlignVCenter | Qt.TextWordWrap)


def fitted_font(painter: QPainter, el: Element, rect: QRectF) -> QFont:
    # Return the element font, shrunk if auto-fit is on and the text overflows.
    pt = el.font_pt
    font = make_font(el.font_family, pt, el.bold, el.italic)
    if not el.auto_fit:
        return font
    flags = _text_flags(el)
    while pt > 4:
        painter.setFont(font)
        used = painter.boundingRect(rect, flags, el.text)
        if used.height() <= rect.height() + 0.5 and used.width() <= rect.width() + 0.5:
            break
        pt *= 0.95
        font = make_font(el.font_family, pt, el.bold, el.italic)
    return font


def split_rects(el: Element, inner: QRectF) -> tuple[QRectF | None, QRectF | None]:
    # Split the inner box into (symbol_rect, text_rect) depending on content.
    has_sym, has_txt = bool(el.symbol), bool(el.text.strip())
    if has_sym and not has_txt:
        return inner, None
    if has_txt and not has_sym:
        return None, inner
    if not has_sym and not has_txt:
        return None, None
    r = min(max(el.symbol_ratio, 0.15), 0.85)
    gap = min(inner.width(), inner.height()) * 0.03
    w, h = inner.width(), inner.height()
    if el.symbol_pos == "bottom":
        return (QRectF(inner.left(), inner.bottom() - h * r, w, h * r),
                QRectF(inner.left(), inner.top(), w, h * (1 - r) - gap))
    if el.symbol_pos == "left":
        return (QRectF(inner.left(), inner.top(), w * r, h),
                QRectF(inner.left() + w * r + gap, inner.top(), w * (1 - r) - gap, h))
    if el.symbol_pos == "right":
        return (QRectF(inner.right() - w * r, inner.top(), w * r, h),
                QRectF(inner.left(), inner.top(), w * (1 - r) - gap, h))
    return (QRectF(inner.left(), inner.top(), w, h * r),
            QRectF(inner.left(), inner.top() + h * r + gap, w, h * (1 - r) - gap))


def draw_element(painter: QPainter, el: Element, mode: str = "color") -> None:
    # Paint one element into the local rect (0, 0, w, h) in painter units, in colour mode
    W, H = el.w * UNIT, el.h * UNIT
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    white = QColor(255, 255, 255)
    bg = convert_color(el.bg_color, mode) if el.bg_color else None
    behind = bg or white
    if bg is not None:
        painter.fillRect(QRectF(0, 0, W, H), bg)
    bw = el.border_mm * UNIT
    if bw > 0:
        pen = QPen(_readable(convert_color(el.border_color, mode), behind, mode), bw,
                   Qt.DashLine if el.dashed else Qt.SolidLine)
        pen.setJoinStyle(Qt.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(bw / 2, bw / 2, W - bw, H - bw))
    pad = bw + el.padding_mm * UNIT
    inner = QRectF(pad, pad, W - 2 * pad, H - 2 * pad)
    if inner.width() > 0 and inner.height() > 0:
        sym_rect, txt_rect = split_rects(el, inner)
        if sym_rect is not None:
            draw_symbol(painter, el.symbol, sym_rect,
                        _readable(convert_color(el.symbol_color, mode), behind, mode), behind)
        if txt_rect is not None and txt_rect.width() > 0 and txt_rect.height() > 0:
            painter.setClipRect(txt_rect)
            painter.setPen(_readable(convert_color(el.text_color, mode), behind, mode))
            painter.setFont(fitted_font(painter, el, txt_rect))
            painter.drawText(txt_rect, _text_flags(el), el.text)
    painter.restore()


def paint_page(painter: QPainter, doc: Document, page: Page, mode: str = "color") -> None:
    # Paint all elements of a page; painter origin = page top-left, unit = 0.1 mm.
    for el in page.elements:
        painter.save()
        painter.translate(el.x * UNIT, el.y * UNIT)
        draw_element(painter, el, mode)
        painter.restore()


def content_bounds_mm(page: Page) -> tuple[float, float, float, float] | None:
    # (min_x, min_y, max_x, max_y) of all elements, or None if the page is empty.
    if not page.elements:
        return None
    return (min(e.x for e in page.elements), min(e.y for e in page.elements),
            max(e.x + e.w for e in page.elements), max(e.y + e.h for e in page.elements))
