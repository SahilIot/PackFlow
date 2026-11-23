"""Dialog for adding / editing a packing instruction, with live preview."""
from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QVBoxLayout, QWidget)

from ..layout import card_from_instruction
from ..models import ALIGNMENTS, SYMBOL_POSITIONS, Instruction
from ..symbols import SYMBOLS
from .widgets import ColorButton, ElementPreview, symbol_icon


def fill_symbol_combo(combo: QComboBox, symbols: list[tuple[str, str]], current: str = "") -> None:
    combo.clear()
    combo.addItem("(no symbol)", "")
    for key, label in symbols:
        combo.addItem(symbol_icon(key, 28), label, key)
    idx = combo.findData(current)
    combo.setCurrentIndex(max(idx, 0))


class InstructionDialog(QDialog):
    def __init__(self, parent: QWidget | None, symbols: list[tuple[str, str]], instruction: Instruction | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Instruction" if instruction else "Add Instruction")
        self._ins = instruction or Instruction(name="")
        ins = self._ins

        self.name = QLineEdit(ins.name)
        self.text = QPlainTextEdit(ins.text or ("" if instruction is None else ins.name))
        self.text.setFixedHeight(76)
        self.text.setPlaceholderText("Text printed on the page (leave empty to use the name)")
        self.symbol = QComboBox()
        fill_symbol_combo(self.symbol, symbols or [(k, v[0]) for k, v in SYMBOLS.items()], ins.symbol)
        self.symbol_pos = QComboBox()
        for pos in SYMBOL_POSITIONS:
            self.symbol_pos.addItem(pos.capitalize(), pos)
        self.symbol_pos.setCurrentIndex(SYMBOL_POSITIONS.index(ins.symbol_pos))
        self.font = QFontComboBox()
        self.font.setCurrentFont(QFont(ins.font_family))
        self.size = QDoubleSpinBox(); self.size.setRange(6, 400); self.size.setSuffix(" pt"); self.size.setValue(ins.font_pt)
        self.bold = QCheckBox("Bold"); self.bold.setChecked(ins.bold)
        self.italic = QCheckBox("Italic"); self.italic.setChecked(ins.italic)
        self.align = QComboBox()
        for a in ALIGNMENTS:
            self.align.addItem(a.capitalize(), a)
        self.align.setCurrentIndex(ALIGNMENTS.index(ins.align))
        self.border = QDoubleSpinBox(); self.border.setRange(0, 10); self.border.setSingleStep(0.5)
        self.border.setSuffix(" mm"); self.border.setValue(ins.border_mm)
        self.text_color = ColorButton(ins.text_color)
        self.symbol_color = ColorButton(ins.symbol_color)
        self.border_color = ColorButton(ins.border_color)
        self.bg_color = ColorButton(ins.bg_color, allow_none=True)
        self.enabled = QCheckBox("Enabled (available for printing)"); self.enabled.setChecked(ins.enabled)

        form = QFormLayout()
        form.setVerticalSpacing(8)
        form.addRow("Name *", self.name)
        form.addRow("Printed text", self.text)
        form.addRow("Symbol", self.symbol)
        form.addRow("Symbol position", self.symbol_pos)
        form.addRow("Font", self.font)
        form.addRow("Maximum font size", self.size)
        style = QHBoxLayout(); style.addWidget(self.bold); style.addWidget(self.italic); style.addStretch()
        form.addRow("Font style", style)
        form.addRow("Text alignment", self.align)
        form.addRow("Border", self.border)
        form.addRow("Text color", self.text_color)
        form.addRow("Symbol color", self.symbol_color)
        form.addRow("Border color", self.border_color)
        form.addRow("Background", self.bg_color)
        form.addRow("", self.enabled)
        hint = QLabel("Text shrinks automatically to fit its box, so the size above is the largest it will print."); hint.setObjectName("hint"); hint.setWordWrap(True)

        self.preview = ElementPreview()
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        left = QVBoxLayout(); left.addLayout(form); left.addWidget(hint); left.addStretch()
        right = QVBoxLayout(); right.addWidget(QLabel("Preview")); right.addWidget(self.preview, 1)
        row = QHBoxLayout(); row.addLayout(left, 3); row.addLayout(right, 2)
        root = QVBoxLayout(self); root.addLayout(row); root.addWidget(buttons)
        self.resize(780, 600)

        for sig in (self.name.textChanged, self.text.textChanged, self.symbol.currentIndexChanged,
                    self.symbol_pos.currentIndexChanged, self.font.currentFontChanged, self.size.valueChanged,
                    self.bold.toggled, self.italic.toggled, self.align.currentIndexChanged, self.border.valueChanged, self.text_color.colorChanged,
                    self.symbol_color.colorChanged, self.border_color.colorChanged, self.bg_color.colorChanged):
            sig.connect(self._update_preview)
        self._update_preview()

    def _collect(self) -> Instruction:
        i = self._ins
        i.name = self.name.text().strip()
        i.text = self.text.toPlainText().strip()
        i.symbol = self.symbol.currentData() or ""
        i.symbol_pos = self.symbol_pos.currentData()
        i.font_family = self.font.currentFont().family()
        i.font_pt = self.size.value()
        i.bold, i.italic = self.bold.isChecked(), self.italic.isChecked()
        i.align = self.align.currentData()
        i.border_mm = self.border.value()
        i.enabled = self.enabled.isChecked()
        i.text_color, i.symbol_color = self.text_color.color(), self.symbol_color.color()
        i.border_color, i.bg_color = self.border_color.color(), self.bg_color.color()
        return i

    def _update_preview(self) -> None:
        i = self._collect()
        self.preview.set_element(card_from_instruction(i, 0, 0, 90, 70))

    def _accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, "Name required", "Please enter a name for the instruction.")
            return
        self.accept()

    def instruction(self) -> Instruction:
        return self._collect()
