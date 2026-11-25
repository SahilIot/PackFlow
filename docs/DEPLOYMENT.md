# PackFlow - sharing with the team

PackFlow is a standalone Windows program. Each computer keeps its own instructions, templates, layouts and settings. No server, account, database installation or internet connection is needed.

## Build once (on one Windows computer with Python 3.10+)
1. `scripts\build.bat` - creates `dist\PackFlow\PackFlow.exe` (a folder; Python is not needed to run it) and runs a self-check.
2. `scripts\build_installer.bat` (needs Inno Setup 6) - creates `installer\Output\PackFlow-Setup.exe`.

## Share
Give colleagues `PackFlow-Setup.exe` (or zip the `dist\PackFlow` folder; they run `PackFlow.exe` from it).

## Install and use
Run `PackFlow-Setup.exe` (no administrator rights needed), open PackFlow, choose your printer, print.

## Data and upgrades
* Data file: `%APPDATA%\PackFlow\machine_packing_print.db`. It is created on first start. Installing a newer version, or uninstalling, never deletes it.
* If an older version's data exists in `%APPDATA%\MachinePackingPrint`, it is copied (not moved) on first start of PackFlow.
* Database upgrades are automatic and keep a `.bak-vN` copy next to the file.
* To move data to another computer, copy the `.db` file into the same folder there while PackFlow is closed.

## Troubleshooting
* Printer missing: run `PackFlow.exe --printer-diag` (report saved in `%TEMP%\PackFlow_printers.txt`).
* Self-check: `PackFlow.exe --selftest` (report in `%TEMP%\PackFlow_selftest.txt`).