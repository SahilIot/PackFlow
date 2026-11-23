# Printer integration built on native Qt printing (QPrinter / QPrinterInfo).
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from .models import Document
from .renderer import UNIT, content_bounds_mm, paint_page

class PrintError(RuntimeError):
     """ Raised with a user-readable message when printing cannot proceed."""

@dataclass
class PrinterEntry:
    name: str
    is_default: bool
    available: bool
    detail: str
    source: str = "qt"          # "qt" = enumerated by Qt, "windows" = found only via the Windows spooler API
    color_supported: bool | None = None   # True/False from the printer driver, None = driver did not say


@dataclass
class PrinterScan:
   # Result of one fresh printer enumeration, with everything needed to explain it.
    printers: list[PrinterEntry] = field(default_factory=list)
    default: str | None = None
    qt_count: int = 0
    win_count: int = 0
    errors: list[str] = field(default_factory=list)
    spooler_down: bool = False

    def summary(self) -> str:
        n = len(self.printers)
        if self.spooler_down:
            return "The Windows printer service (Print Spooler) is not running. Start it in Windows Services, then press Refresh Printers."
        if n == 0:
            extra = f" ({'; '.join(self.errors)})" if self.errors else ""
            return "No printers are installed in Windows." + extra
        return f"{n} printer{'s' if n != 1 else ''} detected."


# Windows error codes returned by the spooler API
_ERROR_INSUFFICIENT_BUFFER = 122
_RPC_S_SERVER_UNAVAILABLE = 1722
_RPC_S_CALL_FAILED = 1726

def _windows_printers() -> tuple[list[str], str | None, str | None, bool]:
    # Ask the Windows spooler directly (ctypes, no extra packages).
    # Returns (names, default_name, error_text, spooler_down). Empty on non-Windows systems.

    if not sys.platform.startswith("win"):
        return [], None, None, False
    try:
        import ctypes
        from ctypes import wintypes
        winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
        class PRINTER_INFO_4W(ctypes.Structure):
            _fields_ = [("pPrinterName", wintypes.LPWSTR), ("pServerName", wintypes.LPWSTR),
                        ("Attributes", wintypes.DWORD)]

        enum = winspool.EnumPrintersW
        enum.restype = wintypes.BOOL
        enum.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_byte),
                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
        flags = 0x2 | 0x4  # PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
        needed, returned = wintypes.DWORD(0), wintypes.DWORD(0)
        ctypes.set_last_error(0)
        enum(flags, None, 4, None, 0, ctypes.byref(needed), ctypes.byref(returned))
        err = ctypes.get_last_error()
        if err in (_RPC_S_SERVER_UNAVAILABLE, _RPC_S_CALL_FAILED):
            return [], None, f"Windows error {err}", True
        names: list[str] = []
        if needed.value:
            buf = (ctypes.c_byte * needed.value)()
            if not enum(flags, None, 4, buf, needed.value, ctypes.byref(needed), ctypes.byref(returned)):
                err = ctypes.get_last_error()
                return [], None, f"EnumPrinters failed (Windows error {err})", err in (_RPC_S_SERVER_UNAVAILABLE, _RPC_S_CALL_FAILED)
            arr = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_4W))
            names = [arr[i].pPrinterName for i in range(returned.value) if arr[i].pPrinterName]
        default = None
        get_default = winspool.GetDefaultPrinterW
        get_default.restype = wintypes.BOOL
        get_default.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        size = wintypes.DWORD(0)
        get_default(None, ctypes.byref(size))
        if size.value:
            name_buf = ctypes.create_unicode_buffer(size.value)
            if get_default(name_buf, ctypes.byref(size)):
                default = name_buf.value
        return names, default, None, False
    except Exception as exc:  # noqa: BLE001 - diagnostics must never crash the app
        return [], None, f"Windows printer API unavailable: {exc}", False

def _supports_color(info: QPrinterInfo) -> bool | None:
    # Ask the printer driver (through Qt) whether it can print in colour. None if it does not say.
    try:
        modes = list(info.supportedColorModes())
    except Exception:  # noqa: BLE001
        return None
    return QPrinter.ColorMode.Color in modes if modes else None

def _qt_printers() -> tuple[list[PrinterEntry], str | None, list[str]]:
    # Printers known to Qt. Each printer is read separately so one bad driver cannot hide the rest.
    entries: list[PrinterEntry] = []
    errors: list[str] = []
    try:
        infos = QPrinterInfo.availablePrinters()
        default = QPrinterInfo.defaultPrinterName() or None
    except Exception as exc:  # noqa: BLE001
        return [], None, [f"Qt could not list printers: {exc}"]
    for info in infos:
        try:
            name = info.printerName()
            try:
                available = info.state() != QPrinter.PrinterState.Error
            except Exception:  # noqa: BLE001 - state is optional information
                available = True
            detail = info.makeAndModel() or info.description() or info.location() or ""
            entries.append(PrinterEntry(name, name == default, available,
                                        detail if available else f"{detail} (printer reports an error)".strip(),
                                        color_supported=_supports_color(info)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Could not read a printer: {exc}")
    return entries, default, errors

def list_printers() -> PrinterScan:
    # Fresh enumeration of all printers installed in Windows (Qt first, Windows API as cross-check).
    scan = PrinterScan()
    qt_entries, qt_default, qt_errors = _qt_printers()
    scan.errors.extend(qt_errors)
    scan.qt_count = len(qt_entries)
    win_names, win_default, win_error, scan.spooler_down = _windows_printers()
    scan.win_count = len(win_names)
    if win_error:
        scan.errors.append(win_error)
    known = {e.name.lower() for e in qt_entries}
    scan.printers = list(qt_entries)
    for name in win_names:          # printers Windows lists but Qt did not: only offer them if Qt can really open them
        if name.lower() in known:
            continue
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPrinterName(name)
        ok = printer.isValid() and printer.printerName() == name
        scan.printers.append(PrinterEntry(
            name, False, ok, "" if ok else "Windows lists this printer but Qt cannot open it", source="windows"))
    default = qt_default or win_default
    for e in scan.printers:
        e.is_default = default is not None and e.name.lower() == default.lower()
    scan.default = next((e.name for e in scan.printers if e.is_default), None)
    return scan

def _find_info(name: str) -> QPrinterInfo | None:
    for info in QPrinterInfo.availablePrinters():
        if info.printerName() == name:
            return info
    return None

def create_printer(name: str | None, orientation: str, copies: int = 1, mode: str = "color") -> QPrinter:
    # Create an A4 QPrinter for exactly the named Windows printer (never silently another one).
    if name:
        info = _find_info(name)
        printer = QPrinter(info, QPrinter.HighResolution) if info else QPrinter(QPrinter.HighResolution)
        if not info:
            printer.setPrinterName(name)
        if not printer.isValid() or printer.printerName() != name:
            raise PrintError(f"The printer '{name}' is not available.\n"
                             "Check that it is switched on and connected, then press Refresh Printers.")
    else:
        printer = QPrinter(QPrinter.HighResolution)
    configure(printer, orientation, copies, mode)
    return printer

def qt_color_mode(mode: str) -> QPrinter.ColorMode:
    return QPrinter.ColorMode.Color if mode == "color" else QPrinter.ColorMode.GrayScale

def configure(printer: QPrinter, orientation: str, copies: int = 1, mode: str = "color") -> None:
    orient = QPageLayout.Landscape if orientation == "landscape" else QPageLayout.Portrait
    layout = QPageLayout(QPageSize(QPageSize.A4), orient, QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter)
    printer.setPageLayout(layout)
    printer.setFullPage(True)           # origin = paper corner, so mm positions are exact
    printer.setCopyCount(max(1, copies))
    printer.setColorMode(qt_color_mode(mode))   # the driver is told too; pixels are also converted by the renderer

def printable_margins_mm(printer: QPrinter) -> tuple[float, float, float, float]:
    # Hardware minimum margins (left, top, right, bottom) in mm.
    m = printer.pageLayout().minimumMargins()
    return (m.left(), m.top(), m.right(), m.bottom())

def clipping_warnings(doc: Document, printer: QPrinter) -> list[str]:
    # Describe pages whose content reaches into the printer's unprintable edge.
    left, top, right, bottom = printable_margins_mm(printer)
    pw, ph = doc.size_mm
    warnings = []
    for i, page in enumerate(doc.pages, 1):
        b = content_bounds_mm(page)
        if not b:
            continue
        x0, y0, x1, y1 = b
        if x0 < left - 0.01 or y0 < top - 0.01 or x1 > pw - right + 0.01 or y1 > ph - bottom + 0.01:
            warnings.append(f"Page {i}: content is closer to the paper edge than this printer can print "
                            f"(needs about {max(left, top, right, bottom):.1f} mm). Edges may be cut off.")
        if x0 < -0.01 or y0 < -0.01 or x1 > pw + 0.01 or y1 > ph + 0.01:
            warnings.append(f"Page {i}: content extends beyond the A4 page.")
    return warnings

def render_document(printer: QPrinter, doc: Document, copies: int = 1, mode: str = "color") -> list[str]:
    """Paint every page of `doc` onto `printer` (a real printer, PDF or preview) in colour `mode`.
    Used for printing, print preview and PDF export, so all three are identical. The same mode is applied to
    every page and every copy. Returns warnings (e.g. the driver changed the colour mode).
    """
    warnings: list[str] = []
    loops = 1 if printer.supportsMultipleCopies() or copies <= 1 else copies
    painter = QPainter()
    if not painter.begin(printer):
        raise PrintError("Could not start printing. The printer may be offline, busy or has no paper size A4.")
    try:
        wanted = qt_color_mode(mode)
        if printer.colorMode() != wanted:
            warnings.append(
                "The printer driver changed the colour mode "
                f"({'colour' if wanted == QPrinter.ColorMode.Color else 'grayscale'} was requested). "
                "Open the printer's Printing Preferences in Windows and set its colour option to Color / Auto "
                "(or Grayscale), then print again.")
        scale = printer.resolution() / 25.4 / UNIT   # painter units (0.1 mm) -> device pixels
        first = True
        for _ in range(loops):
            for page in doc.pages:
                if not first and not printer.newPage():
                    raise PrintError("The printer refused to start a new page.")
                first = False
                painter.save()
                painter.scale(scale, scale)
                paint_page(painter, doc, page, mode)
                painter.restore()
    finally:
        painter.end()
    if printer.printerState() == QPrinter.PrinterState.Error:
        raise PrintError("The printer reported an error while printing. Check paper, ink/toner and connection.")
    return warnings

def print_document(doc: Document, printer_name: str | None, copies: int, mode: str = "color") -> list[str]:
    if not any(p.elements for p in doc.pages):
        raise PrintError("There is nothing to print. Select at least one instruction.")
    printer = create_printer(printer_name, doc.orientation, copies, mode)
    return render_document(printer, doc, copies, mode)

def export_pdf(doc: Document, path: str, mode: str = "color") -> None:
    # Write `doc` to a PDF through the same render path (used for checks).
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(path)
    configure(printer, doc.orientation, 1, mode)
    render_document(printer, doc, 1, mode)

def diagnose() -> list[str]:
    # Human-readable printer diagnostics (used by --printer-diag and --selftest). Prints nothing.
    from PySide6 import __version__ as pyside_version
    from PySide6.QtCore import qVersion
    lines = [f"PySide6 {pyside_version}, Qt {qVersion()}, platform {sys.platform}"]
    scan = list_printers()
    lines.append(f"Qt enumeration: {scan.qt_count} printer(s); Windows spooler API: {scan.win_count} printer(s)")
    lines.append(scan.summary())
    lines.extend(f"  problem: {e}" for e in scan.errors)
    for e in scan.printers:
        flags = ("default " if e.is_default else "") + ("" if e.available else "UNAVAILABLE ") + f"[{e.source}]"
        try:
            pr = create_printer(e.name, "portrait", 2)
            colour = {True: "yes", False: "NO", None: "unknown"}[e.color_supported]
            check = (f"opens OK, valid={pr.isValid()}, colour={colour}, {pr.resolution()} dpi, "
                     f"multiple copies in driver={pr.supportsMultipleCopies()}, state={pr.printerState().name}")
        except Exception as exc:  # noqa: BLE001
            check = f"CANNOT OPEN: {exc}"
        lines.append(f"  - {e.name}  ({flags})  {check}")
    return lines