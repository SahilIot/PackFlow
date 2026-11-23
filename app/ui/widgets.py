# Small reusable widgets: symbol icons, element preview and A4 page preview.
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QColorDialog, QMenu, QPushButton, QSizePolicy, QWidget

from ..models import PRESET_COLORS, Document, Element
from ..renderer import UNIT, draw_element, paint_page
from ..symbols import draw_symbol


def symbol_icon(key: str, size: int = 40, color: str = "#000000") -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.white)
    p = QPainter(pm)
    draw_symbol(p, key, QRectF(2, 2, size - 4, size - 4), QColor(color))
    p.end()
    return QIcon(pm)


def swatch_icon(color: str, size: int = 18) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if color:
        p.setBrush(QColor(color))
        p.setPen(QPen(QColor("#7d8b9a"), 1))
    else:   # "no colour": white square with a red slash
        p.setBrush(Qt.white)
        p.setPen(QPen(QColor("#7d8b9a"), 1))
    p.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 3, 3)
    if not color:
        p.setPen(QPen(QColor("#d00000"), 2))
        p.drawLine(4, size - 4, size - 4, 4)
    p.end()
    return QIcon(pm)


class ColorButton(QPushButton):
    # Button showing the current colour; opens a menu of preset colours plus a full colour picker.
    colorChanged = Signal(str)

    def __init__(self, color: str = "#000000", allow_none: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self._allow_none = allow_none
        self.setMinimumWidth(120)
        menu = QMenu(self)
        for name, value in PRESET_COLORS:
            menu.addAction(swatch_icon(value), name).triggered.connect(lambda _=False, v=value: self.set_color(v, True))
        if allow_none:
            menu.addAction(swatch_icon(""), "No background").triggered.connect(lambda _=False: self.set_color("", True))
        menu.addSeparator()
        menu.addAction("Custom color…").triggered.connect(self._pick)
        self.setMenu(menu)
        self._refresh()

    def color(self) -> str:
        return self._color

    def set_color(self, color: str, emit: bool = False) -> None:
        self._color = color
        self._refresh()
        if emit:
            self.colorChanged.emit(color)

    def _pick(self) -> None:
        start = QColor(self._color) if self._color else QColor("#ffffff")
        chosen = QColorDialog.getColor(start, self, "Choose color")
        if chosen.isValid():
            self.set_color(chosen.name(), True)

    def _refresh(self) -> None:
        self.setIcon(swatch_icon(self._color))
        self.setText(self._color.upper() if self._color else "None")


class ElementPreview(QWidget):
    # Shows one element exactly as it will be printed, scaled to fit.

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._el: Element | None = None
        self.setMinimumSize(QSize(180, 140))

    def set_element(self, el: Element) -> None:
        self._el = el
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#dfe5ec"))
        if self._el is None:
            return
        el = self._el
        W, H = el.w * UNIT, el.h * UNIT
        s = min((self.width() - 16) / W, (self.height() - 16) / H)
        p.translate((self.width() - W * s) / 2, (self.height() - H * s) / 2)
        p.scale(s, s)
        p.fillRect(QRectF(0, 0, W, H), Qt.white)
        draw_element(p, el)


class PagePreview(QWidget):
    # Live A4 page thumbnail rendered by the same code that prints.

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc: Document | None = None
        self._page = 0
        self._mode = "color"
        self.setMinimumSize(QSize(200, 200))
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def set_document(self, doc: Document | None, page: int = 0, mode: str = "color") -> None:
        self._doc, self._page, self._mode = doc, page, mode
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#cdd5df"))
        if self._doc is None or not self._doc.pages:
            return
        pw, ph = self._doc.size_mm
        W, H = pw * UNIT, ph * UNIT
        s = min((self.width() - 24) / W, (self.height() - 24) / H)
        x0, y0 = (self.width() - W * s) / 2, (self.height() - H * s) / 2
        p.fillRect(QRectF(x0 + 4, y0 + 4, W * s, H * s), QColor(0, 0, 0, 50))  # shadow
        p.translate(x0, y0)
        p.scale(s, s)
        p.fillRect(QRectF(0, 0, W, H), Qt.white)
        page = self._doc.pages[min(self._page, len(self._doc.pages) - 1)]
        paint_page(p, self._doc, page, self._mode)
        p.setPen(QPen(QColor("#9aa5b1"), 0))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(0, 0, W, H))
