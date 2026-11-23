"""Headless self-check used to verify a packaged build: `PackFlow.exe --selftest`.

Checks database creation, layout, vector rendering to PDF and printer detection,
then writes a report to %TEMP%\\PackFlow_selftest.txt and exits 0 (pass) or 1.
"""
from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path


def run_selftest() -> int:
    report = Path(tempfile.gettempdir()) / "PackFlow_selftest.txt"
    lines: list[str] = []
    ok = True
    tmp = tempfile.mkdtemp(prefix="mpp_selftest_")
    os.environ["MPP_DATA_DIR"] = tmp          # never touch the real user data
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)          # must exist for printing and fonts
        app.processEvents()
        from . import printing
        from .database import DEFAULT_INSTRUCTIONS, Database
        from .layout import build_document
        from .models import AutoLayoutParams, Instruction
        from .paths import db_path, resource_path

        # local SQLite database is created on first start and seeded with the default instructions
        db = Database(db_path())
        n = len(db.list_instructions())
        assert n >= 10, f"database was not seeded ({n} instructions)"
        db.set_setting("copies", "3"); db.close()
        db = Database(db_path())
        assert db.get_setting("copies") == "3" and len(db.list_instructions()) == n, "data did not survive a restart"
        db.close()
        lines.append(f"local SQLite database: OK ({n} instructions, survives restart)")
        ins = [Instruction(name=n, text=n, symbol=sy, font_pt=pt, text_color=tc, symbol_color=sc, border_color=bc, id=i + 1)
               for i, (n, sy, pt, tc, sc, bc) in enumerate(DEFAULT_INSTRUCTIONS)]
        doc = build_document(ins, AutoLayoutParams())
        pdf = str(Path(tmp) / "check.pdf")
        printing.export_pdf(doc, pdf)
        size = Path(pdf).stat().st_size
        assert size > 1000, "PDF output is empty"
        lines.append(f"render to A4 PDF: OK ({len(doc.pages)} pages, {size} bytes)")
        # colour pipeline: colour mode must contain colour, grayscale / black & white must not
        from PySide6.QtGui import QColor, QImage, QPainter

        from .renderer import paint_page

        def coloured_pixels(mode: str) -> int:
            img = QImage(420, 594, QImage.Format_RGB32)
            img.fill(QColor("white"))
            qp = QPainter(img)
            qp.scale(0.2, 0.2)
            paint_page(qp, doc, doc.pages[0], mode)
            qp.end()
            return sum(1 for y in range(0, img.height(), 2) for x in range(0, img.width(), 2)
                       if (lambda c: max(c.red(), c.green(), c.blue()) - min(c.red(), c.green(), c.blue()) > 40)(
                           QColor(img.pixel(x, y))))
        counts = {m: coloured_pixels(m) for m in ("color", "grayscale", "bw")}
        assert counts["color"] > 0 and counts["grayscale"] == 0 and counts["bw"] == 0, f"colour check failed {counts}"
        lines.append(f"colour modes: OK (coloured pixels: color={counts['color']}, grayscale=0, b&w=0)")
        for m in ("color", "grayscale", "bw"):
            printing.export_pdf(doc, str(Path(tmp) / f"check_{m}.pdf"), m)
        lines.append("PDF export in all 3 colour modes: OK")
        icon = resource_path("resources", "icon.ico")
        lines.append(f"resources: {'OK' if icon.exists() else 'MISSING icon.ico'}")
        ok = ok and icon.exists()
        lines.append("printers:")
        lines.extend("  " + ln for ln in printing.diagnose())
    except Exception:  # noqa: BLE001
        ok = False
        lines.append("FAILED:\n" + traceback.format_exc())
    lines.append("RESULT: " + ("PASS" if ok else "FAIL"))
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


def run_printer_diag() -> int:
    """`--printer-diag`: list printers as the app sees them (Qt and Windows API) and test that each opens."""
    report = Path(tempfile.gettempdir()) / "PackFlow_printers.txt"
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        app.processEvents()
        from . import printing
        lines = printing.diagnose()
    except Exception:  # noqa: BLE001
        lines = ["FAILED:\n" + traceback.format_exc()]
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    try:  # packaged windowed exe has no console, so also show the result in a dialog
        from PySide6.QtWidgets import QMessageBox
        if getattr(sys, "frozen", False) and not os.environ.get("MPP_NO_DIALOG"):
            QMessageBox.information(None, "Printer diagnostics", "\n".join(lines) + f"\n\nSaved to {report}")
    except Exception:  # noqa: BLE001
        pass
    return 0
