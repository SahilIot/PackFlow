"""Template manager: use, edit layout, duplicate, rename and delete saved templates."""
from __future__ import annotations

import json
from typing import Callable

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from ..errors import DatabaseError
from ..database import Database
from ..models import Document, Template


class TemplateDialog(QDialog):
    def __init__(self, parent: QWidget | None, db: Database,
                 edit_layout: Callable[[Template], Document | None]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage Templates")
        self.db, self._edit_layout = db, edit_layout
        self.use_template_id: int | None = None
        self.changed = False

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _i: self._use())
        self.list.currentItemChanged.connect(lambda *_: self._update_info())
        self.info = QLabel(); self.info.setObjectName("hint"); self.info.setWordWrap(True)

        def btn(text: str, fn, name: str = "") -> QPushButton:
            b = QPushButton(text); b.clicked.connect(fn)
            if name: b.setObjectName(name)
            return b

        side = QVBoxLayout()
        for b in (btn("Use Template", self._use, "primary"), btn("Edit Layout…", self._edit),
                  btn("Duplicate", self._duplicate), btn("Rename…", self._rename), btn("Delete", self._delete, "danger")):
            side.addWidget(b)
        side.addStretch(); side.addWidget(btn("Close", self.accept))
        row = QHBoxLayout(); row.addWidget(self.list, 1); row.addLayout(side)
        root = QVBoxLayout(self); root.addLayout(row, 1); root.addWidget(self.info)
        self.resize(560, 380)
        self._reload()

    def _reload(self, select_id: int | None = None) -> None:
        self.list.clear()
        for t in self.db.list_templates():
            it = QListWidgetItem(t.name + ("   (custom layout)" if t.document else ""))
            it.setData(0x100, t.id)
            self.list.addItem(it)
            if t.id == select_id:
                self.list.setCurrentItem(it)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self._update_info()

    def _current(self) -> Template | None:
        it = self.list.currentItem()
        return self.db.get_template(it.data(0x100)) if it else None

    def _update_info(self) -> None:
        t = self._current()
        if not t:
            self.info.setText("")
            return
        layout = "custom A4 layout" if t.document else "automatic layout"
        orient = t.document.orientation if t.document else t.params.orientation
        self.info.setText(f"{len(t.instruction_ids)} instruction(s) · {layout} · {orient}")

    def _use(self) -> None:
        t = self._current()
        if t:
            self.use_template_id = t.id
            self.accept()

    def _edit(self) -> None:
        t = self._current()
        if not t:
            return
        doc = self._edit_layout(t)
        if doc is not None:
            t.document = doc
            t.params.orientation = doc.orientation
            self._save(t)

    def _duplicate(self) -> None:
        t = self._current()
        if not t:
            return
        name, ok = QInputDialog.getText(self, "Duplicate template", "Name for the copy:", text=f"{t.name} (copy)")
        if ok and name.strip():
            t.id, t.name = None, name.strip()
            if t.document:
                t.document = Document.from_dict(json.loads(json.dumps(t.document.to_dict())))
            self._save(t)

    def _rename(self) -> None:
        t = self._current()
        if not t:
            return
        name, ok = QInputDialog.getText(self, "Rename template", "New name:", text=t.name)
        if ok and name.strip():
            t.name = name.strip()
            self._save(t)

    def _delete(self) -> None:
        t = self._current()
        if t and QMessageBox.question(self, "Delete template", f"Delete the template '{t.name}'?\nThis cannot be undone.",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                self.db.delete_template(t.id)  # type: ignore[arg-type]
            except DatabaseError as exc:
                QMessageBox.warning(self, "Template not deleted", str(exc))
                self._reload()
                return
            self.changed = True
            self._reload()

    def _save(self, t: Template) -> None:
        try:
            tid = self.db.save_template(t)
        except DatabaseError as exc:
            QMessageBox.warning(self, "Template not saved", str(exc))
            self._reload()
            return
        self.changed = True
        self._reload(tid)
