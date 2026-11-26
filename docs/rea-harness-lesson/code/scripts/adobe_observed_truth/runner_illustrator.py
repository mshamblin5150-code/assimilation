"""The sweep runner for Illustrator 2026: each menu command run by name on a scratch document of test
art, what it did read as a vector change, its dialogs captured and cancelled.

Specs come from illustrator_families (menu_specs). Each runs new_fixture (an RGB document of test
art, everything top-level selected), run_menu_command (app.executeMenuCommand with alerts shown,
in a worker thread while dialogs are watched for), record (dialogs; the document's vector change,
vector_change), cancel_dialogs and close_throwaway_document. Illustrator's dialogs are standard
dialog windows (#32770) whose controls it draws itself, so they are found by class and answered by
closing them, which cancels (Rotate, 2026-11-25). The session, idle guards and stack sampler are
the Photoshop runner's; run only with no real document open.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import capture, win_input
from .families import ScenarioSpec, session_blocker
from .idle import Interrupted
from .illustrator import Illustrator
from .photoshop import THROWAWAY_PREFIX
from .runner import Refused, RunResult, execute, plan_queue, run_session
from .vector_change import vector_change

DIALOG_CLASS = "#32770"
PANEL_PREFIX = "OWL."  # Illustrator's floating panels: never closed
COMMAND_TIMEOUT_S = 90

FIXTURE_JS = r"""
var p=new DocumentPreset();p.title=PREFIX+"sweep";p.width=400;p.height=300;p.units=RulerUnits.Points;
p.colorMode=DocumentColorSpace.RGB;var d=app.documents.addDocument("",p,false);
function rgb(r,g,b){var c=new RGBColor();c.red=r;c.green=g;c.blue=b;return c;}
var ab=d.artboards[0].artboardRect,L=ab[0],T=ab[1];
var r=d.pathItems.rectangle(T-30,L+30,120,80);r.fillColor=rgb(255,0,0);r.strokeColor=rgb(0,0,0);r.strokeWidth=2;r.name="rect";
var e=d.pathItems.ellipse(T-30,L+180,90,90);e.fillColor=rgb(0,0,255);e.stroked=false;e.name="ellipse";
var a=d.pathItems.add();a.setEntirePath([[L+30,T-200],[L+90,T-150],[L+150,T-200]]);a.filled=false;a.stroked=true;
a.strokeColor=rgb(0,0,0);a.strokeWidth=3;a.name="arch";
var s=d.pathItems.star(L+300,T-80,40,20,5);s.fillColor=rgb(0,160,0);s.name="star";
var t=d.textFrames.add();t.contents="Observed 123";t.position=[L+30,T-240];t.name="text";
var g=d.groupItems.add();g.name="group";var g1=g.pathItems.rectangle(T-220,L+250,30,30);g1.fillColor=rgb(255,200,0);
var g2=g.pathItems.rectangle(T-220,L+290,30,30);g2.fillColor=rgb(200,0,200);
for(var i=0;i<d.pageItems.length;i++){if(d.pageItems[i].parent.typename!="GroupItem")d.pageItems[i].selected=true;}
return q(d.name);
"""

SNAPSHOT_JS = r"""
var d=harnessDoc(DOC);
function col(c){if(!c)return "null";var n=c.typename;
 if(n=="RGBColor")return q("rgb("+Math.round(c.red)+","+Math.round(c.green)+","+Math.round(c.blue)+")");
 if(n=="GrayColor")return q("gray("+Math.round(c.gray)+")");if(n=="NoColor")return q("none");return q(n);}
var out=[];
for(var i=0;i<d.pageItems.length;i++){var it=d.pageItems[i],t=it.typename,f=['"type":'+q(t),'"bounds":'+rect(it.geometricBounds)];
 try{f.push('"opacity":'+Math.round(it.opacity));}catch(x){}
 if(t=="PathItem"){f.push('"points":'+it.pathPoints.length,'"closed":'+it.closed,'"filled":'+it.filled,'"stroked":'+it.stroked);
  if(it.filled)f.push('"fill":'+col(it.fillColor));if(it.stroked){f.push('"stroke":'+col(it.strokeColor),'"stroke_mpt":'+m(it.strokeWidth));}}
 if(t=="GroupItem")f.push('"children":'+it.pageItems.length,'"clipped":'+it.clipped);
 if(t=="CompoundPathItem")f.push('"paths":'+it.pathItems.length);
 if(t=="TextFrame")f.push('"text_length":'+it.contents.length,'"text_kind":'+q(it.kind));
 out.push("{"+f.join(",")+"}");}
var doc='{"artboards":'+d.artboards.length+',"layers":'+d.layers.length+',"swatches":'+d.swatches.length
 +',"symbols":'+d.symbols.length+',"graphic_styles":'+d.graphicStyles.length+',"selected":'+d.selection.length
 +',"color_space":'+q(d.documentColorSpace)+'}';
return '{"items":['+out.join(",")+'],"document":'+doc+'}';
"""


# Apply XML to a copy of fixture item ITEM in DOC, expand it, measure what is left, remove it:
# [error, items, points, area, left, top, right, bottom] (illustrator_effects.measured).
EFFECT_JS = r"""
var d=app.documents.getByName(DOC); d.selection=null;
if(ITEM=='overlap'){var g=d.groupItems.add(); g.name='overlap';
 g.pathItems.rectangle(80,240,60,60); g.pathItems.rectangle(60,270,60,60);}
var c=d.pageItems.getByName(ITEM).duplicate(); var err='';
try{ c.applyEffect(XML); }catch(e){ err=String(e); }
d.selection=null; c.selected=true; app.executeMenuCommand('expandStyle');
var n=0,pts=0,area=0,L=1e9,T=-1e9,R=-1e9,B=1e9;
function walk(x){ n++; var g=x.geometricBounds; L=Math.min(L,g[0]);T=Math.max(T,g[1]);R=Math.max(R,g[2]);B=Math.min(B,g[3]);
 if(x.typename=='PathItem'){pts+=x.pathPoints.length; area+=Math.abs(x.area);}
 if(x.typename=='CompoundPathItem'){for(var j=0;j<x.pathItems.length;j++){pts+=x.pathItems[j].pathPoints.length;
  area+=Math.abs(x.pathItems[j].area);}}
 else if(x.pageItems){for(var i=0;i<x.pageItems.length;i++) walk(x.pageItems[i]);} }
var s=d.selection; for(var k=0;k<s.length;k++) walk(s[k]);
for(var k=s.length-1;k>=0;k--) s[k].remove();
function r(v){return Math.round(v*100)/100;}
return '['+q(err)+','+n+','+pts+','+r(area)+','+r(L)+','+r(T)+','+r(R)+','+r(B)+']';
"""


def dialog_windows(windows: list[tuple[int, str, str, bool]], *, main_hwnd: int) -> list[int]:
    """Of a program's top-level windows (hwnd, class, title, visible), the boxes to close: every
    visible one but the main window and the floating panels (OWL.*). Dialogs are standard dialog
    windows; the About box is a splash window, and left open it held the next command."""
    return [hwnd for hwnd, cls, _title, visible in windows
            if visible and hwnd != main_hwnd and not cls.startswith(PANEL_PREFIX)]


def _top_windows(pid: int) -> list[tuple[int, str, str, bool]]:
    import win32gui
    import win32process

    found: list[tuple[int, str, str, bool]] = []

    def visit(hwnd: int, _: Any) -> bool:
        try:
            if win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
                found.append((hwnd, win32gui.GetClassName(hwnd), win32gui.GetWindowText(hwnd),
                              bool(win32gui.IsWindowVisible(hwnd))))
        except win32gui.error:  # closed while the windows were listed
            pass
        return True

    win32gui.EnumWindows(visit, None)
    return found


CRASH_REPORT_TITLE = 'Error Report for "Illustrator"'


def dont_send_button(children: list[tuple[int, str, str]]) -> int | None:
    """Of a crash report's child windows (hwnd, class, text), its Don't send button."""
    return next((hwnd for hwnd, cls, text in children if cls == "Button" and text.replace("&", "") == "Don't send"), None)


_DECLINED = re.compile(r"an Illustrator error occurred: -?\d+ \(\\?'(\w+)\\?'\)")


def declined(error: str) -> str | None:
    """Illustrator's answer when it declined a command here (no dialog, at once), as a refusal
    message; None for any other error. Live effects and window commands answered 'BKey'."""
    if found := _DECLINED.search(error):
        return f"Illustrator declined the command (error {found.group(1)})"
    return None


def while_command_runs(*, handler_waiting: bool, dialogs: list[int]) -> str:
    """What to do each moment a command runs: hand the first dialog to a handler waiting for one,
    and until then close nothing but crash reports (a dialog opening between two looks went to the
    closer); with no handler, close every dialog."""
    if not handler_waiting:
        return "close_dialogs"
    return "hand_over" if dialogs else "crash_reports_only"


def documents_to_close(before: list[str], now: list[str]) -> list[str]:
    """The documents to close after a spec: the harness's own, and any not open before it."""
    return [name for name in now if name.startswith(THROWAWAY_PREFIX) or name not in before]


class IllustratorAdapter:
    def __init__(self, captures: Path) -> None:
        self.restart()  # waits for the main window: a relaunching Illustrator has none yet
        self.ocr: Any = None  # Windows OCR, started at the first dialog driven
        self.captures = captures
        captures.mkdir(parents=True, exist_ok=True)
        self.begin(ScenarioSpec("none", "none", "run"), lambda: False)

    def begin(self, spec: ScenarioSpec, should_stop: Callable[[], bool]) -> None:
        self.item_id, self.should_stop = spec.item_id, should_stop
        self.document: str | None = None
        self.before: dict[str, Any] | None = None
        self.dialogs_seen: list[dict[str, Any]] = []
        self.documents_before: list[str] = []  # read by check_documents, before anything runs
        self.dialog_path = ""  # the command whose dialog is being driven, for the sweep's control windows
        self.driven: dict[str, Any] | None = None
        self.surveyed: dict[str, Any] | None = None
        self.effect: dict[str, Any] | None = None
        self.trace: dict[str, Any] | None = None
        self.pathfinder: dict[str, Any] | None = None
        self.brushes: dict[str, Any] | None = None
        self.freehand: dict[str, Any] = {}

    def step(self, name: str, *args: Any) -> Any:
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            raise NotImplementedError(f"the Illustrator runner cannot yet do step {name!r}")
        return handler(*args)

    # Documents ------------------------------------------------------------------------------
    def _open_documents(self) -> list[str]:
        return self.ill.js('var n=[];for(var i=0;i<app.documents.length;i++)n.push(q(app.documents[i].name));'
                           'return "["+n.join(",")+"]";')

    def restart(self) -> None:
        """Reconnect to Illustrator 2026, starting it if it is gone, once its main window is up
        (it crashed mid-sweep and Adobe's crash handling relaunched it, 2026-11-25)."""
        last: Exception | None = None
        for _ in range(60):
            try:
                self.ill = Illustrator()
                self.identity = self.ill.identity()
                print(f"connected to Illustrator pid {self.identity.pid}", flush=True)
                return
            except Exception as error:  # noqa: BLE001 - still starting
                last = error
                time.sleep(5)
        raise RuntimeError(f"Illustrator did not come back within 5 minutes: {last}")

    def relaunch_if_gone(self) -> None:
        import psutil

        if not psutil.pid_exists(self.identity.pid):
            print("Illustrator is gone; reconnecting before the next spec", flush=True)
            self.restart()

    def _check_documents(self) -> None:
        open_now = self._open_documents()
        if blocker := session_blocker(open_now):
            raise RuntimeError(blocker)
        self.documents_before = open_now

    def _new_fixture(self) -> None:
        self.document = self.ill.js(FIXTURE_JS)
        self.before = self._snapshot()

    def _build_state(self, name: str) -> None:
        """Turn the fixture into one of illustrator_states.STATES; what the command then does is
        measured against the state, not the plain fixture."""
        from .illustrator_states import STATE_PRELUDE, STATES

        self.ill.js(f"var DOC={json.dumps(self.document)};" + STATE_PRELUDE + STATES[name])
        self.before = self._snapshot()

    def _snapshot(self) -> dict[str, Any]:
        return self.ill.js(f"var DOC={json.dumps(self.document)};" + SNAPSHOT_JS)

    # Dialog controls -------------------------------------------------------------------------
    def _drive_dialog_controls(self, command: str, drive: bool = True) -> None:
        """Run `command` and drive every control of the dialog it opens with the Photoshop control
        pass (control_pass.drive_dialog: Tab walk and probes, no catalogue yet), then close it,
        which cancels. Rows go to the sweep's control-actions.jsonl with no text read off the
        dialog (publishable), and the full rows beside the captures."""
        from .control_pass import controls_summary, drive_dialog
        from .dialog_surface import DialogSurface, Ocr

        self.dialog_path = command
        self.driven: dict[str, Any] | None = None

        def drive(hwnd: int) -> None:
            if self.should_stop():
                raise Interrupted("the person is back")
            time.sleep(1.5)  # previews finish drawing
            if self.ocr is None:
                self.ocr = Ocr()
            rows = drive_dialog(DialogSurface(hwnd, self.identity.pid, self.ocr, self.should_stop), [], command,
                                drive=drive)
            self._record_control_rows(rows)
            self.driven = controls_summary(rows)

        self._run_menu_command(command, on_dialog=drive)

    def _survey_dialog(self, command: str) -> None:
        """Run `command` and look at the dialog it opens (dialog_dropdowns.survey_dialog: its text
        read with no correction toward Photoshop's labels, each dropdown opened and its list read),
        then close it, which cancels. The text is Adobe's: it goes beside the captures only, and the
        sweep records counts."""
        import types

        from PIL import Image

        from .dialog_dropdowns import survey_dialog
        from .dialog_surface import DialogSurface, Ocr

        self.dialog_path = command

        def look(hwnd: int) -> None:
            if self.should_stop():
                raise Interrupted("the person is back")
            time.sleep(1.5)  # dialogs fade in and previews finish drawing
            if getattr(self, "plain_ocr", None) is None:
                self.plain_ocr = Ocr(corrector=types.SimpleNamespace(word=str))
            seen = survey_dialog(DialogSurface(hwnd, self.identity.pid, self.plain_ocr, self.should_stop))
            image = f"{self.item_id.replace(':', '_')}-survey.png"
            Image.fromarray(seen["image"]).save(self.captures / image)
            with (self.captures.parent / "dialog-survey-full.jsonl").open("a", encoding="utf-8", newline="\n") as out:
                out.write(json.dumps({"item_id": self.item_id, "image": image, "words": seen["words"],
                                      "dropdowns": seen["dropdowns"]}) + "\n")
            self.surveyed = {"image": image, "words": len(seen["words"]),
                             "dropdowns": [len(d["choices"]) for d in seen["dropdowns"]],
                             "lists_opened": sum(d["opened"] for d in seen["dropdowns"])}

        self._run_menu_command(command, on_dialog=look)

    # Live effects (illustrator_effects) -------------------------------------------------------
    def _apply_effect(self, name: str, item: str, data: str) -> None:
        """Apply live effect `name` with dictionary `data` to a copy of fixture item `item` ("overlap":
        two overlapping squares grouped, for Pathfinder), expand it, and measure what it left."""
        from .illustrator_effects import measured

        xml = f'<LiveEffect name="{name}"><Dict data="{data}"/></LiveEffect>'
        raw = self.ill.js(f"var DOC={json.dumps(self.document)};var ITEM={json.dumps(item)};"
                          f"var XML={json.dumps(xml)};" + EFFECT_JS)
        self.effect = {"effect": name, "data": data, **measured(raw)}

    def _trace_image(self, image: str, options: dict[str, Any]) -> None:
        """Place the harness's own raster `image` (illustrator_trace) in a scratch document, trace
        it with `options`, expand it and keep every path; the document closes unsaved."""
        from PIL import Image

        from .corpus import CORPUS
        from .illustrator_trace import raster, trace_js

        folder = CORPUS / "sandbox" / "trace"
        folder.mkdir(parents=True, exist_ok=True)
        png = folder / f"{THROWAWAY_PREFIX}{image}.png"
        if not png.exists():
            Image.fromarray(raster(image)).save(png)
        self.trace = {"image": image, **self.ill.js(trace_js(png.as_posix(), options))}

    def _pathfinder_curves(self, command: int) -> None:
        """Pathfinder `command` on two overlapping circles in a scratch document (illustrator_pathfinder)."""
        from .illustrator_pathfinder import pathfinder_js

        self.pathfinder = {"command": command, **self.ill.js(pathfinder_js(command))}

    # Width tool, Pencil and Simplify (illustrator_freehand) ---------------------------------
    def _freehand_document(self, kind: str) -> None:
        from .illustrator_freehand import document_js

        self.document = self.ill.js(document_js(kind))
        self.freehand = {"kind": kind, "measures": []}

    def _pencil_fidelity(self, stop: int) -> None:
        """Set the Pencil's Fidelity through its options dialog (Enter with the Pencil selected):
        a preference set by script neither shows there nor reaches the live tool (2026-11-26). The
        person's stop is read first, for restore_pencil_fidelity, and the knob is checked to have
        moved before OK."""
        from .illustrator_freehand import fidelity_slider
        from .input_plan import chord

        self._select_tool("Adobe Freehand Tool")
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        win_input.perform(chord("enter"), pid=self.identity.pid, should_stop=self.should_stop)
        dialog = self._dialog("Pencil Tool Options")
        left, top, *_ = capture.frame_bounds(dialog)

        def read() -> tuple[int, list[float], int]:
            end = time.monotonic() + 5
            while True:  # the dialog can be found before it has painted its knob
                try:
                    return fidelity_slider(capture.grab(dialog).convert("RGB"))
                except ValueError:
                    if time.monotonic() > end:
                        raise
                    time.sleep(0.25)

        at, xs, y = read()
        if getattr(self, "saved_fidelity", None) is None:
            self.saved_fidelity = at
        if at != stop:
            self._click_screen(left + round(xs[stop]), top + y)
            time.sleep(0.5)
            at, _xs, _y = read()
        if at != stop:
            self._click_word(dialog, "Cancel")
            raise RuntimeError(f"the Fidelity knob stayed at {at}, not {stop}")
        self._click_word(dialog, "OK")
        time.sleep(0.8)

    def _restore_pencil_fidelity(self) -> None:
        saved = getattr(self, "saved_fidelity", None)
        if saved is not None:
            self._pencil_fidelity(saved)
            self.saved_fidelity = None

    def _drag_points(self, points: list[list[float]], hold: list[str] | None = None) -> None:
        """Drag the selected tool through document points (pt, y up), button held from the first
        to the last. The view is first fitted into the part of the canvas no floating panel covers
        (canvas_room), and every point is checked to be over the canvas before anything is sent:
        drags under a floating dock went to the dock, not the tool (2026-11-26)."""
        import ctypes
        from ctypes import wintypes

        from .canvas_room import free_rect, points_on_canvas, view_for
        from .illustrator import canvas_rect, device_pixels_per_point, document_to_screen
        from .input_plan import KeyDown, KeyUp, MouseDown, MouseMove, MouseUp

        canvas = canvas_rect(self.identity.hwnd)
        covers = [capture.frame_bounds(h) for h, _cls, _text, visible in _top_windows(self.identity.pid)
                  if visible and h != self.identity.hwnd]
        room = free_rect(canvas, covers)
        view = self.ill.view(self.document)
        scale = device_pixels_per_point(view_bounds_mpt=view["bounds_mpt"], zoom_ppm=view["zoom_ppm"], canvas=canvas)
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        centre, zoom = view_for((min(xs), min(ys), max(xs), max(ys)), room, canvas, float(scale), margin=0.15)
        self.ill.set_view(self.document, center_mpt=centre, zoom_ppm=zoom)
        view = self.ill.view(self.document)
        scale = device_pixels_per_point(view_bounds_mpt=view["bounds_mpt"], zoom_ppm=view["zoom_ppm"], canvas=canvas)
        screen = [document_to_screen((round(x * 1000), round(y * 1000)), center_mpt=tuple(view["center_mpt"]),
                                     zoom_ppm=view["zoom_ppm"], canvas=canvas, device_pixels_per_point=scale) for x, y in points]
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)

        def top_window_at(point: tuple[int, int]) -> int:
            return ctypes.windll.user32.GetAncestor(ctypes.windll.user32.WindowFromPoint(wintypes.POINT(*point)), 2)

        covered = points_on_canvas(screen, top_window_at, self.identity.hwnd)
        if covered:
            raise RuntimeError(f"{len(covered)} of {len(screen)} drag points are not over the canvas, e.g. {covered[:3]}")
        keys = hold or []
        lead = MouseMove(screen[0][0] + 6, screen[0][1] + 6)  # a press with no move before it can be ignored
        events = [lead, MouseMove(*screen[0]), *(KeyDown(k) for k in keys), MouseDown(), *(MouseMove(*p) for p in screen[1:])]
        win_input.perform(events, pid=self.identity.pid, delay_s=0.03, should_stop=self.should_stop)  # releases itself if stopped
        time.sleep(0.4)  # a release straight after the last move dropped that move (Pencil, 2026-11-26)
        win_input.perform([MouseUp(), *(KeyUp(k) for k in reversed(keys))], pid=self.identity.pid, delay_s=0.03)
        time.sleep(1.0)
        self.freehand.setdefault("drags", []).append(points)
        self.freehand.setdefault("screen_px_per_pt", []).append(round(float(scale), 4))  # a tool's pixel tolerances in document points

    def _outline_paths(self) -> None:
        from .illustrator_freehand import OUTLINE_JS

        self.freehand["measures"].append({"outline": self.ill.js(OUTLINE_JS)})

    def _all_paths(self) -> None:
        from .illustrator_freehand import ALL_PATHS_JS

        self.freehand["measures"].append({"paths": self.ill.js(ALL_PATHS_JS)})

    def _simplify_selected(self) -> None:
        """Object > Path > Simplify at its automatic amount; its floating slider is closed by Enter."""
        from .input_plan import chord

        self.ill.js("app.executeMenuCommand('simplify menu item');return 'null';")
        time.sleep(1.5)
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        win_input.perform(chord("enter"), pid=self.identity.pid, should_stop=self.should_stop)
        time.sleep(1.0)
        self._answer_dialogs()

    # Art and pattern brushes (illustrator_brushes) -----------------------------------------
    def _brush_document(self) -> None:
        from .illustrator_brushes import document_js

        self.document = self.ill.js(document_js())

    def _ocr_words(self, hwnd: int) -> list[dict[str, Any]]:
        import numpy as np

        if self.ocr is None:
            from .dialog_surface import Ocr

            self.ocr = Ocr()
        return self.ocr.words(np.asarray(capture.grab(hwnd).convert("RGB")))

    def _click_screen(self, x: int, y: int) -> None:
        from .input_plan import click

        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        win_input.perform(click((x, y)), pid=self.identity.pid, should_stop=self.should_stop)

    def _click_word(self, hwnd: int, text: str) -> None:
        left, top, *_ = capture.frame_bounds(hwnd)
        found = [w for w in self._ocr_words(hwnd) if w["text"] == text]
        if not found:
            raise RuntimeError(f"no {text!r} in the window read")
        w = found[0]
        self._click_screen(left + w["x"] + w["w"] // 2, top + w["y"] + w["h"] // 2)

    def _dialog(self, title: str, timeout_s: float = 10) -> int:
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            for hwnd, cls, text, visible in _top_windows(self.identity.pid):
                if visible and cls == "#32770" and text == title:
                    return hwnd
            time.sleep(0.25)
        raise RuntimeError(f"the {title!r} dialog did not open")

    def _type_into(self, hwnd: int, word: str, text: str) -> None:
        """Click the field showing `word` (OCR), replace its text with `text` and Tab out."""
        from .input_plan import chord

        self._click_word(hwnd, word)
        events = chord("ctrl+a") + [e for ch in text for e in chord(ch)] + chord("tab")
        win_input.perform(events, pid=self.identity.pid, should_stop=self.should_stop)
        time.sleep(0.4)

    def _set_pattern_options(self, dialog: int, settings: dict[str, Any]) -> None:
        """One Pattern Brush Options setting (illustrator_brushes.PATTERN_OPTIONS), checked by
        reading the dialog again before OK."""
        if "scale" in settings:
            self._type_into(dialog, "100%", str(settings["scale"]))
            expect = f"{settings['scale']}%"
        elif "spacing" in settings:
            self._type_into(dialog, "0%", str(settings["spacing"]))
            expect = f"{settings['spacing']}%"
        elif "fit" in settings:
            self._click_word(dialog, {"add_space": "Add", "approximate": "Approximate"}[settings["fit"]])
            expect = None
        elif settings.get("flip_along"):
            self._click_word(dialog, "Along")
            expect = None
        else:
            raise ValueError(f"no pattern option in {settings}")
        time.sleep(0.4)
        if expect and expect not in {w["text"] for w in self._ocr_words(dialog)}:
            self._click_word(dialog, "Cancel")
            raise RuntimeError(f"the options dialog did not show {expect} after typing it")

    def _define_brush(self, kind: str, settings: dict[str, Any] | None = None) -> None:
        """Make a brush of the selected art through the Brushes panel's New Brush button and its
        dialogs, at their defaults or with one pattern option changed (`settings`). The panel is
        opened from the Window menu when no dock shows it."""
        from .illustrator_brushes import KINDS

        radio, _name, options = KINDS[kind]

        def brushes_dock() -> tuple[int, dict[str, Any]] | None:
            for hwnd, cls, _text, visible in _top_windows(self.identity.pid):
                if visible and cls == "OWL.Dock":
                    for w in self._ocr_words(hwnd):
                        if w["text"] == "Brushes":
                            return hwnd, w
            return None

        found = brushes_dock()
        if found is None:
            self.ill.js("app.executeMenuCommand('Adobe BrushManager Menu Item');return '1';")
            time.sleep(1.5)
            found = brushes_dock()
        if found is None:
            raise RuntimeError("the Brushes panel could not be found")
        dock, tab = found
        left, top, right, bottom = capture.frame_bounds(dock)
        self._click_screen(left + tab["x"] + tab["w"] // 2, top + tab["y"] + tab["h"] // 2)
        time.sleep(0.6)
        self._click_screen(right - 76, bottom - 25)  # the New Brush button, bottom right of the panel
        chooser = self._dialog("New Brush")
        self._click_word(chooser, radio)
        self._click_word(chooser, "OK")
        dialog = self._dialog(options)
        if settings:
            time.sleep(0.6)
            self._set_pattern_options(dialog, settings)
        self._click_word(dialog, "OK")
        time.sleep(1.0)

    def _brush_paths(self, brush: str) -> None:
        from .illustrator_brushes import apply_js

        self.brushes = {"brush": brush, "paths": self.ill.js(apply_js(brush))}
        self.document = None

    def _record_control_rows(self, rows: list[dict[str, Any]]) -> None:
        from .control_pass import publishable

        at = time.strftime("%Y-%m-%dT%H:%M:%S")
        for path, shape in ((self.captures.parent / "control-actions-full.jsonl", dict),
                            (self.captures.parent / "control-actions.jsonl", lambda r: publishable(r, set()))):
            with path.open("a", encoding="utf-8", newline="\n") as out:
                for row in rows:
                    out.write(json.dumps({"item_id": self.item_id, "at": at, **shape(row)}) + "\n")

    # Tools (illustrator_tools) --------------------------------------------------------------
    def _select_tool(self, tool: str) -> None:
        try:
            self.ill.select_tool(tool)
        except Exception as error:  # noqa: BLE001 - Illustrator declining the tool here
            if refusal := declined(str(error)):
                raise Refused(refusal) from error
            raise

    def _use_tool(self, kind: str, commit: str) -> None:
        """Use the selected tool on the fixture: Photoshop's gesture shapes (planned on a 600 x 400
        chart) scaled onto the artboard, sent where Illustrator shows it now, then ended with
        `commit` where the tool waits; any box it opens is captured and closed."""
        from .illustrator import canvas_rect, device_pixels_per_point, document_to_screen
        from .input_plan import chord
        from .tool_gestures import gesture_events

        self.ill.js('app.executeMenuCommand("fitin");return "null";')  # the artboard fills the window
        view = self.ill.view(self.document)
        left, top, _right, _bottom = self.ill.geometry(self.document)["artboard_rects_mpt"][0]
        canvas = canvas_rect(self.identity.hwnd)
        scale = device_pixels_per_point(view_bounds_mpt=view["bounds_mpt"], zoom_ppm=view["zoom_ppm"], canvas=canvas)

        def to_screen(x: float, y: float) -> tuple[int, int]:
            point = (round(left + x * 400 / 600 * 1000), round(top - y * 300 / 400 * 1000))
            return document_to_screen(point, center_mpt=tuple(view["center_mpt"]), zoom_ppm=view["zoom_ppm"],
                                      canvas=canvas, device_pixels_per_point=scale)

        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        win_input.perform(gesture_events(kind, to_screen), pid=self.identity.pid, should_stop=self.should_stop)
        if commit:
            win_input.perform(chord(commit), pid=self.identity.pid, should_stop=self.should_stop)
        settle = time.monotonic() + 2.0
        while time.monotonic() < settle:
            self._answer_dialogs()
            time.sleep(0.3)

    def _close_throwaway_document(self) -> None:
        """Close the harness's documents and any document a command made during this spec
        (File > New), without saving; a document open before the spec is never touched."""
        self._answer_dialogs()
        for name in documents_to_close(self.documents_before, self._open_documents()):
            self.ill.js(f"app.documents.getByName({json.dumps(name)}).close(SaveOptions.DONOTSAVECHANGES);"
                        "return 'null';")

    # Acting ---------------------------------------------------------------------------------
    def _run_menu_command(self, command: str, on_dialog: Callable[[int], None] | None = None) -> None:
        """executeMenuCommand with alerts shown, in a worker thread (a dialog holds the call
        until it is answered); dialogs are captured and closed meanwhile. `on_dialog`, if given,
        gets the first dialog's window before it is closed (its controls are driven)."""
        done: dict[str, Any] = {}
        pending = [on_dialog] if on_dialog else []

        def work() -> None:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            try:
                app = win32com.client.GetActiveObject("Illustrator.Application.30")
                app.DoJavaScript("var __u=app.userInteractionLevel;app.userInteractionLevel="
                                 f"UserInteractionLevel.DISPLAYALERTS;try{{app.executeMenuCommand({json.dumps(command)});}}"
                                 'finally{app.userInteractionLevel=__u;}"null";')
            except Exception as error:  # noqa: BLE001 - reported below
                done["error"] = error
            finally:
                pythoncom.CoUninitialize()

        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        deadline = time.monotonic() + COMMAND_TIMEOUT_S
        while worker.is_alive():
            if time.monotonic() > deadline:
                raise TimeoutError(f"{command} did not return within {COMMAND_TIMEOUT_S} s")
            found = dialog_windows(_top_windows(self.identity.pid), main_hwnd=self.identity.hwnd) if pending else []
            action = while_command_runs(handler_waiting=bool(pending), dialogs=found)
            if action == "hand_over":
                pending.pop()(found[0])
                deadline = time.monotonic() + COMMAND_TIMEOUT_S  # driving took its own time
                self._answer_dialogs()
            elif action == "crash_reports_only":
                self._answer_crash_reports()
            else:
                self._answer_dialogs()
            worker.join(0.3)
        if "error" in done:
            if refusal := declined(str(done["error"])):
                raise Refused(refusal) from done["error"]
            raise done["error"]

    def _answer_crash_reports(self) -> int:
        """Answer Illustrator's crash reporter with Don't send (never Generate report)."""
        import win32con
        import win32gui

        reports: list[int] = []
        win32gui.EnumWindows(lambda h, _: reports.append(h) if win32gui.IsWindowVisible(h)
                             and win32gui.GetWindowText(h).startswith(CRASH_REPORT_TITLE) else None or True, None)
        for report in reports:
            children: list[tuple[int, str, str]] = []
            win32gui.EnumChildWindows(report, lambda c, _: children.append(
                (c, win32gui.GetClassName(c), win32gui.GetWindowText(c))) or True, None)
            if (button := dont_send_button(children)) is not None:
                win32gui.PostMessage(button, win32con.BM_CLICK, 0, 0)
                self.dialogs_seen.append({"class": "crash_report", "answer": "dont_send"})
                time.sleep(1.0)
        return len(reports)

    def _answer_dialogs(self) -> int:
        import win32con
        import win32gui

        self._answer_crash_reports()
        answered = 0
        windows = _top_windows(self.identity.pid)
        classes = {hwnd: cls for hwnd, cls, _title, _visible in windows}
        for hwnd in dialog_windows(windows, main_hwnd=self.identity.hwnd):
            if not win32gui.IsWindow(hwnd):  # the About box's two windows close together
                continue
            path = self.captures / f"{self.item_id.replace(':', '_')}-dialog-{len(self.dialogs_seen)}.png"
            try:
                sha = capture.capture_window(hwnd, path)
            except Exception:  # noqa: BLE001 - a dialog closing as it is captured
                sha = None
            self.dialogs_seen.append({"class": classes[hwnd], "image": path.name, "sha256": sha, "answer": "close"})
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except win32gui.error:  # gone in the meantime
                continue
            answered += 1
            time.sleep(0.5)
        return answered

    def _cancel_dialogs(self) -> None:
        for _ in range(5):
            if not self._answer_dialogs():
                return

    # Recording ------------------------------------------------------------------------------
    def _record(self, *kinds: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for kind in kinds:
            if kind == "dialogs":
                out["dialogs"] = self.dialogs_seen

            elif kind == "controls":
                out["controls"] = self.driven
            elif kind == "survey":
                out["survey"] = self.surveyed
            elif kind == "effect":
                out["effect"] = self.effect
            elif kind == "trace":
                out["trace"] = self.trace
            elif kind == "pathfinder":
                out["pathfinder"] = self.pathfinder
            elif kind == "brushes":
                out["brushes"] = self.brushes
            elif kind == "freehand":
                out["freehand"] = self.freehand
            elif kind == "document":
                if self.document in self._open_documents() and self.before is not None:
                    out["document"] = vector_change(self.before, self._snapshot())
                else:
                    out["document"] = {"document_closed": True}
            else:
                raise NotImplementedError(f"cannot record {kind!r} yet")
        return out


def _sampled_sweep(folder: Path, dialog_of: Callable[[], str] = lambda: "") -> Any:
    """A SampledSweep sampling Illustrator's interface thread, and its busiest others, in every
    decompiled Illustrator binary."""
    from .corpus import CORPUS
    from .sampled_sweep import SampledSweep, watched_binaries
    from .stack_sampler import sample_process, ui_thread

    watch, indexes = watched_binaries(CORPUS, "illustrator")
    print(f"sampling {len(watch)} decompiled Illustrator binaries")

    def start(pid: int, stop: threading.Event, out: Path) -> None:
        for _ in range(120):
            if (tid := ui_thread(pid, "illustrator")) is not None:
                stats = sample_process(pid, tid, watch, indexes, out, stop)
                print(f"sampler for pid {pid} stopped: {json.dumps(stats)}")
                return
            if stop.wait(1):
                return

    def pids() -> list[int]:
        return [pid for pid, *_ in _illustrator_pids()]

    return SampledSweep(folder, start, pids=pids, dialog_of=lambda: dialog_of() or None)


def _illustrator_pids() -> list[tuple[int]]:
    from .illustrator import _running_illustrators

    return [(pid,) for pid, _path in _running_illustrators()]


def main() -> None:
    """python -m scripts.adobe_observed_truth.runner_illustrator --dataset <dir> --specs <file> [--sample <dir>] [--now]"""
    from .idle import RealInputWatcher
    from .runner_photoshop import away_after_s, install_session_guard

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--specs", default="menu-families.jsonl")
    parser.add_argument("--sample", type=Path, help="sweep folder: stack-sample Illustrator throughout")
    parser.add_argument("--now", action="store_true", help="attended: do not wait to be away")
    parser.add_argument("--only", help="comma-separated item ids to run")
    parser.add_argument("--idle-minutes", type=float, default=10.0)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    rows = [json.loads(line) for line in (args.dataset / args.specs).read_text(encoding="utf-8").splitlines() if line]
    specs = [ScenarioSpec(**{**r, "steps": tuple(map(tuple, r["steps"])), "never_press": tuple(r["never_press"])})
             for r in rows]
    folder = args.sample or args.dataset
    folder.mkdir(parents=True, exist_ok=True)
    results_path = folder / "results.jsonl"
    done: set[str] = set()
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["status"] in ("ok", "refused") or (row["status"] == "failed" and not args.retry_failed):
                done.add(row["item_id"])
            elif args.retry_failed:
                done.discard(row["item_id"])
    queue = plan_queue(specs, done)
    if args.only:
        wanted = set(args.only.split(","))
        queue = [s for s in specs if s.item_id in wanted and s.safety == "run"]
    print(f"{len(queue)} specs queued ({len(done)} already done)")

    watcher = RealInputWatcher()
    threshold = away_after_s(now=args.now, idle_minutes=args.idle_minutes)
    install_session_guard(watcher.idle_s, threshold)
    win_input.make_dpi_aware()
    adapter = IllustratorAdapter(folder / "captures")
    from .corpus import CORPUS

    stop_file = CORPUS / "STOP-RUNNER"  # beside the sweeps, as the sweep scripts check it

    def run_one(spec: ScenarioSpec, should_stop: Any) -> RunResult:
        adapter.relaunch_if_gone()
        adapter.begin(spec, should_stop)
        adapter.step("check_documents")
        result = execute(spec, adapter, should_stop)
        print(f"{result.status:12} {spec.item_id}  {result.error or ''}", flush=True)
        return result

    def write(result: RunResult) -> None:
        row = {"item_id": result.item_id, "status": result.status, "observations": result.observations,
               "error": result.error, "cleanup_errors": result.cleanup_errors, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with results_path.open("a", encoding="utf-8", newline="\n") as out:
            out.write(json.dumps(row) + "\n")

    sweep = _sampled_sweep(args.sample, lambda: adapter.dialog_path) if args.sample else None
    if sweep is not None:
        plain = run_one

        def run_one(spec: ScenarioSpec, should_stop: Any) -> RunResult:  # noqa: F811
            with sweep.spec(spec.item_id, spec.family):
                return plain(spec, should_stop)

    import contextlib

    from .control_drivers import timed

    try:
        # Each control action's time window goes to the sweep's timeline, tagged with its dialog.
        with timed(sweep.control_acted) if sweep is not None else contextlib.nullcontext():
            run_session(queue, run_one, watcher.idle_s, threshold_s=threshold, sleep=time.sleep, write=write,
                        recover=adapter.restart, should_quit=stop_file.exists)
    finally:
        if sweep is not None:
            sweep.close()
    print("queue finished")


if __name__ == "__main__":
    main()
