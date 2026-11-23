# PackFlow

A standalone Windows desktop application for printing machine packing instructions (FRONT, TOP, FRAGILE, …) on A4 paper.
The page is printed directly from the app - no Word, Excel or PDF editor needed.

## Features

- Ready-made packing instructions plus your own, with text, symbol, border and background colours
- Templates, and a visual layout editor (drag, resize, multi-page, grid arrange, undo/redo)
- A4 portrait or landscape, live preview, print preview, copies, printer selection, PDF output
- Colour, grayscale or black & white printing (Brother printers supported)
- Works offline; every computer keeps its own data. No server, account or database install

## Technology

Python 3.10+, PySide6 (Qt, including Qt Print Support), SQLite, PyInstaller (Windows build), Inno Setup 6 (installer).

## Download and install

1. Get `PackFlow-Setup.exe` (build it yourself, see below, or ask whoever built it).
2. Run it (no administrator rights needed) and open **PackFlow** from the desktop or Start menu.
3. Choose your printer in the app and print.

## Run from source

Windows: double-click `scripts\run_from_source.bat` (creates `.venv`, installs requirements, starts the app).
Manually: `pip install -r requirements.txt` then `python main.py`.

## Build the Windows executable and installer

Run on a Windows PC with Python 3.10+:

1. `scripts\build.bat` - builds `dist\PackFlow\PackFlow.exe` and runs a self-check. Python is not needed to run the result.
2. `scripts\build_installer.bat` (needs [Inno Setup 6](https://jrsoftware.org/isdl.php)) - creates `installer\Output\PackFlow-Setup.exe`.

More in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## For factory users (daily use)

1. Double-click **PackFlow**.
2. Tick the instructions you need (or choose a **Template**, e.g. *Export Packing*).
3. Check the live A4 preview on the right. Use ◀ ▶ if there is more than one page.
4. Choose the **Printer** and the number of **Copies**.
5. Click **PRINT** (or **A4 Print Preview** first).

Tips
- *Select All / Deselect All* act on the instructions currently shown by the search box.
- **Disable** hides an instruction from printing without deleting it.
- **Customize Layout…** opens the visual A4 editor. **Save…** stores the selection and layout as a template.
- If the printer is switched on after the app started, press **Refresh** next to the printer list.

## Colors and print color mode

- **Print color** (Print Settings): *Color*, *Grayscale* or *Black & White*. The A4 preview, PDF export and the
  printer all use the same conversion, so the preview shows exactly what will be printed. Your choice is remembered
  and also saved inside templates.
- Grayscale converts every color to its gray equivalent. Black & White prints only pure black and white (light colors
  such as yellow become white; text is never printed white-on-white).
- The app asks the printer driver whether it can print color. If it cannot, *Color* is disabled and the app prints in
  grayscale with a notice. If the driver does not say, color stays available.
- Each instruction has **text, symbol, border and background colors** (Edit Instruction dialog), and each element in the
  layout editor has the same controls. Pick from Black, Red, Blue, Green, Orange, Yellow, White or **Custom color…**.
  Built-in instructions come with example colors (FRONT blue, FRAGILE red, KEEP DRY blue …) that you can change.
- Existing data is upgraded automatically (a `.bak-vN` backup of the database is made first). Old templates and layouts
  keep their black-and-white look.
- If the printout is not in color although *Color* is selected, open the printer's **Printing Preferences** in Windows
  and set its color option to *Color* or *Auto* - some drivers (Brother included) have a saved default that can
  override applications. After each print the app compares the driver's mode with the requested one and warns on a mismatch.

## Layout editor

- Add text boxes, symbols (arrows, fragile, keep dry, …) or whole instruction cards.
- Drag to move, drag the square handles to resize; arrow keys nudge by 1 mm (Shift = 5 mm). Ctrl+wheel zooms.
- Right panel: exact position/size in mm, text, symbol and its position, font, size, bold/italic, alignment,
  border (solid/dashed), padding, "shrink text to fit".
- Snap-to-grid for tidy layouts, or switch it off for free positioning. **Arrange in Grid…** re-flows all
  elements into any columns × rows. Align menu, duplicate, front/back, undo/redo (Ctrl+Z / Ctrl+Y).
- Portrait or landscape, margin guide, several pages per document.

Preview and printout use the same drawing code (vector, 0.1 mm units, real A4 = 210 × 297 mm), so they match.
Before printing, the app warns if content is closer to the edge than the selected printer can print.

## Where data is stored

Everything is on this computer, in `%APPDATA%\PackFlow\machine_packing_print.db` (SQLite): instructions, colours, templates, layouts and
settings (printer, copies, window). It is created automatically on first start and never stored in the install folder.
Installing a newer version or uninstalling does not delete it; database upgrades are automatic and keep a `.bak-vN` copy.
If an older version left data in `%APPDATA%\MachinePackingPrint`, it is copied (not moved) on first start.
To back up or move your data, copy the `.db` file while PackFlow is closed.

Note: templates with a *custom layout* store their own copy of the text; editing an instruction later does not
change such templates (automatic-layout templates always use the current instruction).

### Printer troubleshooting
- The printer list is read fresh from Windows every time you press **Refresh Printers**, using Qt first and the Windows
  spooler API as a cross-check. The line under the printer box says how many printers were found and which is selected.
  Hover over it to see how many Qt and Windows each found.
- Every printer in the list was opened through Qt, so it can really print; a printer Windows lists but Qt cannot open
  is shown as "unavailable".
- Run `PackFlow.exe --printer-diag` (or `python main.py --printer-diag`) for a full report; it is saved to
  `%TEMP%\PackFlow_printers.txt`.
- "Print Spooler not running": start the *Print Spooler* service (Win+R, `services.msc`).
- Selecting "Microsoft Print to PDF" asks you where to save the PDF, which is a handy way to check output without paper.

### First-time checklist on the factory PC
- Run `PackFlow.exe --selftest` from a Command Prompt once; it should end with `RESULT: PASS` and
  list your printers (report: `%TEMP%\PackFlow_selftest.txt`).
- Print one test page and measure the box edges with a ruler (A4 scale 100 % - the app already prints at actual size).
  Make sure the printer driver is set to "Actual size / 100 %", not "Fit to page".

## Project structure

```
main.py             entry point (--selftest = headless check, --printer-diag = printer report)
requirements.txt    runtime and build dependencies
app/                application source
  database.py         local SQLite storage, versioned migrations, default instructions
  models.py           Instruction, Element, Page, Document, Template
  paths.py            user-data folder and bundled-resource paths
  renderer.py         ONE drawing path for editor, preview, PDF and printer
  layout.py           automatic grid layout + pagination
  printing.py         printer discovery, preview/print, margin checks
  symbols.py          built-in vector symbols
  selftest.py         --selftest / --printer-diag
  ui/                 main window, layout editor, dialogs, styles
resources/          icon.ico and other bundled assets
scripts/            build.bat, build_installer.bat, run_from_source.bat
packaging/          PackFlow.spec (PyInstaller)
installer/          PackFlow.iss (Inno Setup)
docs/               deployment notes
```

Adding a symbol: write a `draw(painter)` function on a 100 × 100 canvas in `app/symbols.py` and add it to
`SYMBOLS`.
