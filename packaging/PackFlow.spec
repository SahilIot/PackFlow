# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PackFlow (folder build: reliable, fast start, few antivirus false alarms).
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))   # SPECPATH = this packaging\ folder; ROOT = project root

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, "resources"), "resources")],
    hiddenimports=["PySide6.QtPrintSupport"],   # makes sure the Windows printer plugin is bundled
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick",
              "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtNetwork", "PySide6.QtSql"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="PackFlow",
    console=False,                 # normal windowed application
    icon=os.path.join(ROOT, "resources", "icon.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PackFlow", upx=False)
