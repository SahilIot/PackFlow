"""Main window: the whole print workflow on one screen."""
from __future__ import annotations

import json

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtPrintSupport import QPrintPreviewDialog
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)

from .. import __version__, printing
from ..database import Database, DatabaseError
from ..layout import build_document
from ..models import COLOR_MODES, AutoLayoutParams, Document, Instruction, Template
from .instruction_dialog import InstructionDialog
from .layout_editor import LayoutEditor
from .template_dialog import TemplateDialog
from .widgets import PagePreview, symbol_icon

ID_ROLE = Qt.UserRole
PER_PAGE_CHOICES = [("Automatic", 0), ("1 per page", 1), ("2 per page", 2), ("4 per page", 4), ("6 per page", 6),
                    ("8 per page", 8), ("9 per page", 9)]


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle("Machine Packing Print")
        self.instructions: list[Instruction] = []
        self.custom_doc: Document | None = None     # None = automatic layout
        self.custom_name = ""
        self._printers: list[printing.PrinterEntry] = []
        self._wanted_color = "color"
        self._scan = printing.PrinterScan()
        self._switch_note = ""
        self._page = 0
        self._busy = False

        self._build_ui()
        self.reload_instructions(restore_selection=True)
        self.reload_templates()
        self.refresh_printers()
        self._restore_settings()
        self.refresh_preview()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        def btn(text: str, fn, name: str = "") -> QPushButton:
            b = QPushButton(text); b.clicked.connect(fn)
            if name: b.setObjectName(name)
            return b

        def card(title: str) -> tuple[QFrame, QVBoxLayout]:
            frame = QFrame(); frame.setObjectName("card")
            lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 14); lay.setSpacing(10)
            t = QLabel(title); t.setObjectName("cardTitle"); lay.addWidget(t)
            return frame, lay

        def label(text: str) -> QLabel:
            l = QLabel(text); l.setObjectName("fieldLabel"); return l

        # ---- left card: instructions
        self.search = QLineEdit(); self.search.setPlaceholderText("Search instructions by name…")
        self.search.setClearButtonEnabled(True); self.search.textChanged.connect(self.apply_filter)
        self.list = QListWidget(); self.list.setIconSize(QSize(30, 30)); self.list.setUniformItemSizes(True)
        self.list.itemChanged.connect(self._item_changed)
        self.list.itemDoubleClicked.connect(lambda _i: self.edit_instruction())
        self.list.currentItemChanged.connect(lambda *_: self._update_count())
        self.count_label = QLabel(); self.count_label.setObjectName("status")
        self.toggle_btn = btn("Disable", self.toggle_enabled)
        selrow = QHBoxLayout(); selrow.setSpacing(8)
        selrow.addWidget(btn("Select All", self.select_all)); selrow.addWidget(btn("Deselect All", self.deselect_all))
        selrow.addStretch(); selrow.addWidget(self.count_label)
        manage = QHBoxLayout(); manage.setSpacing(8)
        for b in (btn("Add Instruction", self.add_instruction, "primary"), btn("Edit", self.edit_instruction),
                  self.toggle_btn, btn("Delete", self.delete_instruction, "danger")):
            manage.addWidget(b)
        left, lv = card("Packing Instructions")
        lv.addWidget(self.search); lv.addLayout(selrow); lv.addWidget(self.list, 1); lv.addLayout(manage)

        # ---- right card 1: preview
        self.preview = PagePreview()
        self.page_label = QLabel(); self.page_label.setAlignment(Qt.AlignCenter); self.page_label.setObjectName("status")
        self.prev_btn = btn("‹  Previous", lambda: self._go_page(-1), "nav")
        self.next_btn = btn("Next  ›", lambda: self._go_page(1), "nav")
        nav = QHBoxLayout(); nav.addWidget(self.prev_btn); nav.addWidget(self.page_label, 1); nav.addWidget(self.next_btn)
        pv_card, pv = card("A4 Page Preview")
        pv.addWidget(self.preview, 1); pv.addLayout(nav)

        # ---- right card 2: print settings
        self.template_combo = QComboBox(); self.template_combo.activated.connect(self._template_chosen)
        self.paper = QLabel("A4  (210 × 297 mm)"); self.paper.setObjectName("value")
        self.orient = QComboBox(); self.orient.addItem("Portrait", "portrait"); self.orient.addItem("Landscape", "landscape")
        self.orient.currentIndexChanged.connect(self._layout_option_changed)
        self.per_page = QComboBox()
        for text, v in PER_PAGE_CHOICES: self.per_page.addItem(text, v)
        self.per_page.currentIndexChanged.connect(self._layout_option_changed)
        self.color_combo = QComboBox()
        for key, text in COLOR_MODES: self.color_combo.addItem(text, key)
        self.color_combo.currentIndexChanged.connect(self._color_changed)
        self.color_note = QLabel(); self.color_note.setObjectName("hint"); self.color_note.setWordWrap(True)
        self.layout_label = QLabel(); self.layout_label.setObjectName("hint"); self.layout_label.setWordWrap(True)
        self.reset_btn = btn("Back to Automatic", self.reset_to_auto)
        self.printer_combo = QComboBox(); self.printer_combo.currentIndexChanged.connect(self._printer_changed)
        self.printer_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.printer_combo.setMinimumContentsLength(18)
        self.printer_label = QLabel(); self.printer_label.setObjectName("hint"); self.printer_label.setWordWrap(True); self.printer_label.setMinimumHeight(44)
        self.copies = QSpinBox(); self.copies.setRange(1, 999); self.copies.setValue(1); self.copies.setFixedWidth(110)
        self.copies.valueChanged.connect(lambda v: self.db.set_setting("copies", v))

        st_card, sv = card("Print Settings")
        g = QGridLayout(); g.setHorizontalSpacing(10); g.setVerticalSpacing(8)
        g.addWidget(label("Template"), 0, 0); g.addWidget(self.template_combo, 0, 1, 1, 3)
        tb = QHBoxLayout(); tb.setSpacing(8); tb.addWidget(btn("Save…", self.save_template)); tb.addWidget(btn("Manage…", self.manage_templates))
        g.addLayout(tb, 0, 4)
        g.addWidget(label("Paper size"), 1, 0); g.addWidget(self.paper, 1, 1)
        g.addWidget(label("Orientation"), 1, 2); g.addWidget(self.orient, 1, 3, 1, 2)
        g.addWidget(label("Per page"), 2, 0); g.addWidget(self.per_page, 2, 1)
        g.addWidget(label("Copies"), 2, 2); cr = QHBoxLayout(); cr.addWidget(self.copies); cr.addStretch(); g.addLayout(cr, 2, 3, 1, 2)
        g.addWidget(label("Print color"), 3, 0); g.addWidget(self.color_combo, 3, 1)
        g.addWidget(self.color_note, 3, 2, 1, 3)
        g.addWidget(label("Layout"), 4, 0)
        lr = QHBoxLayout(); lr.setSpacing(8); lr.addWidget(btn("Customize Layout…", self.open_editor)); lr.addWidget(self.reset_btn)
        lr.addWidget(self.layout_label, 1); g.addLayout(lr, 4, 1, 1, 4)
        g.addWidget(label("Printer"), 5, 0); g.addWidget(self.printer_combo, 5, 1, 1, 3)
        g.addWidget(btn("Refresh Printers", self.refresh_printers), 5, 4)
        g.addWidget(self.printer_label, 6, 1, 1, 4)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)
        sv.addLayout(g)

        self.preview_btn = btn("A4 Print Preview", self.show_preview, "big")
        self.print_btn = btn("PRINT", self.print_now, "print")
        actions = QHBoxLayout(); actions.setSpacing(10); actions.addWidget(self.preview_btn); actions.addWidget(self.print_btn, 1)

        right = QVBoxLayout(); right.setSpacing(12)
        right.addWidget(pv_card, 1); right.addWidget(st_card); right.addLayout(actions)
        root = QHBoxLayout(); root.setContentsMargins(14, 14, 14, 10); root.setSpacing(14)
        root.addWidget(left, 4); root.addLayout(right, 6)
        central = QWidget(); central.setLayout(root); self.setCentralWidget(central)

        ver = QLabel(f"v{__version__}"); self.statusBar().addPermanentWidget(ver)
        self.statusBar().showMessage("Ready")
        hint = central.minimumSizeHint()   # never let the window shrink below what the controls need
        self.setMinimumSize(max(1000, hint.width() + 20), hint.height() + self.statusBar().sizeHint().height() + 4)
        self.resize(1200, max(860, self.minimumHeight()))

    # --------------------------------------------------------- settings io
    def _restore_settings(self) -> None:
        g = self.db.get_setting
        self.copies.setValue(int(g("copies", "1")))
        self.orient.blockSignals(True); self.per_page.blockSignals(True)
        self.orient.setCurrentIndex(max(self.orient.findData(g("orientation", "portrait")), 0))
        self.per_page.setCurrentIndex(max(self.per_page.findData(int(g("per_page", "0"))), 0))
        self.orient.blockSignals(False); self.per_page.blockSignals(False)
        self._wanted_color = g("color_mode", "color") or "color"
        self._set_color_mode(self._wanted_color)
        self._update_color_capability()
        geo = g("window_geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromHex(geo.encode()))
        self._update_layout_ui()

    def closeEvent(self, event) -> None:
        self.db.set_setting("window_geometry", bytes(self.saveGeometry().toHex()).decode())
        self._save_selection()
        super().closeEvent(event)

    def _save_selection(self) -> None:
        self.db.set_setting("selected_ids", json.dumps(sorted(self.checked_ids())))

    # --------------------------------------------------------- instructions
    def reload_instructions(self, restore_selection: bool = False, keep: set[int] | None = None) -> None:
        if restore_selection:
            keep = set(json.loads(self.db.get_setting("selected_ids", "[]") or "[]"))
        elif keep is None:
            keep = self.checked_ids()
        self.instructions = self.db.list_instructions()
        self.list.blockSignals(True)
        self.list.clear()
        for ins in self.instructions:
            label = ins.name if ins.enabled else f"{ins.name}   (disabled)"
            it = QListWidgetItem(symbol_icon(ins.symbol, 60, ins.symbol_color) if ins.symbol else symbol_icon("", 60), label)
            it.setData(ID_ROLE, ins.id)
            it.setSizeHint(QSize(0, 46))
            if ins.enabled:
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if ins.id in keep else Qt.Unchecked)
            else:
                it.setFlags(it.flags() & ~Qt.ItemIsUserCheckable)
                it.setForeground(QColor("#98a2ae"))
            self.list.addItem(it)
        self.list.blockSignals(False)
        self.apply_filter()
        self._update_count()

    def apply_filter(self) -> None:
        q = self.search.text().strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            ins = self._ins_by_id(it.data(ID_ROLE))
            it.setHidden(bool(q) and ins is not None and q not in f"{ins.name} {ins.text}".lower())

    def _ins_by_id(self, ins_id: int) -> Instruction | None:
        return next((i for i in self.instructions if i.id == ins_id), None)

    def checked_ids(self) -> set[int]:
        out = set()
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable and it.checkState() == Qt.Checked:
                out.add(it.data(ID_ROLE))
        return out

    def selected_instructions(self) -> list[Instruction]:
        ids = self.checked_ids()
        return [i for i in self.instructions if i.id in ids and i.enabled]

    def _current_instruction(self) -> Instruction | None:
        it = self.list.currentItem()
        return self._ins_by_id(it.data(ID_ROLE)) if it else None

    def _item_changed(self, _item) -> None:
        self._selection_edited()

    def _selection_edited(self) -> None:
        """Checkbox change: an edited selection means automatic layout again."""
        if self.custom_doc is not None:
            self.custom_doc = None
            self.statusBar().showMessage("Selection changed - switched back to automatic layout.", 5000)
        self._update_count(); self._update_layout_ui(); self.refresh_preview(); self._save_selection()

    def _set_all(self, state: Qt.CheckState) -> None:
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            it = self.list.item(i)
            if not it.isHidden() and it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(state)
        self.list.blockSignals(False)
        self._selection_edited()

    def select_all(self) -> None: self._set_all(Qt.Checked)
    def deselect_all(self) -> None: self._set_all(Qt.Unchecked)

    def _update_count(self) -> None:
        n = len(self.selected_instructions())
        self.count_label.setText(f"{n} selected")
        cur = self._current_instruction()
        self.toggle_btn.setText("Enable" if cur and not cur.enabled else "Disable")

    def _symbols(self) -> list[tuple[str, str]]:
        return self.db.symbol_config()

    def add_instruction(self) -> None:
        self._edit_dialog(None)

    def edit_instruction(self) -> None:
        cur = self._current_instruction()
        if cur is None:
            QMessageBox.information(self, "Edit instruction", "Select an instruction in the list first.")
            return
        self._edit_dialog(cur)

    def _edit_dialog(self, ins: Instruction | None) -> None:
        dlg = InstructionDialog(self, self._symbols(), ins)
        while dlg.exec() == InstructionDialog.Accepted:
            try:
                new_id = self.db.save_instruction(dlg.instruction())
            except DatabaseError as exc:
                QMessageBox.warning(self, "Instruction", str(exc))
                continue
            keep = self.checked_ids() | ({new_id} if ins is None else set())
            self.reload_instructions(keep=keep)
            self._selection_edited()
            break

    def toggle_enabled(self) -> None:
        cur = self._current_instruction()
        if cur is None:
            return
        row = self.list.currentRow()
        self.db.set_instruction_enabled(cur.id, not cur.enabled)  # type: ignore[arg-type]
        self.reload_instructions()
        self.list.setCurrentRow(row)       # keep the row selected so the button flips to Enable/Disable
        self._selection_edited()

    def delete_instruction(self) -> None:
        cur = self._current_instruction()
        if cur is None:
            return
        if QMessageBox.question(self, "Delete instruction",
                                f"Delete the instruction '{cur.name}'?\nThis cannot be undone.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_instruction(cur.id)  # type: ignore[arg-type]
            self.reload_instructions()
            self._selection_edited()

    # ------------------------------------------------------------ layout
    # ------------------------------------------------------------- print color
    def color_mode(self) -> str:
        return self.color_combo.currentData() or "color"

    def _set_color_mode(self, mode: str) -> None:
        self.color_combo.blockSignals(True)
        self.color_combo.setCurrentIndex(max(self.color_combo.findData(mode), 0))
        self.color_combo.blockSignals(False)

    def _color_changed(self) -> None:
        self._wanted_color = self.color_mode()      # remember what the user asked for
        self.db.set_setting("color_mode", self._wanted_color)
        self.refresh_preview()

    def _update_color_capability(self) -> None:
        """Enable/disable colour according to what the selected printer's driver reports."""
        entry = next((p for p in self._printers if p.name == self.printer_combo.currentData()), None)
        supported = entry.color_supported if entry else None
        color_item = self.color_combo.model().item(self.color_combo.findData("color"))
        color_item.setEnabled(supported is not False)
        if supported is False:
            note = f"{entry.name} does not support color. Printing in grayscale."
            self._set_color_mode("grayscale" if self._wanted_color == "color" else self._wanted_color)
        else:
            self._set_color_mode(self._wanted_color)
            note = ("Color printing is available." if supported else
                    "The driver does not report color support." if entry else "No printer selected: preview only.")
        self.color_note.setObjectName("notice" if supported is False else "hint")
        self._restyle(self.color_note)
        self.color_note.setText(note)
        self.refresh_preview()

    def params(self) -> AutoLayoutParams:
        return AutoLayoutParams(orientation=self.orient.currentData(), per_page=self.per_page.currentData(),
                                color_mode=self.color_mode())

    def effective_document(self) -> Document:
        if self.custom_doc is not None:
            return self.custom_doc
        return build_document(self.selected_instructions(), self.params())

    def _layout_option_changed(self) -> None:
        self.db.set_setting("orientation", self.orient.currentData())
        self.db.set_setting("per_page", self.per_page.currentData())
        self.refresh_preview()

    def _update_layout_ui(self) -> None:
        custom = self.custom_doc is not None
        self.orient.setEnabled(not custom); self.per_page.setEnabled(not custom); self.reset_btn.setVisible(custom)
        self.layout_label.setText(f"Custom layout: {self.custom_name or 'edited'}" if custom else
                                  "Automatic: sized to fill the page.")

    def reset_to_auto(self) -> None:
        self.custom_doc = None
        self._update_layout_ui(); self.refresh_preview()

    def refresh_preview(self) -> None:
        doc = self.effective_document()
        self._page = min(self._page, len(doc.pages) - 1)
        self.preview.set_document(doc, self._page, self.color_mode())
        total = len(doc.pages)
        empty = not any(p.elements for p in doc.pages)
        self.page_label.setText("Nothing selected" if empty else f"Page {self._page + 1} of {total}")
        self.prev_btn.setEnabled(self._page > 0); self.next_btn.setEnabled(self._page < total - 1)
        self._update_print_enabled(empty)

    def _go_page(self, d: int) -> None:
        self._page += d
        self.refresh_preview()

    def open_editor(self) -> None:
        doc = self._run_editor(self.effective_document(), self.selected_instructions_or_all())
        if doc is not None:
            self.custom_doc = doc
            self.custom_name = self.custom_name if self.custom_name and self.custom_doc else "edited"
            self._update_layout_ui(); self.refresh_preview()

    def selected_instructions_or_all(self) -> list[Instruction]:
        return self.instructions

    def _run_editor(self, doc: Document, instructions: list[Instruction], save_cb=None) -> Document | None:
        ed = LayoutEditor(self, doc, instructions, self._symbols(), self._show_preview_for,
                          save_cb or self._save_template_for)
        return ed.document() if ed.exec() == LayoutEditor.Accepted else None

    # ---------------------------------------------------------- templates
    def reload_templates(self, select_id: int | None = None) -> None:
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("(no template)", None)
        for t in self.db.list_templates():
            self.template_combo.addItem(t.name, t.id)
        idx = self.template_combo.findData(select_id) if select_id else 0
        self.template_combo.setCurrentIndex(max(idx, 0))
        self.template_combo.blockSignals(False)

    def _template_chosen(self) -> None:
        tid = self.template_combo.currentData()
        if tid is not None:
            t = self.db.get_template(tid)
            if t:
                self.apply_template(t)

    def apply_template(self, t: Template) -> None:
        valid = {i.id for i in self.instructions if i.enabled}
        ids = [i for i in t.instruction_ids if i in valid]
        self.list.blockSignals(True)
        for r in range(self.list.count()):
            it = self.list.item(r)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Checked if it.data(ID_ROLE) in ids else Qt.Unchecked)
        self.list.blockSignals(False)
        self.orient.blockSignals(True); self.per_page.blockSignals(True)
        self.orient.setCurrentIndex(max(self.orient.findData(t.params.orientation), 0))
        self.per_page.setCurrentIndex(max(self.per_page.findData(t.params.per_page), 0))
        self.orient.blockSignals(False); self.per_page.blockSignals(False)
        if t.params.color_mode:
            self._wanted_color = t.params.color_mode
            self.db.set_setting("color_mode", self._wanted_color)
            self._update_color_capability()
        self.custom_doc = Document.from_dict(t.document.to_dict()) if t.document else None
        self.custom_name = t.name
        self._page = 0
        missing = len(t.instruction_ids) - len(ids)
        self._update_count(); self._update_layout_ui(); self.refresh_preview(); self._save_selection()
        self.statusBar().showMessage(f"Template '{t.name}' loaded" + (f" ({missing} unavailable instruction(s) skipped)" if missing else ""), 6000)

    def _template_from_state(self, name: str, doc: Document | None) -> Template:
        params = self.params()
        if doc is not None:
            params.orientation = doc.orientation
        return Template(name=name, instruction_ids=[i.id for i in self.selected_instructions()],  # type: ignore[misc]
                        params=params, document=doc)

    def save_template(self) -> None:
        self._save_template_for(self.custom_doc)

    def _save_template_for(self, doc: Document | None) -> None:
        current = self.template_combo.currentText() if self.template_combo.currentData() else ""
        name, ok = QInputDialog.getText(self, "Save template", "Template name:", text=current)
        name = name.strip()
        if not ok or not name:
            return
        t = self._template_from_state(name, doc)
        existing = next((x for x in self.db.list_templates() if x.name.lower() == name.lower()), None)
        if existing:
            if QMessageBox.question(self, "Save template", f"A template named '{existing.name}' already exists. Replace it?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            t.id = existing.id
        try:
            tid = self.db.save_template(t)
        except DatabaseError as exc:
            QMessageBox.warning(self, "Template", str(exc)); return
        self.custom_name = name
        self.reload_templates(tid)
        self.statusBar().showMessage(f"Template '{name}' saved", 5000)

    def manage_templates(self) -> None:
        dlg = TemplateDialog(self, self.db, self._edit_template_layout)
        dlg.exec()
        current = self.template_combo.currentData()
        self.reload_templates(current)
        if dlg.use_template_id:
            t = self.db.get_template(dlg.use_template_id)
            if t:
                self.reload_templates(t.id)
                self.apply_template(t)

    def _edit_template_layout(self, t: Template) -> Document | None:
        valid = {i.id: i for i in self.instructions if i.enabled}
        doc = t.document or build_document([valid[i] for i in t.instruction_ids if i in valid], t.params)
        return self._run_editor(doc, self.instructions, save_cb=self._save_template_for)

    # ------------------------------------------------------------ printers
    def refresh_printers(self) -> None:
        """Fresh enumeration of the printers installed in Windows; keeps the selected printer if it still exists."""
        wanted = self.printer_combo.currentData() or self.db.get_setting("printer")
        self._switch_note = ""
        try:
            self._scan = printing.list_printers()
        except Exception as exc:  # noqa: BLE001 - never crash on a broken print spooler
            self._scan = printing.PrinterScan(errors=[f"Printer enumeration failed: {exc}"])
        scan = self._scan
        self._printers = scan.printers
        self.printer_combo.blockSignals(True)
        self.printer_combo.clear()
        for p in self._printers:
            text = p.name + ("  (default)" if p.is_default else "") + ("" if p.available else "  - unavailable")
            self.printer_combo.addItem(text, p.name)
        if not self._printers:
            self.printer_combo.addItem("Print Spooler not running" if scan.spooler_down else "No printers installed", None)
        self.printer_combo.setEnabled(bool(self._printers))
        names = [p.name for p in self._printers]
        if wanted in names:
            pick = wanted
        else:
            pick = scan.default if scan.default in names else (names[0] if names else None)
            if wanted and pick:   # never switch silently
                self._switch_note = f"Printer '{wanted}' is no longer available. Selected '{pick}' instead - please check."
        if pick:
            self.printer_combo.setCurrentIndex(self.printer_combo.findData(pick))
        self.printer_combo.blockSignals(False)
        self._printer_changed(save=not self._switch_note and bool(pick))

    @staticmethod
    def _restyle(w: QWidget) -> None:
        w.style().unpolish(w)
        w.style().polish(w)

    def _printer_changed(self, *_args, save: bool = True) -> None:
        name = self.printer_combo.currentData()
        entry = next((p for p in self._printers if p.name == name), None)
        scan = self._scan
        msg, warn = scan.summary(), entry is None
        if entry is not None:
            msg += f" {entry.name} selected."
            if not entry.available:
                msg += f" Printer is unavailable: {entry.detail or 'check power, cable and paper.'}"
                warn = True
            if save:
                self.db.set_setting("printer", entry.name)
        if self._switch_note:
            msg, warn = f"{self._switch_note}\n{msg}", True
        if scan.errors and entry is not None and scan.qt_count != scan.win_count and scan.win_count:
            msg += f" (Qt sees {scan.qt_count}, Windows sees {scan.win_count} printers.)"
        self.printer_label.setObjectName("notice" if warn else "hint")
        self._restyle(self.printer_label)
        self.printer_label.setText(msg)
        self.printer_label.setToolTip("\n".join(
            [f"Qt printers: {scan.qt_count}", f"Windows spooler printers: {scan.win_count}", *scan.errors]))
        self._update_print_enabled()
        if hasattr(self, "color_combo") and hasattr(self, "_wanted_color"):
            self._update_color_capability()

    def _update_print_enabled(self, empty: bool | None = None) -> None:
        if empty is None:
            empty = not any(p.elements for p in self.effective_document().pages)
        self.print_btn.setEnabled(not empty and self.printer_combo.currentData() is not None)
        self.preview_btn.setEnabled(not empty)

    # ------------------------------------------------------ preview / print
    def _show_preview_for(self, doc: Document) -> None:
        mode = self.color_mode()
        if not any(p.elements for p in doc.pages):
            QMessageBox.information(self, "Preview", "There is nothing to preview. Select at least one instruction.")
            return
        try:
            printer = printing.create_printer(self.printer_combo.currentData(), doc.orientation, self.copies.value(), mode)
        except printing.PrintError:
            printer = printing.create_printer(None, doc.orientation, self.copies.value(), mode)  # preview works without the printer
        dlg = QPrintPreviewDialog(printer, self)
        dlg.setWindowTitle("A4 Print Preview")
        dlg.resize(1000, 760)

        def paint(pr) -> None:
            try:
                printing.configure(pr, doc.orientation, self.copies.value(), mode)
                printing.render_document(pr, doc, 1, mode)
            except printing.PrintError as exc:
                QMessageBox.warning(dlg, "Preview", str(exc))
        dlg.paintRequested.connect(paint)
        dlg.exec()

    def show_preview(self) -> None:
        self._show_preview_for(self.effective_document())

    def print_now(self) -> None:
        if self._busy:
            return
        doc = self.effective_document()
        name, copies, mode = self.printer_combo.currentData(), self.copies.value(), self.color_mode()
        if name is None:
            QMessageBox.warning(self, "Print", "No printer is selected."); return
        self._busy = True
        self.print_btn.setEnabled(False)
        try:
            printer = printing.create_printer(name, doc.orientation, copies, mode)
            warnings = printing.clipping_warnings(doc, printer)
            if warnings and QMessageBox.warning(
                    self, "Check margins", "\n\n".join(warnings) + "\n\nPrint anyway?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            notes = printing.render_document(printer, doc, copies, mode)
            pages = len(doc.pages)
            label = dict((k, t) for k, t in COLOR_MODES)[mode]
            self.statusBar().showMessage(f"Sent {pages} page(s) x {copies} cop{'y' if copies == 1 else 'ies'} to {name} ({label})", 8000)
            if notes:
                QMessageBox.warning(self, "Printer color setting", "\n\n".join(notes))
        except printing.PrintError as exc:
            QMessageBox.critical(self, "Printing failed", str(exc))
        except Exception as exc:  # noqa: BLE001 - surface any driver problem clearly
            QMessageBox.critical(self, "Printing failed", f"Unexpected printer problem:\n{exc}")
        finally:
            self._busy = False
            self._update_print_enabled()
