
from __future__ import annotations

from pathlib import Path

from ..paths import resource_path

TEXT = "#1b2733"
MUTED = "#5b6878"
DISABLED = "#98a2ae"
BG = "#eef1f5"
PANEL = "#ffffff"
BORDER = "#c5cdd8"
PRIMARY = "#1f5fa8"
PRIMARY_HOVER = "#2a6fbd"
PRIMARY_DARK = "#174a85"
ACCENT = "#1c8c4a"
ACCENT_HOVER = "#22a156"
ACCENT_DARK = "#14693a"
DANGER = "#b3261e"
SELECT_BG = "#e1ecf9"
HOVER_BG = "#f1f5fa"
RADIUS = "6px"


def _url(name: str) -> str:
    path: Path = resource_path("resources", "icons", name)
    return f'url("{path.as_posix()}")'


def build_stylesheet() -> str:
    return f"""
* {{ font-family: "Segoe UI", "Arial", sans-serif; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#card, QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; }}
QLabel {{ background: transparent; color: {TEXT}; }}
QLabel#cardTitle {{ font-size: 11pt; font-weight: 600; color: {TEXT}; }}
QLabel#fieldLabel {{ color: {MUTED}; font-weight: 600; }}
QLabel#hint {{ color: {MUTED}; }}
QLabel#status {{ color: {TEXT}; font-weight: 600; }}
QLabel#value {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {RADIUS}; padding: 5px 10px; color: {TEXT}; }}
QLabel#notice {{ background: #fff6e0; border: 1px solid #ecd28a; border-radius: {RADIUS}; padding: 6px 10px; color: #5c4400; min-height: 36px; }}

/* ---- push buttons ---- */
QPushButton {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS};
    padding: 0 14px; min-height: 32px; }}
QPushButton:hover {{ background: {HOVER_BG}; border-color: {PRIMARY}; color: {TEXT}; }}
QPushButton:pressed {{ background: {SELECT_BG}; color: {TEXT}; }}
QPushButton:focus {{ border: 1px solid {PRIMARY}; }}
QPushButton:disabled {{ background: #f1f3f6; color: {DISABLED}; border-color: #dde2e9; }}
QPushButton#primary {{ background: {PRIMARY}; color: #ffffff; border: 1px solid {PRIMARY_DARK}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {PRIMARY_HOVER}; color: #ffffff; }}
QPushButton#primary:pressed {{ background: {PRIMARY_DARK}; color: #ffffff; }}
QPushButton#primary:disabled {{ background: #a9bfd8; color: #f4f7fb; border-color: #a9bfd8; }}
QPushButton#danger {{ color: {DANGER}; }}
QPushButton#danger:hover {{ background: #fdeceb; border-color: {DANGER}; color: {DANGER}; }}
QPushButton#danger:disabled {{ color: {DISABLED}; }}
QPushButton#print {{ background: {ACCENT}; color: #ffffff; border: 1px solid {ACCENT_DARK}; font-size: 14pt;
    font-weight: 700; min-height: 46px; padding: 0 28px; }}
QPushButton#print:hover {{ background: {ACCENT_HOVER}; color: #ffffff; }}
QPushButton#print:pressed {{ background: {ACCENT_DARK}; color: #ffffff; }}
QPushButton#print:disabled {{ background: #b9c4be; color: #f6f6f6; border-color: #b9c4be; }}
QPushButton#big {{ min-height: 46px; font-weight: 600; padding: 0 20px; }}
QPushButton#nav {{ min-width: 110px; }}

/* ---- tool buttons / toolbar / menus ---- */
QToolBar {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: {RADIUS}; spacing: 4px; padding: 3px; }}
QToolButton {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS}; padding: 5px 9px; }}
QToolButton:hover {{ background: {HOVER_BG}; border-color: {PRIMARY}; color: {TEXT}; }}
QToolButton:pressed {{ background: {SELECT_BG}; }}
QToolButton:disabled {{ color: {DISABLED}; }}
QToolButton::menu-indicator {{ image: none; width: 0px; }}
QMenu {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; color: {TEXT}; background: transparent; }}
QMenu::item:selected {{ background: {SELECT_BG}; color: {TEXT}; }}
QMenu::item:disabled {{ color: {DISABLED}; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}

/* ---- text inputs ---- */
QLineEdit, QPlainTextEdit {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS};
    padding: 5px 8px; selection-background-color: {SELECT_BG}; selection-color: {TEXT}; }}
QLineEdit {{ min-height: 22px; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {PRIMARY}; }}
QLineEdit:disabled, QPlainTextEdit:disabled {{ background: #f1f3f6; color: {DISABLED}; }}

/* ---- combo boxes ---- */
QComboBox, QFontComboBox {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS};
    padding: 4px 30px 4px 8px; min-height: 24px; }}
QComboBox:hover, QFontComboBox:hover {{ border-color: {PRIMARY}; }}
QComboBox:focus, QFontComboBox:focus {{ border: 1px solid {PRIMARY}; }}
QComboBox:disabled, QFontComboBox:disabled {{ background: #f1f3f6; color: {DISABLED}; }}
QComboBox::drop-down, QFontComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
    width: 26px; border: none; border-left: 1px solid {BORDER}; border-top-right-radius: {RADIUS}; border-bottom-right-radius: {RADIUS}; }}
QComboBox::down-arrow, QFontComboBox::down-arrow {{ image: {_url("arrow_down.png")}; width: 12px; height: 12px; }}
QComboBox::down-arrow:disabled, QFontComboBox::down-arrow:disabled {{ image: {_url("arrow_down_disabled.png")}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER};
    selection-background-color: {SELECT_BG}; selection-color: {TEXT}; outline: 0; }}

/* ---- spin boxes ---- */
QSpinBox, QDoubleSpinBox {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS};
    padding: 4px 28px 4px 8px; min-height: 24px; selection-background-color: {SELECT_BG}; selection-color: {TEXT}; }}
QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {PRIMARY}; }}
QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: #f1f3f6; color: {DISABLED}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 24px;
    border-left: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; border-top-right-radius: {RADIUS}; background: {BG}; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 24px;
    border-left: 1px solid {BORDER}; border-bottom-right-radius: {RADIUS}; background: {BG}; }}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {SELECT_BG}; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: {_url("arrow_up.png")}; width: 10px; height: 10px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: {_url("arrow_down.png")}; width: 10px; height: 10px; }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{ image: {_url("arrow_up_disabled.png")}; }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ image: {_url("arrow_down_disabled.png")}; }}

/* ---- check boxes ---- */
QCheckBox {{ color: {TEXT}; spacing: 8px; background: transparent; }}
QCheckBox:disabled {{ color: {DISABLED}; }}
QCheckBox::indicator, QListWidget::indicator {{ width: 18px; height: 18px; }}
QCheckBox::indicator:unchecked, QListWidget::indicator:unchecked {{ border: 2px solid #7d8b9a; border-radius: 4px; background: {PANEL}; }}
QCheckBox::indicator:unchecked:hover, QListWidget::indicator:unchecked:hover {{ border-color: {PRIMARY}; }}
QCheckBox::indicator:checked, QListWidget::indicator:checked {{ border: 2px solid {PRIMARY}; border-radius: 4px;
    background: {PRIMARY}; image: {_url("check.png")}; }}
QCheckBox::indicator:disabled {{ border-color: #c9d0d9; background: #f1f3f6; }}

/* ---- instruction list ---- */
QListWidget {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS}; outline: 0; }}
QListWidget::item {{ color: {TEXT}; background: transparent; padding: 4px 8px; border-bottom: 1px solid #eef1f5; }}
QListWidget::item:hover {{ background: {HOVER_BG}; color: {TEXT}; }}
QListWidget::item:selected, QListWidget::item:selected:active, QListWidget::item:selected:!active {{
    background: {SELECT_BG}; color: {TEXT}; }}
QListWidget::item:disabled {{ color: {DISABLED}; }}

/* ---- scroll bars ---- */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #c3cbd6; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #a9b3c0; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #c3cbd6; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

/* ---- group boxes (editor side panels) ---- */
QGroupBox {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; margin-top: 14px; padding: 12px 8px 8px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {TEXT}; font-weight: 600; background: {PANEL}; }}

QStatusBar {{ background: #e3e8ee; color: {TEXT}; }}
QStatusBar QLabel {{ color: {MUTED}; }}
QMessageBox {{ background: {BG}; }}
"""


def light_palette():
    """Fixed light palette so the app looks identical when Windows is in dark mode."""
    from PySide6.QtGui import QColor, QPalette
    pal = QPalette()
    for role, color in ((QPalette.Window, BG), (QPalette.WindowText, TEXT), (QPalette.Base, PANEL),
                        (QPalette.AlternateBase, "#f4f6f9"), (QPalette.Text, TEXT), (QPalette.Button, PANEL),
                        (QPalette.ButtonText, TEXT), (QPalette.ToolTipBase, PANEL), (QPalette.ToolTipText, TEXT),
                        (QPalette.PlaceholderText, "#7a8794"), (QPalette.Highlight, SELECT_BG),
                        (QPalette.HighlightedText, TEXT), (QPalette.BrightText, "#ffffff"), (QPalette.Link, PRIMARY)):
        pal.setColor(role, QColor(color))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(DISABLED))
    return pal
