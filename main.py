"""Machine Packing Print - application entry point."""
from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.database import Database, DatabaseError
from app.paths import data_dir, db_path, resource_path
from app.ui.main_window import MainWindow
from app.ui.styles import build_stylesheet, light_palette


def main() -> int:
    if "--selftest" in sys.argv:
        from app.selftest import run_selftest
        return run_selftest()
    if "--printer-diag" in sys.argv:
        from app.selftest import run_printer_diag
        return run_printer_diag()
    app = QApplication(sys.argv)
    app.setApplicationName("Machine Packing Print")
    app.setStyle("Fusion")
    if hasattr(app.styleHints(), "setColorScheme"):        # Qt 6.8+: ignore Windows dark mode
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(light_palette())
    app.setStyleSheet(build_stylesheet())
    app.setFont(QFont("Segoe UI", 10))
    icon = resource_path("resources", "icon.ico")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    sys.excepthook = lambda t, v, tb: QMessageBox.critical(
        None, "Unexpected error", "".join(traceback.format_exception(t, v, tb))[-1500:])
    try:
        db = Database(db_path())
    except (DatabaseError, OSError) as exc:
        QMessageBox.critical(None, "Machine Packing Print", f"The data file could not be opened:\n{exc}\n\nFolder: {data_dir()}")
        return 1
    if db.recovered_from:
        QMessageBox.warning(None, "Data file repaired",
                            f"The data file was damaged and a new one was created.\nThe old file was kept as:\n{db.recovered_from}")
    window = MainWindow(db)
    window.show()
    code = app.exec()
    db.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
