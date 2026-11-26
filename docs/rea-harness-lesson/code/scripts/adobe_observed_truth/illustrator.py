"""Running Illustrator 2026 over COM: version binding, identity, exact reads, throwaway documents.

Illustrator 2024, 2025 and 2026 are installed side by side, and the unversioned ProgID
binds to whichever registered last. The adapter therefore launches or attaches to the
2026 executable only, and refuses while any other Illustrator version is running.

Script coordinates are Illustrator's scripting coordinates: points, y increasing upward.
Reads return them as integer milli-points (mpt) and zoom as parts per million (ppm), so
evidence carries no floats. Reads name exact properties; nothing is dumped wholesale.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import time
from ctypes import wintypes
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, TypeVar

from .photoshop import THROWAWAY_PREFIX


ILLUSTRATOR_2026 = Path(
    r"C:\Program Files\Adobe\Adobe Illustrator 2026\Support Files\Contents\Windows\Illustrator.exe"
)
MAJOR_VERSION = "30"  # Illustrator 2026
FIXTURE_NAME = THROWAWAY_PREFIX + "fixture"
DIRECT_SELECTION_TOOL = "Adobe Direct Select Tool"

Point = tuple[int, int]
Rect = tuple[int, int, int, int]  # left, top, right, bottom

# ExtendScript is ES3: no JSON object, so the JSON we return is built by hand.
_PRELUDE = r"""
function q(s){return '"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"')+'"';}
function m(v){return Math.round(v*1000);}
function pt(p){return '['+m(p[0])+','+m(p[1])+']';}
function rect(r){return '['+m(r[0])+','+m(r[1])+','+m(r[2])+','+m(r[3])+']';}
function harnessDoc(name){
 if(name.indexOf(PREFIX)!==0){throw new Error("not a harness document");}
 return app.documents.getByName(name);}
function pathJson(item){var pts=item.pathPoints,out=[];
 for(var i=0;i<pts.length;i++){var p=pts[i];
  out.push('{"anchor":'+pt(p.anchor)+',"left_direction":'+pt(p.leftDirection)
   +',"right_direction":'+pt(p.rightDirection)+',"point_type":'+q(p.pointType)
   +',"selected":'+q(p.selected)+'}');}
 return '{"name":'+q(item.name)+',"closed":'+item.closed+',"selected":'+item.selected
  +',"points":['+out.join(',')+']}';}
function selectionJson(doc){var s=doc.selection,out=[];
 for(var i=0;i<s.length;i++){out.push('{"typename":'+q(s[i].typename)+',"name":'+q(s[i].name)+'}');}
 return '['+out.join(',')+']';}
"""

T = TypeVar("T")


@dataclass(frozen=True)
class Identity:
    version: str
    build: str
    executable_path: str
    executable_sha256: str
    pid: int
    hwnd: int


class Illustrator:
    def __init__(
        self,
        executable: Path = ILLUSTRATOR_2026,
        major_version: str = MAJOR_VERSION,
        launch_timeout_s: float = 240,
    ) -> None:
        import win32com.client

        running = _running_illustrators()
        foreign = sorted({path for _, path in running if not _same_path(path, executable)})
        if foreign:
            raise RuntimeError(
                f"Another Illustrator is running ({foreign}); the harness binds to 2026 only "
                "and does not close applications it did not start."
            )
        self.executable = executable
        # Reported so the operator knows the harness left an Illustrator running.
        self.launched = not running
        if self.launched:
            detached = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen([str(executable)], close_fds=True, creationflags=detached)
        prog_id = f"Illustrator.Application.{major_version}"
        self.app = _retry_com(lambda: win32com.client.GetActiveObject(prog_id), launch_timeout_s)
        version = _retry_com(lambda: str(self.app.Version), launch_timeout_s)
        if version.split(".")[0] != major_version:
            raise RuntimeError(f"Bound Illustrator {version}, expected major version {major_version}.")
        # app.path names the install folder, four levels above the executable.
        if not _same_path(str(self.app.Path), executable.parents[3]):
            raise RuntimeError(f"Bound Illustrator at {self.app.Path}, expected {executable}.")

    def js(self, body: str) -> Any:
        """Run `body` as a function body returning a JSON string, with alerts suppressed."""
        script = (
            f"var PREFIX={json.dumps(THROWAWAY_PREFIX)};{_PRELUDE}"
            "var __uil=app.userInteractionLevel;"
            "app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;var __r;"
            f"try{{__r=(function(){{{body}}})();}}finally{{app.userInteractionLevel=__uil;}}__r;"
        )
        return json.loads(self.app.DoJavaScript(script))

    def identity(self) -> Identity:
        path = str(self.executable)
        pid, hwnd = _main_window(path)
        return Identity(
            version=str(self.app.Version),
            build=str(self.app.BuildNumber),
            executable_path=path,
            executable_sha256=_sha256(self.executable),
            pid=pid,
            hwnd=hwnd,
        )

    def new_document(self, name: str, width_pt: int = 400, height_pt: int = 300) -> str:
        """Create an RGB document titled observed-truth-<name>; returns its document name."""
        return self.js(
            "var p=new DocumentPreset();"
            f"p.title={json.dumps(THROWAWAY_PREFIX + name)};p.width={width_pt};p.height={height_pt};"
            "p.units=RulerUnits.Points;p.colorMode=DocumentColorSpace.RGB;"
            'var d=app.documents.addDocument("",p,false);return q(d.name);'
        )

    def close_throwaway_document(self, document: str) -> None:
        # harnessDoc refuses any document this harness did not name.
        self.js(f"harnessDoc({json.dumps(document)}).close(SaveOptions.DONOTSAVECHANGES);return 'null';")

    def create_fixture_path(self, document: str) -> dict[str, Any]:
        """An open, stroked three-anchor arch on the active artboard, nothing selected.

        Relative to the artboard's top-left, in points with y up: corner (100, -200),
        smooth (200, -100) with handles (150, -100) and (250, -100), corner (300, -200).
        """
        return self.js(
            f"var d=harnessDoc({json.dumps(document)});app.activeDocument=d;"
            "var ab=d.artboards[d.artboards.getActiveArtboardIndex()].artboardRect,L=ab[0],T=ab[1];"
            f"var p=d.pathItems.add();p.name={json.dumps(FIXTURE_NAME)};"
            "var c=new RGBColor();c.red=0;c.green=0;c.blue=0;"
            "p.filled=false;p.stroked=true;p.strokeWidth=1;p.strokeColor=c;"
            "p.setEntirePath([[L+100,T-200],[L+200,T-100],[L+300,T-200]]);"
            "var s=p.pathPoints[1];s.leftDirection=[L+150,T-100];s.rightDirection=[L+250,T-100];"
            "s.pointType=PointType.SMOOTH;d.selection=null;return pathJson(p);"
        )

    def path_item(self, document: str, name: str = FIXTURE_NAME) -> dict[str, Any]:
        return self.js(
            f"return pathJson(harnessDoc({json.dumps(document)}).pathItems.getByName({json.dumps(name)}));"
        )

    def selection(self, document: str) -> list[dict[str, str]]:
        return self.js(f"return selectionJson(harnessDoc({json.dumps(document)}));")

    def select_anchors(self, document: str, indices: list[int], name: str = FIXTURE_NAME) -> None:
        """Deselect everything, then select exactly these anchors, by script."""
        self.js(
            f"var d=harnessDoc({json.dumps(document)});d.selection=null;"
            f"var pts=d.pathItems.getByName({json.dumps(name)}).pathPoints,ix={json.dumps(indices)};"
            "for(var i=0;i<ix.length;i++){pts[ix[i]].selected=PathPointSelection.ANCHORPOINT;}"
            "return 'null';"
        )

    def geometry(self, document: str) -> dict[str, Any]:
        """Coordinate system, document size and artboard rectangles ([left, top, right, bottom])."""
        return self.js(
            f"var d=harnessDoc({json.dumps(document)}),abs=[];"
            "for(var i=0;i<d.artboards.length;i++){abs.push(rect(d.artboards[i].artboardRect));}"
            'return \'{"coordinate_system":\'+q(app.coordinateSystem)+\',"width_mpt":\'+m(d.width)'
            "+',\"height_mpt\":'+m(d.height)+',\"artboard_rects_mpt\":['+abs.join(',')+']'"
            "+',\"active_artboard_index\":'+d.artboards.getActiveArtboardIndex()+'}';"
        )

    def view(self, document: str) -> dict[str, Any]:
        """The document's first view: zoom, centre and visible bounds ([left, top, right, bottom])."""
        return self.js(
            f"var v=harnessDoc({json.dumps(document)}).views[0];"
            'return \'{"zoom_ppm":\'+Math.round(v.zoom*1000000)+\',"center_mpt":\'+pt(v.centerPoint)'
            "+',\"bounds_mpt\":'+rect(v.bounds)+',\"screen_mode\":'+q(v.screenMode)+'}';"
        )

    def set_view(self, document: str, *, center_mpt: Point, zoom_ppm: int) -> None:
        self.js(
            f"var v=harnessDoc({json.dumps(document)}).views[0];"
            f"v.zoom={zoom_ppm}/1000000;v.centerPoint=[{center_mpt[0]}/1000,{center_mpt[1]}/1000];"
            "return 'null';"
        )

    def select_tool(self, tool: str) -> None:
        self.js(f"app.selectTool({json.dumps(tool)});return 'null';")


def selected_anchor_indices(points: list[dict[str, Any]]) -> list[int]:
    """Anchors selected as anchors; neighbours report only a selected handle and are excluded."""
    return [
        index
        for index, point in enumerate(points)
        if point["selected"] == "PathPointSelection.ANCHORPOINT"
    ]


def document_to_screen(
    point_mpt: Point,
    *,
    center_mpt: Point,
    zoom_ppm: int,
    canvas: Rect,
    device_pixels_per_point: Fraction | int = 1,
) -> Point:
    """Screen pixel for a document point, assuming the view centre sits at the canvas centre."""
    scale = Fraction(zoom_ppm, 1_000_000) * device_pixels_per_point / 1000
    left, top, right, bottom = canvas
    x = Fraction(left + right, 2) + (point_mpt[0] - center_mpt[0]) * scale
    # Document y increases upward; screen y increases downward.
    y = Fraction(top + bottom, 2) - (point_mpt[1] - center_mpt[1]) * scale
    return round(x), round(y)


def device_pixels_per_point(*, view_bounds_mpt: Rect, zoom_ppm: int, canvas: Rect) -> Fraction:
    """Screen pixels per document point at 100% zoom, from the visible width the view reports."""
    visible_width_mpt = view_bounds_mpt[2] - view_bounds_mpt[0]
    return Fraction(canvas[2] - canvas[0]) * 1000 * 1_000_000 / (visible_width_mpt * zoom_ppm)


def canvas_rect(main_hwnd: int) -> Rect:
    """Screen rectangle of the active document's drawing area, in physical pixels.

    Found from window topology, observed on 30.8.2: the main window ('illustrator' class)
    holds one visible 'OWL.Document' window, whose largest inner 'OS_ViewContainer' child
    excludes the scrollbars and status bar. Call win_input.make_dpi_aware() first.
    """
    documents = [h for h in _descendants(main_hwnd) if _class_name(h) == "OWL.Document"]
    if len(documents) != 1:
        raise RuntimeError(f"Expected one visible OWL.Document window, found {len(documents)}")
    outer = _window_rect(documents[0])
    inner = [
        rect
        for rect in (
            _window_rect(h) for h in _descendants(documents[0]) if _title(h) == "OS_ViewContainer"
        )
        if _area(rect) < _area(outer) and rect[0] >= outer[0] and rect[1] >= outer[1]
    ]
    if not inner:
        raise RuntimeError("No drawing-area window inside the document window")
    return max(inner, key=_area)


def _retry_com(call: Callable[[], T], timeout_s: float) -> T:
    # Illustrator rejects COM calls while starting up or busy.
    import pythoncom

    deadline = time.monotonic() + timeout_s
    while True:
        try:
            return call()
        except pythoncom.com_error:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)


def _running_illustrators() -> list[tuple[int, str]]:
    import psutil

    return [
        (process.info["pid"], process.info["exe"] or "")
        for process in psutil.process_iter(["pid", "name", "exe"])
        if (process.info["name"] or "").lower() == "illustrator.exe"
    ]


def _same_path(a: str | Path, b: str | Path) -> bool:
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _main_window(executable_path: str) -> tuple[int, int]:
    # Window titles name open documents (possibly private files), so they are never read here.
    pids = {pid for pid, path in _running_illustrators() if _same_path(path, executable_path)}
    found: list[tuple[int, int]] = []
    user32 = ctypes.windll.user32

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd) and _class_name(hwnd) == "illustrator":
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                found.append((pid.value, hwnd))
        return True

    user32.EnumWindows(visit, 0)
    if len(found) != 1:
        raise RuntimeError(f"Expected one Illustrator main window for {executable_path}, found {found}")
    return found[0]


def _descendants(hwnd: int) -> list[int]:
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(child, _):
        if user32.IsWindowVisible(child):
            found.append(child)
        return True

    user32.EnumChildWindows(hwnd, visit, 0)
    return found


def _class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _title(hwnd: int) -> str:
    # Only used for internal container windows, whose titles are fixed framework names.
    buffer = ctypes.create_unicode_buffer(64)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, 64)
    return buffer.value


def _window_rect(hwnd: int) -> Rect:
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def _area(rect: Rect) -> int:
    return (rect[2] - rect[0]) * (rect[3] - rect[1])
