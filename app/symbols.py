"""Built-in vector packing symbols (black on white, printer friendly).
Every symbol is drawn into a 100 x 100 design box and scaled to the target
rectangle, so it stays sharp at any size and prints identically to the preview.
"""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF

BLACK = QColor(0, 0, 0)
WHITE = QColor(255, 255, 255)
# Colours in force while one symbol is drawn: "ink" = line/fill colour, "paper" = the colour behind the symbol.
_STATE = {"ink": BLACK, "paper": WHITE}

def ink() -> QColor:
    return _STATE["ink"]

def paper() -> QColor:
    return _STATE["paper"]
LW = 5.0  # base line width in design units


def _pen(painter: QPainter, width: float = LW) -> None:
    painter.setPen(QPen(ink(), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)

def _fill(painter: QPainter, color: QColor | None = None) -> None:
    painter.setPen(QPen(ink(), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QBrush(color or ink()))

def _poly(painter: QPainter, pts: list[tuple[float, float]]) -> None:
    painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))

def _arrow_up(painter: QPainter, cx: float, top: float, bottom: float, head_w: float, shaft_w: float,
              head_h: float) -> None:
    _fill(painter)
    _poly(painter, [(cx, top), (cx + head_w / 2, top + head_h), (cx + shaft_w / 2, top + head_h),
                    (cx + shaft_w / 2, bottom), (cx - shaft_w / 2, bottom),
                    (cx - shaft_w / 2, top + head_h), (cx - head_w / 2, top + head_h)])

def _box(painter: QPainter, x: float, y: float, w: float, h: float, tape: bool = True) -> None:
    _pen(painter, 4)
    painter.drawRect(QRectF(x, y, w, h))
    if tape:
        painter.drawLine(QPointF(x + w / 2, y), QPointF(x + w / 2, y + h * 0.3))

def arrow_up(p: QPainter) -> None:
    _arrow_up(p, 50, 6, 94, 70, 28, 40)

def arrow_down(p: QPainter) -> None:
    p.save(); p.translate(50, 50); p.rotate(180); p.translate(-50, -50)
    arrow_up(p); p.restore()

def arrow_left(p: QPainter) -> None:
    p.save(); p.translate(50, 50); p.rotate(-90); p.translate(-50, -50)
    arrow_up(p); p.restore()

def arrow_right(p: QPainter) -> None:
    p.save(); p.translate(50, 50); p.rotate(90); p.translate(-50, -50)
    arrow_up(p); p.restore()

def this_side_up(p: QPainter) -> None:
    # ISO 7000 style: two upward arrows side by side
    _arrow_up(p, 28, 8, 92, 40, 15, 30)
    _arrow_up(p, 72, 8, 92, 40, 15, 30)

def fragile(p: QPainter) -> None:
    # wine glass with a crack
    _pen(p, 5)
    path = QPainterPath()
    path.moveTo(25, 8); path.lineTo(75, 8)
    path.cubicTo(75, 45, 62, 55, 50, 58)
    path.cubicTo(38, 55, 25, 45, 25, 8)
    p.drawPath(path)
    p.drawLine(QPointF(50, 58), QPointF(50, 86))
    p.drawLine(QPointF(30, 92), QPointF(70, 92))
    p.drawLine(QPointF(25, 8), QPointF(75, 8))
    _pen(p, 4)
    zig = QPainterPath()
    zig.moveTo(50, 8); zig.lineTo(43, 24); zig.lineTo(56, 34); zig.lineTo(47, 50)
    p.drawPath(zig)

def handle_with_care(p: QPainter) -> None:
    # carton resting on a cupped hand
    _box(p, 26, 8, 48, 34)
    _pen(p, 5)
    hand = QPainterPath()
    hand.moveTo(6, 58); hand.lineTo(26, 52); hand.lineTo(60, 52)
    hand.cubicTo(70, 52, 70, 64, 60, 64); hand.lineTo(42, 64)
    p.drawPath(hand)
    palm = QPainterPath()
    palm.moveTo(42, 64); palm.lineTo(70, 62); palm.cubicTo(80, 61, 90, 56, 94, 50)
    p.drawPath(palm)
    thumb = QPainterPath()
    thumb.moveTo(6, 58); thumb.lineTo(6, 90); thumb.lineTo(52, 90)
    thumb.cubicTo(70, 90, 82, 80, 94, 50)
    p.drawPath(thumb)

def keep_dry(p: QPainter) -> None:
    # umbrella with rain
    _pen(p, 5)
    canopy = QPainterPath()
    canopy.moveTo(10, 48)
    canopy.cubicTo(10, 12, 90, 12, 90, 48)
    canopy.cubicTo(80, 40, 70, 40, 63, 48)
    canopy.cubicTo(56, 40, 44, 40, 37, 48)
    canopy.cubicTo(30, 40, 20, 40, 10, 48)
    _fill(p)
    p.drawPath(canopy)
    _pen(p, 5)
    p.drawLine(QPointF(50, 30), QPointF(50, 78))
    hook = QPainterPath()
    hook.moveTo(50, 78); hook.cubicTo(50, 92, 36, 92, 36, 80)
    p.drawPath(hook)
    _pen(p, 4)
    for x in (16, 50, 84):
        p.drawLine(QPointF(x, 62 if x != 50 else 84), QPointF(x - 5, 74 if x != 50 else 96))
    p.drawLine(QPointF(30, 58), QPointF(25, 70))
    p.drawLine(QPointF(70, 58), QPointF(65, 70))

def do_not_stack(p: QPainter) -> None:
    _box(p, 22, 6, 56, 30, tape=False)
    _box(p, 22, 38, 56, 30, tape=False)
    _box(p, 22, 70, 56, 26, tape=False)
    _pen(p, 7)
    p.drawLine(QPointF(8, 8), QPointF(92, 94))
    p.drawLine(QPointF(92, 8), QPointF(8, 94))

def heavy_material(p: QPainter) -> None:
    # weight block
    _fill(p)
    path = QPainterPath()
    path.moveTo(34, 20); path.cubicTo(34, 6, 66, 6, 66, 20); path.lineTo(76, 20)
    path.lineTo(96, 90); path.lineTo(4, 90); path.lineTo(24, 20); path.closeSubpath()
    p.drawPath(path)
    p.setPen(QPen(paper(), 4)); p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(41, 10, 18, 14))
    f = p.font(); f.setBold(True); f.setFamily("Arial"); f.setPixelSize(30); p.setFont(f)
    p.drawText(QRectF(4, 40, 92, 50), Qt.AlignCenter, "KG")

def lift_here(p: QPainter) -> None:
    # carton with lifting arrows pointing up at the two lift points
    _box(p, 8, 8, 84, 52)
    _arrow_up(p, 24, 66, 96, 26, 10, 14)
    _arrow_up(p, 76, 66, 96, 26, 10, 14)
    _pen(p, 4)
    p.drawLine(QPointF(24, 60), QPointF(24, 66)); p.drawLine(QPointF(76, 60), QPointF(76, 66))

def center_of_gravity(p: QPainter) -> None:
    c = QPointF(50, 50); r = 26
    rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
    _fill(p, paper())
    p.drawEllipse(rect)
    _fill(p)
    p.drawPie(rect, 90 * 16, 90 * 16)
    p.drawPie(rect, 270 * 16, 90 * 16)
    _pen(p, 5)
    p.drawEllipse(rect)
    p.drawLine(QPointF(50, 4), QPointF(50, 96))
    p.drawLine(QPointF(4, 50), QPointF(96, 50))

# key -> (label, draw function)
SYMBOLS: dict[str, tuple[str, Callable[[QPainter], None]]] = {
    "arrow_up": ("Upward arrow", arrow_up),
    "arrow_down": ("Downward arrow", arrow_down),
    "arrow_left": ("Left arrow", arrow_left),
    "arrow_right": ("Right arrow", arrow_right),
    "fragile": ("Fragile", fragile),
    "handle_with_care": ("Handle with care", handle_with_care),
    "keep_dry": ("Keep dry", keep_dry),
    "do_not_stack": ("Do not stack", do_not_stack),
    "heavy_material": ("Heavy material", heavy_material),
    "lift_here": ("Lift here", lift_here),
    "center_of_gravity": ("Center of gravity", center_of_gravity),
    "this_side_up": ("This side up", this_side_up),
}

def symbol_label(key: str) -> str:
    return SYMBOLS[key][0] if key in SYMBOLS else key

def draw_symbol(painter: QPainter, key: str, rect: QRectF, color: QColor | None = None,
                background: QColor | None = None) -> None:
    """Draw symbol `key` centred in `rect`, keeping its square proportions.
    color is the line/fill colour (default black); `background` is what shows through the
    symbol's "white" parts (default white), so symbols stay correct on coloured backgrounds.
    """
    if key not in SYMBOLS or rect.width() <= 0 or rect.height() <= 0:
        return
    _STATE["ink"], _STATE["paper"] = color or BLACK, background or WHITE
    side = min(rect.width(), rect.height())
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.translate(rect.center().x() - side / 2, rect.center().y() - side / 2)
    painter.scale(side / 100.0, side / 100.0)
    SYMBOLS[key][1](painter)
    painter.restore()
