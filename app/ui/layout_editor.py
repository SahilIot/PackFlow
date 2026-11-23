# A4 layout editor
from __future__ import annotations
import json
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFontComboBox, QFormLayout, QGraphicsItem,
                               QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout, QLabel, QMenu, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea, QToolBar, QToolButton, QVBoxLayout, QWidget)

from ..layout import card_from_instruction
from ..models import ALIGNMENTS, SYMBOL_POSITIONS, Document, Element, Instruction, Page
from ..renderer import UNIT, draw_element
from ..symbols import SYMBOLS
from .instruction_dialog import fill_symbol_combo
from .widgets import ColorButton, symbol_icon

HANDLE = 3.5 * UNIT          # handle size in scene units (3.5 mm)
MIN_SIZE = 8.0               # minimum element size in mm
# handle id -> (x factor, y factor) of the box it sits on: 0 = left/top, 0.5 = middle, 1 = right/bottom
HANDLES = {"nw": (0, 0), "n": (.5, 0), "ne": (1, 0), "e": (1, .5), "se": (1, 1), "s": (.5, 1), "sw": (0, 1), "w": (0, .5)}
CURSORS = {"nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor, "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
           "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor, "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor}

# Manages the page and its background
class PageScene(QGraphicsScene):
    changed_by_user = Signal()

    def __init__(self, doc: Document) -> None:
        super().__init__()
        self.doc = doc
        self.snap = True
        self.show_grid = True
        self.update_size()
# This determines the drawing area
    def update_size(self) -> None:
        w, h = self.doc.size_mm
        pad = 15 * UNIT
        self.setSceneRect(-pad, -pad, w * UNIT + 2 * pad, h * UNIT + 2 * pad)
        self.update()
# Sanp to grid -> useful feature -> suppose the grid size is 5mm we move ele to 23mm it will snap to 25mm make alignment accurately
    def snap_value(self, v: float) -> float:
        step = max(self.doc.grid_mm, 0.5) * UNIT
        return round(v / step) * step if self.snap else v
# Draws the background
    def drawBackground(self, p: QPainter, rect: QRectF) -> None:
        p.fillRect(rect, QColor("#b9c2cd"))
        w, h = self.doc.size_mm
        W, H = w * UNIT, h * UNIT
        p.fillRect(QRectF(UNIT * 1.5, UNIT * 1.5, W, H), QColor(0, 0, 0, 60))
        p.fillRect(QRectF(0, 0, W, H), Qt.white)
        if self.show_grid and self.doc.grid_mm > 0:
            p.setPen(QPen(QColor("#dfe4ea"), 0))
            step = self.doc.grid_mm * UNIT
            x = step
            while x < W:
                p.drawLine(QPointF(x, 0), QPointF(x, H)); x += step
            y = step
            while y < H:
                p.drawLine(QPointF(0, y), QPointF(W, y)); y += step
        m = self.doc.margin_mm * UNIT
        pen = QPen(QColor("#e08a3c"), 0, Qt.DashLine)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(m, m, W - 2 * m, H - 2 * m))

# Manages individual elements on the page
class ElementItem(QGraphicsItem):
    def __init__(self, el: Element, scene: PageScene) -> None:
        super().__init__()
        self.el = el
        self._scene = scene
        self._resize: dict | None = None
        self.base_z = 0.0        # stacking order; the selected item is raised so its handles stay reachable
        self._internal = False   # True while the editor itself moves the item (no snapping)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPos(el.x * UNIT, el.y * UNIT)

    # geometry
    def boundingRect(self) -> QRectF:
        m = HANDLE
        return QRectF(-m, -m, self.el.w * UNIT + 2 * m, self.el.h * UNIT + 2 * m)

    def shape(self):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(self.boundingRect() if self.isSelected() else QRectF(0, 0, self.el.w * UNIT, self.el.h * UNIT))
        return path

    def paint(self, p: QPainter, option, widget=None) -> None:
        draw_element(p, self.el)
        if self.isSelected():
            W, H = self.el.w * UNIT, self.el.h * UNIT
            p.setPen(QPen(QColor("#1f5fa8"), 0, Qt.DashLine)); p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(0, 0, W, H))
            p.setPen(QPen(QColor("#1f5fa8"), 0)); p.setBrush(QColor("white"))
            for fx, fy in HANDLES.values():
                p.drawRect(QRectF(fx * W - HANDLE / 2, fy * H - HANDLE / 2, HANDLE, HANDLE))

    def refresh(self) -> None:
        self.prepareGeometryChange()
        self._internal = True
        self.setPos(self.el.x * UNIT, self.el.y * UNIT)
        self._internal = False
        self.update()

    # interaction
    def _handle_at(self, pos: QPointF) -> str | None:
        if not self.isSelected():
            return None
        W, H = self.el.w * UNIT, self.el.h * UNIT
        for name, (fx, fy) in HANDLES.items():
            if abs(pos.x() - fx * W) <= HANDLE and abs(pos.y() - fy * H) <= HANDLE:
                return name
        return None

    def hoverMoveEvent(self, event) -> None:
        h = self._handle_at(event.pos())
        self.setCursor(CURSORS[h] if h else Qt.SizeAllCursor)

    def mousePressEvent(self, event) -> None:
        h = self._handle_at(event.pos()) if event.button() == Qt.LeftButton else None
        if h:
            self._scene.changed_by_user.emit()  # undo checkpoint
            self._resize = {"h": h, "x": self.el.x, "y": self.el.y, "w": self.el.w, "r": self.el.x + self.el.w,
                            "b": self.el.y + self.el.h}
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self._scene.changed_by_user.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self._resize:
            super().mouseMoveEvent(event)
            return
        r, h = self._resize, self._resize["h"]
        pt = event.scenePos()
        sx, sy = self._scene.snap_value(pt.x()) / UNIT, self._scene.snap_value(pt.y()) / UNIT
        left, top, right, bottom = r["x"], r["y"], r["r"], r["b"]
        if "w" in h: left = min(sx, right - MIN_SIZE)
        if "e" in h: right = max(sx, left + MIN_SIZE)
        if "n" in h: top = min(sy, bottom - MIN_SIZE)
        if "s" in h: bottom = max(sy, top + MIN_SIZE)
        self.prepareGeometryChange()
        self.el.x, self.el.y, self.el.w, self.el.h = left, top, right - left, bottom - top
        self._internal = True
        self.setPos(left * UNIT, top * UNIT)
        self._internal = False
        self.update()
        self.scene().update()
        self._scene.element_geometry_changed()

    def mouseReleaseEvent(self, event) -> None:
        self._resize = None
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None and not self._resize and not self._internal:
            value = QPointF(self._scene.snap_value(value.x()), self._scene.snap_value(value.y()))
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self.setZValue(1e6 if value else self.base_z)
        elif change == QGraphicsItem.ItemPositionHasChanged and not self._resize and not self._internal:
            self.el.x, self.el.y = value.x() / UNIT, value.y() / UNIT
            self._scene.element_geometry_changed()
        return super().itemChange(change, value)


def _element_geometry_changed(self: PageScene) -> None:
    cb = getattr(self, "on_geometry", None)
    if cb:
        cb()


PageScene.element_geometry_changed = _element_geometry_changed  # type: ignore[attr-defined]

# This class controls how the user interacts with the page view.
class EditorView(QGraphicsView):
    def __init__(self, scene: PageScene, owner: "LayoutEditor") -> None:
        super().__init__(scene)
        self.owner = owner
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            self.scale_by(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
        else:
            super().wheelEvent(event)

    def scale_by(self, f: float) -> None:
        self.scale(f, f)

    def keyPressEvent(self, event) -> None:
        step = 5.0 if event.modifiers() & Qt.ShiftModifier else 1.0
        moves = {Qt.Key_Left: (-step, 0), Qt.Key_Right: (step, 0), Qt.Key_Up: (0, -step), Qt.Key_Down: (0, step)}
        if event.key() in moves and self.owner.selected_elements():
            self.owner.nudge(*moves[event.key()])
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.owner.delete_selected()
        else:
            super().keyPressEvent(event)

# Manages the complete editing window and its functionality.
class LayoutEditor(QDialog):

    def __init__(self, parent: QWidget | None, doc: Document, instructions: list[Instruction],
                 symbols: list[tuple[str, str]], preview: Callable[[Document], None],
                 save_template: Callable[[Document], None] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("A4 Layout Editor")
        self.doc = Document.from_dict(json.loads(json.dumps(doc.to_dict())))  # work on a copy
        self.instructions = [i for i in instructions if i.enabled]
        self.symbols = symbols or [(k, v[0]) for k, v in SYMBOLS.items()]
        self._preview, self._save_template = preview, save_template
        self.page_index = 0
        self._undo: list[str] = []
        self._redo: list[str] = []
        self._last_edit = ("", 0.0)
        self._loading = False
        self._items: list[ElementItem] = []

        self.scene = PageScene(self.doc)
        self.scene.changed_by_user.connect(self.push_undo)
        self.scene.on_geometry = self._sync_geometry_fields
        self.scene.selectionChanged.connect(self._selection_changed)
        self.view = EditorView(self.scene, self)

        self._build_ui()
        self._load_page()
        self.resize(1280, 820)
        QTimer.singleShot(0, self.fit)

    def _build_ui(self) -> None:
        tb = QToolBar()
        tb.setStyleSheet("QToolButton { padding: 5px 7px; }")
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        tb.addAction(self._act("Add Text", self.add_text, "Add a text box"))
        sym_btn = QToolButton(); sym_btn.setText("Add Symbol ▾"); sym_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(sym_btn)
        for key, label in self.symbols:
            a = menu.addAction(symbol_icon(key, 32), label)
            a.triggered.connect(lambda _=False, k=key: self.add_symbol(k))
        sym_btn.setMenu(menu); tb.addWidget(sym_btn)
        ins_btn = QToolButton(); ins_btn.setText("Add Instruction ▾"); ins_btn.setPopupMode(QToolButton.InstantPopup)
        imenu = QMenu(ins_btn)
        for ins in self.instructions:
            a = imenu.addAction(symbol_icon(ins.symbol, 32) if ins.symbol else symbol_icon(""), ins.name)
            a.triggered.connect(lambda _=False, i=ins: self.add_instruction(i))
        ins_btn.setMenu(imenu); tb.addWidget(ins_btn)
        tb.addSeparator()
        tb.addAction(self._act("Duplicate", self.duplicate_selected, "Duplicate selected (Ctrl+D)", "Ctrl+D"))
        tb.addAction(self._act("Delete", self.delete_selected, "Delete selected (Del)"))
        tb.addAction(self._act("To Front", lambda: self.reorder(True), "Bring to front"))
        tb.addAction(self._act("To Back", lambda: self.reorder(False), "Send to back"))
        tb.addSeparator()
        al = QToolButton(); al.setText("Align ▾"); al.setPopupMode(QToolButton.InstantPopup)
        am = QMenu(al)
        for label, mode in (("Left", "left"), ("Centre horizontally", "hcenter"), ("Right", "right"),
                            ("Top", "top"), ("Centre vertically", "vcenter"), ("Bottom", "bottom")):
            am.addAction(label).triggered.connect(lambda _=False, m=mode: self.align_selected(m))
        al.setMenu(am); tb.addWidget(al)
        tb.addAction(self._act("Arrange in Grid…", self.arrange_grid, "Arrange all elements on this page in a grid"))
        tb.addSeparator()
        tb.addAction(self._act("Undo", self.undo, "Undo (Ctrl+Z)", "Ctrl+Z"))
        tb.addAction(self._act("Redo", self.redo, "Redo (Ctrl+Y)", "Ctrl+Y"))
        tb.addSeparator()
        tb.addAction(self._act("＋", lambda: self.view.scale_by(1.2)))
        tb.addAction(self._act("－", lambda: self.view.scale_by(1 / 1.2)))
        tb.addAction(self._act("Fit Page", self.fit))

        # page settings
        page_box = QGroupBox("Page")
        pf = QFormLayout(page_box)
        self.orient = QComboBox(); self.orient.addItem("Portrait", "portrait"); self.orient.addItem("Landscape", "landscape")
        self.orient.setCurrentIndex(0 if self.doc.orientation == "portrait" else 1)
        self.orient.currentIndexChanged.connect(self._orientation_changed)
        self.page_combo = QComboBox(); self.page_combo.currentIndexChanged.connect(self._page_changed)
        add_page = QPushButton("+ Page"); add_page.clicked.connect(self.add_page)
        del_page = QPushButton("− Page"); del_page.clicked.connect(self.delete_page)
        prow = QHBoxLayout(); prow.addWidget(add_page); prow.addWidget(del_page); prow.addStretch()
        self.margin = self._dspin(0, 50, self.doc.margin_mm, " mm", self._margin_changed)
        self.grid = self._dspin(0.5, 50, self.doc.grid_mm, " mm", self._grid_changed)
        self.snap = QCheckBox("Snap to grid"); self.snap.setChecked(True); self.snap.toggled.connect(self._snap_changed)
        self.show_grid = QCheckBox("Show grid"); self.show_grid.setChecked(True); self.show_grid.toggled.connect(self._grid_visible)
        pf.addRow("Orientation", self.orient); pf.addRow("", QLabel("A4: 210 × 297 mm")); pf.addRow("Page", self.page_combo); pf.addRow("", prow); pf.addRow("Margin guide", self.margin)
        pf.addRow("Grid size", self.grid); pf.addRow(self.snap); pf.addRow(self.show_grid)

        # element properties
        self.props = QGroupBox("Selected element")
        f = QFormLayout(self.props)
        self.x = self._dspin(-500, 500, 0, " mm", lambda v: self._set_geom("x", v))
        self.y = self._dspin(-500, 500, 0, " mm", lambda v: self._set_geom("y", v))
        self.w = self._dspin(MIN_SIZE, 500, 50, " mm", lambda v: self._set_geom("w", v))
        self.h = self._dspin(MIN_SIZE, 500, 50, " mm", lambda v: self._set_geom("h", v))
        self.text = QPlainTextEdit(); self.text.setFixedHeight(70); self.text.textChanged.connect(lambda: self._set("text", self.text.toPlainText()))
        self.symbol = QComboBox(); fill_symbol_combo(self.symbol, self.symbols)
        self.symbol.currentIndexChanged.connect(lambda: self._set("symbol", self.symbol.currentData() or ""))
        self.symbol_pos = QComboBox()
        for pos in SYMBOL_POSITIONS: self.symbol_pos.addItem(pos.capitalize(), pos)
        self.symbol_pos.currentIndexChanged.connect(lambda: self._set("symbol_pos", self.symbol_pos.currentData()))
        self.ratio = self._dspin(15, 85, 55, " %", lambda v: self._set("symbol_ratio", v / 100))
        self.font = QFontComboBox(); self.font.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon); self.font.setMinimumContentsLength(12); self.font.currentFontChanged.connect(lambda fnt: self._set("font_family", fnt.family()))
        self.size = self._dspin(4, 600, 40, " pt", lambda v: self._set("font_pt", v))
        self.bold = QCheckBox("Bold"); self.bold.toggled.connect(lambda v: self._set("bold", v))
        self.italic = QCheckBox("Italic"); self.italic.toggled.connect(lambda v: self._set("italic", v))
        self.align = QComboBox()
        for a in ALIGNMENTS: self.align.addItem(a.capitalize(), a)
        self.align.currentIndexChanged.connect(lambda: self._set("align", self.align.currentData()))
        self.border = self._dspin(0, 20, 0, " mm", lambda v: self._set("border_mm", v)); self.border.setSingleStep(0.5)
        self.dashed = QCheckBox("Dashed border"); self.dashed.toggled.connect(lambda v: self._set("dashed", v))
        self.padding = self._dspin(0, 40, 2, " mm", lambda v: self._set("padding_mm", v))
        self.autofit = QCheckBox("Shrink text to fit box"); self.autofit.toggled.connect(lambda v: self._set("auto_fit", v))
        self.text_color = ColorButton("#000000"); self.text_color.colorChanged.connect(lambda v: self._set("text_color", v))
        self.symbol_color = ColorButton("#000000"); self.symbol_color.colorChanged.connect(lambda v: self._set("symbol_color", v))
        self.border_color = ColorButton("#000000"); self.border_color.colorChanged.connect(lambda v: self._set("border_color", v))
        self.bg_color = ColorButton("", allow_none=True); self.bg_color.colorChanged.connect(lambda v: self._set("bg_color", v))
        self._geom_widgets = (self.x, self.y, self.w, self.h, self.text)
        f.addRow("X", self.x); f.addRow("Y", self.y); f.addRow("Width", self.w); f.addRow("Height", self.h)
        f.addRow("Text", self.text); f.addRow("Symbol", self.symbol); f.addRow("Symbol at", self.symbol_pos)
        f.addRow("Symbol share", self.ratio); f.addRow("Font", self.font); f.addRow("Size", self.size)
        st = QHBoxLayout(); st.addWidget(self.bold); st.addWidget(self.italic); f.addRow("Style", st)
        f.addRow("Alignment", self.align); f.addRow("Border", self.border); f.addRow("", self.dashed)
        f.addRow("Text color", self.text_color); f.addRow("Symbol color", self.symbol_color)
        f.addRow("Border color", self.border_color); f.addRow("Background", self.bg_color)
        f.addRow("Padding", self.padding); f.addRow("", self.autofit)
        self.props.setEnabled(False)

        side = QVBoxLayout(); side.addWidget(page_box); side.addWidget(self.props); side.addStretch()
        inner = QWidget(); inner.setLayout(side)
        side_w = QScrollArea(); side_w.setWidget(inner); side_w.setWidgetResizable(True); side_w.setFrameShape(QScrollArea.NoFrame)
        side_w.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); side_w.setFixedWidth(420)

        hint = QLabel("Drag to move · drag handles to resize · arrow keys nudge (Shift = 5 mm) · Ctrl+wheel zooms · "
                      "orange dashed line = margin guide"); hint.setObjectName("hint")
        buttons = QHBoxLayout()
        prev = QPushButton("A4 Preview"); prev.clicked.connect(lambda: self._preview(self.doc))
        buttons.addWidget(hint, 1); buttons.addWidget(prev)
        if self._save_template:
            st_btn = QPushButton("Save as Template…"); st_btn.clicked.connect(lambda: self._save_template(self.doc))
            buttons.addWidget(st_btn)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Use This Layout"); ok.setObjectName("primary"); ok.clicked.connect(self.accept)
        buttons.addWidget(cancel); buttons.addWidget(ok)

        main = QHBoxLayout(); main.addWidget(self.view, 1); main.addWidget(side_w)
        root = QVBoxLayout(self); root.addWidget(tb); root.addLayout(main, 1); root.addLayout(buttons)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)

    def _act(self, text: str, fn, tip: str = "", shortcut: str = "") -> QAction:
        a = QAction(text, self)
        a.triggered.connect(lambda _=False: fn())
        if tip: a.setToolTip(tip)
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        return a

    @staticmethod
    def _dspin(lo: float, hi: float, val: float, suffix: str, slot) -> QDoubleSpinBox:
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setDecimals(1); s.setSuffix(suffix); s.setValue(val)
        s.valueChanged.connect(slot)
        return s

    @property
    def page(self) -> Page:
        return self.doc.pages[self.page_index]

    def document(self) -> Document:
        return self.doc

    def _load_page(self) -> None:
        self._loading = True
        self.scene.clearSelection()
        for it in self._items:
            self.scene.removeItem(it)
        self._items = []
        for el in self.page.elements:
            self._add_item(el)
        self.page_combo.blockSignals(True)
        self.page_combo.clear()
        for i in range(len(self.doc.pages)):
            self.page_combo.addItem(f"Page {i + 1} of {len(self.doc.pages)}")
        self.page_combo.setCurrentIndex(self.page_index)
        self.page_combo.blockSignals(False)
        self._loading = False
        self._selection_changed()

    def _add_item(self, el: Element) -> ElementItem:
        it = ElementItem(el, self.scene)
        it.base_z = float(len(self._items)); it.setZValue(it.base_z)
        self.scene.addItem(it)
        self._items.append(it)
        return it

    def selected_items(self) -> list[ElementItem]:
        return [i for i in self.scene.selectedItems() if isinstance(i, ElementItem)]

    def selected_elements(self) -> list[Element]:
        return [i.el for i in self.selected_items()]

    def _snapshot(self) -> str:
        return json.dumps({"doc": self.doc.to_dict(), "page": self.page_index})

    def push_undo(self) -> None:
        if self._loading:
            return
        self._undo.append(self._snapshot())
        del self._undo[:-60]
        self._redo.clear()

    def _restore(self, snap: str) -> None:
        data = json.loads(snap)
        self.doc = Document.from_dict(data["doc"])
        self.page_index = min(data["page"], len(self.doc.pages) - 1)
        self.scene.doc = self.doc
        self.scene.update_size()
        self.orient.blockSignals(True); self.orient.setCurrentIndex(0 if self.doc.orientation == "portrait" else 1); self.orient.blockSignals(False)
        for w, v in ((self.margin, self.doc.margin_mm), (self.grid, self.doc.grid_mm)):
            w.blockSignals(True); w.setValue(v); w.blockSignals(False)
        self._load_page()

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._snapshot())
            self._restore(self._undo.pop())

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._snapshot())
            self._restore(self._redo.pop())

    def _place_new(self, el: Element) -> None:
        self.push_undo()
        pw, ph = self.doc.size_mm
        el.x = self.scene.snap_value((pw - el.w) / 2 * UNIT) / UNIT
        el.y = self.scene.snap_value((ph - el.h) / 2 * UNIT) / UNIT
        self.page.elements.append(el)
        self.scene.clearSelection()
        it = self._add_item(el)
        it.setSelected(True)

    def add_text(self) -> None:
        self._place_new(Element(w=100, h=40, text="TEXT", font_pt=48, border_mm=0))

    def add_symbol(self, key: str) -> None:
        self._place_new(Element(w=60, h=60, symbol=key, border_mm=0, padding_mm=1))

    def add_instruction(self, ins: Instruction) -> None:
        pw, ph = self.doc.size_mm
        w, h = (pw - 2 * self.doc.margin_mm) / 2, (ph - 2 * self.doc.margin_mm) / 3
        self._place_new(card_from_instruction(ins, 0, 0, w, h))

    def delete_selected(self) -> None:
        items = self.selected_items()
        if not items:
            return
        self.push_undo()
        for it in items:
            self.page.elements.remove(it.el)
            self.scene.removeItem(it)
            self._items.remove(it)

    def duplicate_selected(self) -> None:
        items = self.selected_items()
        if not items:
            return
        self.push_undo()
        self.scene.clearSelection()
        for it in items:
            c = it.el.clone(); c.x += 5; c.y += 5
            self.page.elements.append(c)
            self._add_item(c).setSelected(True)

    def reorder(self, front: bool) -> None:
        sel = self.selected_elements()
        if not sel:
            return
        self.push_undo()
        others = [e for e in self.page.elements if e not in sel]
        self.page.elements[:] = others + sel if front else sel + others
        for z, e in enumerate(self.page.elements):
            item = next(i for i in self._items if i.el is e)
            item.base_z = float(z)
            item.setZValue(1e6 if item.isSelected() else item.base_z)

    def nudge(self, dx: float, dy: float) -> None:
        self._coalesced_undo("nudge")
        for it in self.selected_items():
            it.el.x += dx; it.el.y += dy
            it.refresh()
        self._sync_geometry_fields()

    def align_selected(self, mode: str) -> None:
        sel = self.selected_elements()
        if not sel:
            return
        self.push_undo()
        if len(sel) > 1:
            x0, y0 = min(e.x for e in sel), min(e.y for e in sel)
            x1, y1 = max(e.x + e.w for e in sel), max(e.y + e.h for e in sel)
        else:
            pw, ph = self.doc.size_mm
            m = self.doc.margin_mm
            x0, y0, x1, y1 = m, m, pw - m, ph - m
        for e in sel:
            if mode == "left": e.x = x0
            elif mode == "right": e.x = x1 - e.w
            elif mode == "hcenter": e.x = (x0 + x1 - e.w) / 2
            elif mode == "top": e.y = y0
            elif mode == "bottom": e.y = y1 - e.h
            elif mode == "vcenter": e.y = (y0 + y1 - e.h) / 2
        self._refresh_items()

    def arrange_grid(self) -> None:
        els = self.page.elements
        if not els:
            return
        from PySide6.QtWidgets import QDialogButtonBox, QSpinBox as SB
        dlg = QDialog(self); dlg.setWindowTitle("Arrange in Grid")
        cols, rows = SB(), SB()
        n = len(els)
        for s in (cols, rows): s.setRange(1, 12)
        cols.setValue(2 if n > 1 else 1); rows.setValue(-(-n // cols.value()))
        gap = self._dspin(0, 50, 6, " mm", lambda _v: None)
        form = QFormLayout(dlg); form.addRow("Columns", cols); form.addRow("Rows", rows); form.addRow("Gap", gap)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); form.addRow(bb)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        if dlg.exec() != QDialog.Accepted:
            return
        if cols.value() * rows.value() < n:
            QMessageBox.warning(self, "Grid too small", f"The grid has fewer cells than the {n} elements on this page.")
            return
        self.push_undo()
        pw, ph = self.doc.size_mm
        m, g = self.doc.margin_mm, gap.value()
        cw = (pw - 2 * m - g * (cols.value() - 1)) / cols.value()
        ch = (ph - 2 * m - g * (rows.value() - 1)) / rows.value()
        for i, e in enumerate(sorted(els, key=lambda e: (round(e.y / 10), e.x))):
            r, c = divmod(i, cols.value())
            e.x, e.y, e.w, e.h = m + c * (cw + g), m + r * (ch + g), cw, ch
        self._refresh_items()

    def _refresh_items(self) -> None:
        for it in self._items:
            it.refresh()
        self._sync_geometry_fields()

    def add_page(self) -> None:
        self.push_undo()
        self.doc.pages.insert(self.page_index + 1, Page())
        self.page_index += 1
        self._load_page()

    def delete_page(self) -> None:
        if len(self.doc.pages) <= 1:
            QMessageBox.information(self, "Delete page", "A document needs at least one page.")
            return
        if self.page.elements and QMessageBox.question(
                self, "Delete page", "Delete this page and everything on it?") != QMessageBox.Yes:
            return
        self.push_undo()
        del self.doc.pages[self.page_index]
        self.page_index = min(self.page_index, len(self.doc.pages) - 1)
        self._load_page()

    def _page_changed(self, idx: int) -> None:
        if idx >= 0 and not self._loading:
            self.page_index = idx
            self._load_page()

    def _orientation_changed(self) -> None:
        new = self.orient.currentData()
        if new == self.doc.orientation:
            return
        self.push_undo()
        old_w, old_h = self.doc.size_mm
        self.doc.orientation = new
        new_w, new_h = self.doc.size_mm
        sx, sy = new_w / old_w, new_h / old_h   # keep proportions: scale content to the rotated page
        for p in self.doc.pages:
            for e in p.elements:
                e.x, e.w, e.y, e.h = e.x * sx, e.w * sx, e.y * sy, e.h * sy
        self.scene.update_size()
        self._refresh_items()
        QTimer.singleShot(0, self.fit)

    def _margin_changed(self, v: float) -> None:
        self.doc.margin_mm = v
        self.scene.update()

    def _grid_changed(self, v: float) -> None:
        self.doc.grid_mm = v
        self.scene.update()

    def _snap_changed(self, on: bool) -> None:
        self.scene.snap = on

    def _grid_visible(self, on: bool) -> None:
        self.scene.show_grid = on
        self.scene.update()

    def fit(self) -> None:
        w, h = self.doc.size_mm
        self.view.fitInView(QRectF(-5 * UNIT, -5 * UNIT, (w + 10) * UNIT, (h + 10) * UNIT), Qt.KeepAspectRatio)

    def _selection_changed(self) -> None:
        if self._loading:
            return
        sel = self.selected_elements()
        self.props.setEnabled(bool(sel))
        for w in self._geom_widgets:
            w.setEnabled(len(sel) == 1)
        if not sel:
            return
        e = sel[0]
        self._loading = True
        try:
            for w, v in ((self.x, e.x), (self.y, e.y), (self.w, e.w), (self.h, e.h), (self.size, e.font_pt),
                         (self.border, e.border_mm), (self.padding, e.padding_mm), (self.ratio, e.symbol_ratio * 100)):
                w.setValue(v)
            self.text.setPlainText(e.text)
            self.symbol.setCurrentIndex(max(self.symbol.findData(e.symbol), 0))
            self.symbol_pos.setCurrentIndex(self.symbol_pos.findData(e.symbol_pos))
            self.font.setCurrentFont(QFont(e.font_family))
            self.bold.setChecked(e.bold); self.italic.setChecked(e.italic); self.dashed.setChecked(e.dashed)
            self.autofit.setChecked(e.auto_fit)
            self.text_color.set_color(e.text_color); self.symbol_color.set_color(e.symbol_color)
            self.border_color.set_color(e.border_color); self.bg_color.set_color(e.bg_color)
            self.align.setCurrentIndex(self.align.findData(e.align))
        finally:
            self._loading = False

    def _sync_geometry_fields(self) -> None:
        sel = self.selected_elements()
        if len(sel) != 1:
            return
        e = sel[0]
        self._loading = True
        for w, v in ((self.x, e.x), (self.y, e.y), (self.w, e.w), (self.h, e.h)):
            w.setValue(v)
        self._loading = False

    def _coalesced_undo(self, key: str) -> None:
        """One undo step per burst of edits to the same property."""
        import time
        now = time.monotonic()
        if self._last_edit[0] != key or now - self._last_edit[1] > 1.5:
            self.push_undo()
        self._last_edit = (key, now)

    def _set(self, attr: str, value) -> None:
        if self._loading:
            return
        items = self.selected_items()
        if not items:
            return
        self._coalesced_undo(attr)
        for it in items:
            setattr(it.el, attr, value)
            it.refresh()

    def _set_geom(self, attr: str, value: float) -> None:
        if self._loading:
            return
        items = self.selected_items()
        if len(items) != 1:
            return
        self._coalesced_undo("geom" + attr)
        setattr(items[0].el, attr, value)
        items[0].refresh()
