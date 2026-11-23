# Machine Packing Print

Windows desktop application for printing machine packing instructions (FRONT, TOP, FRAGILE, …) on A4 paper.
Works offline. No Word, Excel or PDF editor is needed - the page is printed directly from the app.

## For factory users (daily use)

1. Double-click **MachinePackingPrint.exe**.
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
- Existing data is upgraded automatically (a `.bak-v1` backup of the database is made first). Old templates and layouts
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

`%APPDATA%\MachinePackingPrint\machine_packing_print.db` (SQLite). It survives updates and is not in the
program folder. To back up or move to another PC, copy that file. Deleting it restores the defaults.
A damaged file is kept as `*.corrupt-<time>` and a fresh one is created. Future program versions upgrade the
file automatically (a `.bak-vN` copy is made first).

Note: templates with a *custom layout* store their own copy of the text; editing an instruction later does not
change such templates (automatic-layout templates always use the current instruction).

## Building the .exe (on a Windows PC)

Requirements: Windows 10/11, Python 3.10 or newer from python.org ("Add python.exe to PATH" ticked), internet
for the first build.

1. Open the project folder and double-click **build.bat** (or run it in a terminal).
2. It creates a virtual environment, installs PySide6 + PyInstaller, builds, and then **runs the packaged exe
   with `--selftest`**, which checks database creation, A4 PDF rendering, bundled resources and printer detection.
3. Result: `dist\MachinePackingPrint\MachinePackingPrint.exe`. Copy/zip the **whole folder**
   `dist\MachinePackingPrint` to the target PC; no Python is needed there. Optionally make a desktop shortcut.

To run from source without building: `run_from_source.bat`.

Manual build: `pip install -r requirements.txt` then `pyinstaller --noconfirm --clean MachinePackingPrint.spec`.

### Printer troubleshooting
- The printer list is read fresh from Windows every time you press **Refresh Printers**, using Qt first and the Windows
  spooler API as a cross-check. The line under the printer box says how many printers were found and which is selected.
  Hover over it to see how many Qt and Windows each found.
- Every printer in the list was opened through Qt, so it can really print; a printer Windows lists but Qt cannot open
  is shown as "unavailable".
- Run `MachinePackingPrint.exe --printer-diag` (or `python main.py --printer-diag`) for a full report; it is saved to
  `%TEMP%\MachinePackingPrint_printers.txt`.
- "Print Spooler not running": start the *Print Spooler* service (Win+R, `services.msc`).
- Selecting "Microsoft Print to PDF" asks you where to save the PDF, which is a handy way to check output without paper.

### First-time checklist on the factory PC
- Run `MachinePackingPrint.exe --selftest` from a Command Prompt once; it should end with `RESULT: PASS` and
  list your printers (report: `%TEMP%\MachinePackingPrint_selftest.txt`).
- Print one test page and measure the box edges with a ruler (A4 scale 100 % - the app already prints at actual size).
  Make sure the printer driver is set to "Actual size / 100 %", not "Fit to page".

## Project structure

```
main.py                    entry point (--selftest = headless check)
app/models.py              dataclasses: Instruction, Element, Page, Document, Template
app/database.py            SQLite schema, migrations, repositories, defaults
app/paths.py               user-data folder and bundled-resource paths
app/symbols.py             built-in vector symbol library
app/renderer.py            ONE drawing path for editor, preview and printer
app/layout.py              automatic grid layout + pagination
app/printing.py            Qt printer discovery, preview/print rendering, margin checks
app/ui/                    main window, layout editor, dialogs, styles
MachinePackingPrint.spec   PyInstaller configuration
build.bat                  one-click build + packaged-exe test
```

Adding a symbol: write a `draw(painter)` function on a 100 × 100 canvas in `app/symbols.py` and add it to
`SYMBOLS`; for an existing database also insert a row in `symbol_config` (or add a migration).
