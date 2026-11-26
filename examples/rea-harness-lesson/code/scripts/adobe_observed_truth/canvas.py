"""Where a document point is on screen, read from Photoshop's own view state.

Photoshop 27.11 exposes the active document's view through three document
properties, read by exact key (probed 2026-11-08 on throwaway documents, workstation
locked, one 2560-wide monitor at 120 DPI, Photoshop's main window per-monitor DPI aware):

- ``viewInfo.activeView.globalBounds`` (left/top/right/bottom): the document view's
  rectangle in physical screen pixels. Proven: it equals the Win32 rectangle of the
  ``OWL.Document`` window. It includes the scrollbars and, when shown, the rulers.
- ``viewTransform`` (six doubles ``a, b, c, d, tx, ty``): maps view units, measured from
  the top-left of ``globalBounds``, to document pixels. Proven for the unrotated case:
  ``a == d == monitor scale / zoom`` at every zoom tried (0.5 to 128) and the
  translation follows scripted pans. A 400x300 document opened at 100% put document
  (200.25, 149.5) at the centre of the view minus its scrollbars, and turning the
  rulers on recentred it by half the ruler width while ``globalBounds`` stayed put,
  so the origin is the ``globalBounds`` corner. At 100% one document pixel spans one
  physical pixel. At non-integer zooms the axes differ slightly (66.67%: 1.8727 x 1.8657).
- ``zoom``: a ratio, 1.0 meaning 100%, even though its unit is labelled percent.
  The scripted ``set`` takes the same ratio; 200 is clamped to 128 (12800%).

The view unit is a physical pixel divided by the monitor scale (DPI / 96). Photoshop's
own scale (``hypot(a, b) * zoom``) matched Windows' 1.25 here; ``read_view`` refuses to
map if they disagree, since which one governs would then be unknown.

Assumed, not observed:

- Rotation. The Rotate View tool needs input; ``b`` and ``c`` were always 0. The
  inverse is general, but the order of ``b`` and ``c`` is assumed to be
  ``doc = (a*u + c*v + tx, b*u + d*v + ty)``.
- Which document point a mouse event inside a physical pixel hits. Screen pixels are
  taken at their top-left corner; ``canvas_mapping_check`` measures the error.
- Screen modes and floating document windows. Menu state does not report the
  checked screen mode; only Standard Screen Mode with tabbed documents was seen.
"""

from __future__ import annotations

import ctypes
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .photoshop import Identity, Photoshop


Matrix = tuple[float, float, float, float, float, float]

# Photoshop's scale and Windows' differ by under 0.6% at non-integer zooms.
_SCALE_TOLERANCE = 0.02

_READ_VIEW = r"""
var k=stringIDToTypeID;
function dp(n){var r=new ActionReference();r.putProperty(k("property"),k(n));
 r.putEnumerated(charIDToTypeID("Dcmn"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));
 return executeActionGet(r);}
var l=dp("viewTransform").getList(k("viewTransform")),m=[];
for(var i=0;i<l.count;i++)m.push(l.getDouble(i));
var vi=dp("viewInfo").getObjectValue(k("viewInfo"));
var gb=vi.getObjectValue(k("activeView")).getObjectValue(k("globalBounds"));
var doc=app.activeDocument;
'{"zoom":'+dp("zoom").getUnitDoubleValue(k("zoom"))+',"matrix":['+m.join(',')+']'
+',"bounds":['+gb.getDouble(k("left"))+','+gb.getDouble(k("top"))+','
+gb.getDouble(k("right"))+','+gb.getDouble(k("bottom"))+']'
+',"visible":'+vi.getBoolean(k("visible"))
+',"rulers":'+dp("rulersVisibility").getBoolean(k("rulersVisibility"))
+',"width":'+doc.width.as("px")+',"height":'+doc.height.as("px")+'}';
"""


@dataclass(frozen=True)
class View:
    zoom: float  # 1.0 is 100%
    document_size: tuple[int, int]  # pixels
    view_bounds: tuple[int, int, int, int]  # physical screen pixels, scrollbars and rulers included
    view_to_document: Matrix  # Photoshop's viewTransform
    dpi_scale: float  # physical pixels per view unit: the monitor's DPI / 96
    rulers_visible: bool


def read_view(ps: Photoshop, identity: Identity) -> View:
    """The active document's view; call inside photoshop.exclusive()."""
    from . import win_input

    win_input.make_dpi_aware()
    if _dpi_awareness(identity.hwnd) != 2:
        raise RuntimeError("Photoshop is not per-monitor DPI aware; its view bounds would be virtualized.")
    facts = ps.js(_READ_VIEW)
    if not facts["visible"]:
        raise RuntimeError("The active document's view is not visible.")
    bounds = tuple(round(edge) for edge in facts["bounds"])
    matrix = tuple(float(value) for value in facts["matrix"])
    dpi_scale = _monitor_scale((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
    photoshop_scale = math.hypot(matrix[0], matrix[1]) * facts["zoom"]
    if abs(photoshop_scale - dpi_scale) > _SCALE_TOLERANCE * dpi_scale:
        raise RuntimeError(
            f"Photoshop's view scale {photoshop_scale:.4f} disagrees with the monitor scale {dpi_scale:.4f}."
        )
    return View(
        zoom=float(facts["zoom"]),
        document_size=(round(facts["width"]), round(facts["height"])),
        view_bounds=bounds,  # type: ignore[arg-type]
        view_to_document=matrix,  # type: ignore[arg-type]
        dpi_scale=dpi_scale,
        rulers_visible=bool(facts["rulers"]),
    )


def set_zoom(ps: Photoshop, percent: float) -> None:
    """Zoom the active document about its view centre; Photoshop clamps to 12800%."""
    # The descriptor's unit says percent but Photoshop reads the value as a ratio.
    ps.js(
        'var d=new ActionDescriptor(),r=new ActionReference(),z=new ActionDescriptor();'
        'r.putProperty(charIDToTypeID("Prpr"),charIDToTypeID("Zm  "));'
        'r.putEnumerated(charIDToTypeID("Dcmn"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));'
        'd.putReference(charIDToTypeID("null"),r);'
        f'z.putUnitDouble(charIDToTypeID("Zm  "),charIDToTypeID("#Prc"),{percent / 100!r});'
        'd.putObject(charIDToTypeID("T   "),charIDToTypeID("Zm  "),z);'
        'executeAction(charIDToTypeID("setd"),d,DialogModes.NO);"null";'
    )


def document_to_screen(view: View, x: float, y: float) -> tuple[int, int]:
    """The physical screen pixel nearest document point (x, y), on or off the canvas."""
    a, b, c, d, tx, ty = view.view_to_document
    det = a * d - b * c
    dx, dy = x - tx, y - ty
    u = (d * dx - c * dy) / det
    v = (a * dy - b * dx) / det
    left, top = view.view_bounds[:2]
    return _nearest(left + u * view.dpi_scale), _nearest(top + v * view.dpi_scale)


def screen_to_document(view: View, sx: int, sy: int) -> tuple[float, float]:
    """The document point under the top-left corner of physical screen pixel (sx, sy)."""
    a, b, c, d, tx, ty = view.view_to_document
    left, top = view.view_bounds[:2]
    u = (sx - left) / view.dpi_scale
    v = (sy - top) / view.dpi_scale
    return a * u + c * v + tx, b * u + d * v + ty


def _nearest(value: float) -> int:
    return math.floor(value + 0.5)


def _dpi_awareness(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    return user32.GetAwarenessFromDpiAwarenessContext(user32.GetWindowDpiAwarenessContext(hwnd))


def _monitor_scale(x: int, y: int) -> float:
    from ctypes import wintypes

    user32, shcore = ctypes.windll.user32, ctypes.windll.shcore
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    shcore.GetDpiForMonitor.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
    monitor = user32.MonitorFromPoint(wintypes.POINT(x, y), 2)  # MONITOR_DEFAULTTONEAREST
    dpi_x, dpi_y = ctypes.c_uint(), ctypes.c_uint()
    # MDT_EFFECTIVE_DPI; the caller is per-monitor aware, so this is the monitor's real DPI.
    if shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) != 0:
        raise OSError("GetDpiForMonitor failed")
    return dpi_x.value / 96
