"""Carry out runner steps on the real Photoshop (live adapter; proven by running it).

    python -m scripts.adobe_observed_truth.runner_photoshop --dataset <dir> [--limit N] [--now]

Waits until the person has been away 20 minutes (or runs at once with --now, attended), then
works through scenario-families.jsonl, appending each result to results.jsonl in the dataset
folder. Dialog images go to the local captures folder, not the repo. Stop with Ctrl+C; the
next run resumes after the last written result.
"""

from __future__ import annotations

import contextlib
import ctypes
import functools
import json
import re
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from . import adjust_probe, brush_probe, heal_probe, canvas, capture, channel_probe, effect_probe, lasso_probe, layer_probe, pen_probe, resample_probe, parity, photoshop, retouch_probe, selection_probe, smudge_probe, test_images, tipmix_probe, win_input
from . import ps_pixels as px
from . import ps_tools as tools
from .action_settings import event_script, settings_of
from .control_drivers import timed
from .control_pass import (
    catalogued,
    controls_summary,
    drive_dialog,
    known_labels,
    publishable,
)
from .corpus import CORPUS
from .dialog_surface import DialogSurface, Ocr, answer_file_dialog, is_file_dialog
from .dialog_work import make_input
from .document_states import STATES
from .families import ScenarioSpec, panel_menu_path, session_blocker
from .idle import ATTENDED_QUIET_S, Interrupted
from .input_plan import chord, click
from .inventory import load_inventory
from .panel_flyouts import read_flyouts
from .ps_pixels import canvas_change, pixels_sha256
from .run import preflight
from .runner import (
    Blocked,
    Refused,
    RunResult,
    done_items,
    execute,
    plan_queue,
    run_session,
)
from .sweeps import replay_script
from .tool_gestures import gesture_events
from .uxp_bridge import PLUGIN_PORT, Bridge, require_photoshop
from .workspace import likeness, locate, plane_clicks, trim_frame

EXE = Path(r"C:\Program Files\Adobe\Adobe Photoshop 2026\Photoshop.exe")
# Prefixes of the executable names (what _program returns) of Adobe programs a probe may launch.
_OTHER_ADOBE_PROGRAMS = ("Creative Cloud", "Adobe Bridge", "Adobe Desktop")
WM_CLOSE = photoshop.WM_CLOSE
_SELECT_TOOL = (
    "var d=new ActionDescriptor(),r=new ActionReference();r.putClass(stringIDToTypeID(%s));"
    'd.putReference(charIDToTypeID("null"),r);executeAction(charIDToTypeID("slct"),d,DialogModes.NO);'
)
# The preset manager's list for one class, its size in n (Define dialogs add to these).
# The preset manager's class per kind, as ExtendScript: patterns are listed under the char code
# PttR, which has no string ID (stringIDToTypeID('pattern') is another class: looked up by it,
# patterns seemed missing from the list, 2026-11-26).
_PRESET_CLASS = {"pattern": "charIDToTypeID('PttR')", "brush": "stringIDToTypeID('brush')",
                 "shape": "stringIDToTypeID('customShape')"}
_PRESETS_JS = (
    "var cls=%s,r=new ActionReference();"
    "r.putProperty(charIDToTypeID('Prpr'),stringIDToTypeID('presetManager'));"
    "r.putEnumerated(charIDToTypeID('capp'),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));"
    "var m=executeActionGet(r).getList(stringIDToTypeID('presetManager')),n=-1;"
    "for(var k=0;k<m.count;k++)if(m.getObjectType(k)==cls)n=m.getObjectValue(k).getList(charIDToTypeID('Nm  ')).count;"
    "if(n<0)throw new Error('no preset list for this class');"
)
# The active document's visible pixels as a PNG copy at %s. PNG cannot hold CMYK, Lab,
# Multichannel, Duotone or 32 bits: those are saved from an RGB (or Grayscale) duplicate, so
# no Save a Copy dialog asks (Image > Mode > CMYK Color, 2026-11-24). Dialogs are off meanwhile.
_EXPORT_PNG = (
    "var f=new File(%s),d=app.activeDocument,m=d.mode,dd=app.displayDialogs;"
    "app.displayDialogs=DialogModes.NO;"
    "try{var png=(m==DocumentMode.RGB||m==DocumentMode.GRAYSCALE||m==DocumentMode.INDEXEDCOLOR"
    "||m==DocumentMode.BITMAP)&&d.bitsPerChannel!=BitsPerChannelType.THIRTYTWO;"
    "if(png){d.saveAs(f,new PNGSaveOptions(),true,Extension.LOWERCASE);}"
    "else{var c=d.duplicate('observed-truth-export');"
    "try{if(c.bitsPerChannel==BitsPerChannelType.THIRTYTWO)c.bitsPerChannel=BitsPerChannelType.SIXTEEN;"
    "if(c.mode!=DocumentMode.RGB){try{c.changeMode(ChangeMode.RGB);}catch(e){c.changeMode(ChangeMode.GRAYSCALE);}}"
    "c.saveAs(f,new PNGSaveOptions(),true,Extension.LOWERCASE);}"
    "finally{c.close(SaveOptions.DONOTSAVECHANGES);app.activeDocument=d;}}}"
    'finally{app.displayDialogs=dd;}"null";'
)

# A dialog's work done by script when its window needs a button pressed first (Choose…, Browse…,
# Save…): each reads `in/` and writes `out/` of its own sandbox folder, never anywhere else
# (dialog_work.RECIPES, 2026-11-24). Batch has none: app.batch opened its window instead.
RECIPES: dict[str, str] = {
    "pdf_presentation": (
        "var o=new PresentationOptions();o.presentation=false;"
        'app.makePDFPresentation([new File(%(input)s)],new File(%(out_file)s),o);"null";'
    ),
    "save_for_web": (
        "var o=new ExportOptionsSaveForWeb();o.format=SaveDocumentType.PNG;o.PNG8=false;"
        'app.activeDocument.exportDocument(new File(%(out_file)s),ExportType.SAVEFORWEB,o);"null";'
    ),
}
_RECIPE_OUTPUTS = {"pdf_presentation": "presentation.pdf", "save_for_web": "web.png"}


def recipe_script(name: str, folder: Path) -> str:
    """Recipe `name`'s script for its sandbox `folder` (`in/` the chart, `out/` empty)."""
    out = folder / "out"
    return RECIPES[name] % {
        "input": json.dumps((folder / "in" / f"{photoshop.THROWAWAY_PREFIX}chart.png").as_posix()),
        "out_file": json.dumps((out / f"{photoshop.THROWAWAY_PREFIX}{_RECIPE_OUTPUTS[name]}").as_posix()),
    }


class PhotoshopAdapter:
    def __init__(self, bridge: Bridge, inventory: list[Any], sandbox: Path, captures: Path) -> None:
        self.bridge, self.sandbox, self.captures = bridge, sandbox, captures
        self.menu_commands = {
            i.path: i.facts["command"] for i in inventory if i.kind == "menu_command"
        }
        self.panel_names = {
            i.id.removeprefix("panel:"): i.name for i in inventory if i.kind == "panel"
        }
        self.workspace_commands = [
            i.facts["command"]
            for i in inventory
            if i.kind == "menu_command" and i.path.startswith("Window > Workspace > ")
        ]
        # Names of the open documents at the last good reading; None until one succeeds.
        self.documents_seen: list[str] | None = None
        self.documents_seen_at = 0.0  # time.monotonic() of that reading
        # Seconds since the person's last real input; the default never allows a force-quit.
        self.idle_s: Callable[[], float] = lambda: 0.0
        # Takes the parity observation (REA observe_native_ui) of a Photoshop process; what
        # each result names as `parity`. None until main() gives the runner an observer.
        self.observe_parity: Callable[[photoshop.Identity], dict[str, Any] | None] = (
            lambda identity: None
        )
        self.parity: dict[str, Any] | None = None
        # Catalogued controls of a menu path (control_pass.catalogued); where rows are written.
        self.catalogue: Callable[[str], list[dict[str, Any]]] = lambda path: []
        self.control_actions: Path | None = None
        self.known_labels: set[str] | None = None  # the only text a published row may carry
        self.ocr: Ocr | None = None  # one OCR reader process for the whole run
        self._connect()
        self.begin(ScenarioSpec("", "", "run"), lambda: False)

    def _connect(self) -> None:
        self.ps = photoshop.Photoshop()
        self.identity = self.ps.identity()

    def begin(self, spec: ScenarioSpec, should_stop: Callable[[], bool]) -> None:
        """Start a spec with no snapshots left over from the last one."""
        self.item_id, self.should_stop = spec.item_id, should_stop
        self.dialogs_seen: list[dict[str, Any]] = []
        self.documents_before: list[int] | None = None
        self.panels_before: set[str] | None = None
        self.windows_before: set[int] | None = None  # window handles at the snapshot
        self.workspace_before: int | None = None
        self.never_press = spec.never_press
        self.accept_dialogs = False
        self.test_image: str | None = None
        self.pixels_before: np.ndarray | None = None
        self.event_settings: dict[str, Any] | None = None
        self.sweep: dict[str, Any] | None = None
        self.brush: dict[str, Any] | None = None  # the brush probe's stroke: options, points, size
        self.retouch: dict[str, Any] | None = None  # the retouch probe's tool options as read back
        self.tipmix: dict[str, Any] | None = None  # the texture and dual-tip probe's options as set and read back
        self.heal: dict[str, Any] | None = None  # the healing probe's tool options as set and read back
        self.smudge: dict[str, Any] | None = None  # the smudge probe's tool options as set and read back
        self.blend: dict[str, Any] | None = None  # the layer probe's blend mode, opacity and image kind
        self.saved_tools: dict[str, Any] | None = None  # save_tool_state's snapshot, for restore_tool_state
        self.recipe: str | None = None  # the recipe this spec ran (run_recipe)
        self.dialog_task: str | None = None
        self.workspace: dict[str, Any] | None = None
        self.dialog_path, self.expected = "", []
        self.controls: dict[str, Any] | None = None
        self.flyouts: list[dict[str, Any]] | None = None
        self.view: Any = None  # the chart's place on screen, read before an accepted command
        self.presets_before: int | None = None  # before a Define dialog: only newer ones are deleted
        self.file_answer: Path | None = None  # the sandbox file the next file dialog is given

    def step(self, name: str, *args: Any) -> Any:
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            raise NotImplementedError(f"the runner cannot yet do step {name!r}")
        if _photoshop_hung(self.identity.pid):
            # A scripting call to a hung Photoshop never returns (Fibers, 2026-11-09).
            raise TimeoutError(f"Photoshop is not responding; step {name!r} not attempted")
        try:
            return handler(*args)
        except (Refused, Blocked, Interrupted):
            raise
        except Exception as error:
            if refusal := photoshop_refusal(str(error)):  # Photoshop answered: not stuck
                raise Refused(refusal) from error
            raise

    # Documents and the sandbox ---------------------------------------------------------
    def _read_documents(self) -> list[str]:
        names = [d["name"] for d in self.ps.open_documents()]
        self.documents_seen, self.documents_seen_at = names, time.monotonic()
        return names

    def _require_only_harness_documents(self) -> None:
        if reason := session_blocker(self._read_documents()):
            raise Blocked(reason)

    def _check_documents(self) -> None:
        """Note what is open before each spec, so a restart knows whether it may force-quit.
        A stuck Photoshop answers nothing; the last reading then stands, and counts only if it
        was taken after the person last touched the machine."""
        try:
            self._read_documents()
        except Exception:  # noqa: BLE001, S110 - keep the last good reading
            pass

    def _new_throwaway_document(self) -> None:
        self.ps.new_document("probe", 400, 300)

    def _save_throwaway_to_sandbox(self) -> None:
        self.ps.save_throwaway_to_sandbox(self.sandbox)

    def _snapshot_documents(self) -> None:
        self.documents_before = [d["id"] for d in self.ps.open_documents()]

    def _close_new_documents(self) -> None:
        if self.documents_before is not None:  # no snapshot: only harness documents get closed
            self.ps.close_new_documents(self.documents_before)

    def _close_throwaway_document(self) -> None:
        # Dialogs are answered meanwhile: a Save As a command opened late, past its dialog
        # check, held the close for 6 minutes (2026-11-24).
        script = (
            "for(var i=app.documents.length-1;i>=0;i--){var d=app.documents[i];"
            f"if(d.name.indexOf({json.dumps(photoshop.THROWAWAY_PREFIX)})===0)"
            'd.close(SaveOptions.DONOTSAVECHANGES);}"null";'
        )
        self._drive(lambda: _js_in_own_apartment(script))

    # Brush probe (brush_probe) ----------------------------------------------------------------
    def _brush_canvas(self) -> None:
        """A throwaway document with an empty paint layer, black on white; the person's brush
        options and colours are kept to be written back (brush_restore, a clean-up step)."""
        self.ps.new_document("brush", brush_probe.WIDTH, brush_probe.HEIGHT)
        self.ps.js(f'app.activeDocument.artLayers.add().name={json.dumps(_PAINT_LAYER)};"null";')
        saved = self._drive(lambda: tools.snapshot_tool_state(_OWN_APARTMENT, ["brush"]))
        self.brush = {"saved": saved}
        tools.set_colours(self.ps, foreground=(0, 0, 0))

    def _brush_stroke(self, options: dict[str, Any], points: list[list[int]]) -> None:
        """Set the brush and stroke; with `pressure` (size, opacity or both) the options bar's
        pressure switches go on and Photoshop simulates pen pressure along the stroke."""
        pressure = options.get("pressure")
        tip = {k: v for k, v in options.items() if k != "pressure"}
        switches = {"pressure_size": pressure in ("size", "both"), "pressure_opacity": pressure in ("opacity", "both")}
        read_back = self._drive(lambda: tools.set_brush_options(_OWN_APARTMENT, "brush", **tip, **switches))
        self.brush = {**(self.brush or {}), "read_back": {**read_back, "pressure": pressure},
                      "points": points, "size": options["size_px"]}
        self._drive(lambda: tools.stroke(_OWN_APARTMENT, "brush", [tuple(p) for p in points],
                                         simulate_pressure=pressure is not None))

    def _pen_stroke(self, options: dict[str, Any], points: list[list[int]], pen: dict[str, list]) -> None:
        """Set the brush, then paint `points` (document pixels) with a synthetic pen through
        Windows pointer input (pen_input), carrying `pen`'s pressures (0..1), tilts and rotations
        frame by frame (pen_probe)."""
        import ctypes
        from ctypes import wintypes

        from . import pen_input
        from .canvas_room import points_on_canvas

        self.ps.bring_to_front()  # Photoshop refuses a script's tool selection in the background
        read_back = self._drive(lambda: tools.set_brush_options(_OWN_APARTMENT, "brush", **options))
        self.brush = {**(self.brush or {}), "read_back": {**read_back, "pen": True}, "points": points, "size": options["size_px"]}
        view = canvas.read_view(self.ps, self.identity)
        screen = [tuple(int(v) for v in canvas.document_to_screen(view, x, y)) for x, y in points]
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)

        def top_window_at(point: tuple[int, int]) -> int:
            return ctypes.windll.user32.GetAncestor(ctypes.windll.user32.WindowFromPoint(wintypes.POINT(*point)), 2)

        covered = points_on_canvas(screen, top_window_at, self.identity.hwnd)
        if covered:
            raise RuntimeError(f"{len(covered)} of {len(screen)} pen points are not over Photoshop, e.g. {covered[:3]}")
        frames = pen_input.pen_frames(screen, pen["pressures"], pen.get("tilts"), pen.get("rotations"))
        pen_input.inject(frames, should_stop=self.should_stop)
        time.sleep(1.0)

    def _brush_restore(self) -> None:
        saved = (self.brush or {}).get("saved")
        if saved is None:
            return
        restored = self._drive(lambda: tools.restore_tool_state(_OWN_APARTMENT, saved))
        self.brush["saved"] = None
        if not tools.all_restored(restored):
            raise RuntimeError(f"brush options or colours did not read back as they were: {restored}")

    def _lasso_trace(self, options: dict[str, Any], points: list[list[float]], mode: str = "clicks") -> None:
        """Magnetic Lasso with `options` (its option keys) round `points` (document pixels), closed
        with Enter (lasso_probe). "clicks": a click at every point; "moves": one click, then the
        mouse moved through the rest, so the tool lays its own anchors. Every point is first
        checked to be over Photoshop's window: earlier move runs went where another app's window
        lay, and looked as if the tool ignored moves (2026-11-26). The pointer then comes to the
        first point from beside it: a trace starting where the last one ended got no mouse move
        before its press, Photoshop ignored the press, and the trace came back empty."""
        import ctypes
        from ctypes import wintypes

        from .canvas_room import points_on_canvas
        from .input_plan import MouseMove

        self.ps.bring_to_front()  # Photoshop refuses a script's tool selection in the background
        self.lasso = self._drive(lambda: tools.set_tool_options(_OWN_APARTMENT, "magnetic_lasso", options))
        view = canvas.read_view(self.ps, self.identity)
        screen = [canvas.document_to_screen(view, x, y) for x, y in points]
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)

        def top_window_at(point: tuple[int, int]) -> int:
            return ctypes.windll.user32.GetAncestor(ctypes.windll.user32.WindowFromPoint(wintypes.POINT(*point)), 2)

        covered = points_on_canvas(screen, top_window_at, self.identity.hwnd)
        if covered:
            raise RuntimeError(f"{len(covered)} of {len(screen)} lasso points are not over Photoshop, e.g. {covered[:3]}")
        # The pointer arrives from beside the first point: a click where it already stood (the
        # last trace ended there) comes with no mouse move, and Photoshop ignored that press.
        lead = [MouseMove(screen[0][0] + 6, screen[0][1] + 6)]
        if mode == "moves":
            events = lead + click(screen[0]) + [MouseMove(*p) for p in screen[1:]]
        else:
            events = lead + [e for p in screen[:-1] for e in click(p)]
        win_input.perform(events, pid=self.identity.pid, delay_s=0.03, should_stop=self.should_stop)
        win_input.perform(chord("enter"), pid=self.identity.pid, should_stop=self.should_stop)
        time.sleep(1.0)

    def _effect_document(self) -> None:
        """The layer effect probe's document: white page, the harness's own black square on a layer."""
        self.ps.js(effect_probe.document_js())

    def _layer_effect(self, kind: str, params: dict[str, Any]) -> None:
        self.ps.js(effect_probe.effect_js(kind, params))

    def _adjust(self, kind: str, params: dict[str, Any]) -> None:
        """One adjustment by its event, settings in the descriptor (adjust_probe)."""
        self.ps.js(adjust_probe.adjust_js(kind, params))

    def _resize_image(self, size: int, method: str) -> None:
        """Image Size to `size` x `size` px with one resampling method (resample_probe)."""
        self.ps.js(resample_probe.resize_js(size, method))

    def _selection_ops(self, ops: list[list[Any]]) -> None:
        """Run selection operations on the open test image (channel_probe)."""
        self.ps.js(tools.selection_ops_js(ops))

    def _blend_layer(self, top: str, mode: str, opacity: int) -> None:
        """Put test image `top` over the open one as a layer with blend `mode` (a blendMode
        string ID) and `opacity` per cent (layer_probe)."""
        source = self._test_image_file(top)
        self.ps.js(
            f"var base=app.activeDocument;app.open(new File({json.dumps(source.as_posix())}));var t=app.activeDocument;"
            "t.activeLayer.duplicate(base,ElementPlacement.PLACEATBEGINNING);t.close(SaveOptions.DONOTSAVECHANGES);"
            "app.activeDocument=base;base.activeLayer=base.layers[0];"
            "var d=new ActionDescriptor(),r=new ActionReference();"
            "r.putEnumerated(charIDToTypeID('Lyr '),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));d.putReference(charIDToTypeID('null'),r);"
            f"var l=new ActionDescriptor();l.putEnumerated(stringIDToTypeID('mode'),stringIDToTypeID('blendMode'),stringIDToTypeID({json.dumps(mode)}));"
            f"l.putUnitDouble(stringIDToTypeID('opacity'),charIDToTypeID('#Prc'),{int(opacity)});"
            "d.putObject(charIDToTypeID('T   '),charIDToTypeID('Lyr '),l);executeAction(charIDToTypeID('setd'),d,DialogModes.NO);"
            "var g=new ActionReference();g.putEnumerated(charIDToTypeID('Lyr '),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));"
            "var got=executeActionGet(g);'{\"mode\":'+q(typeIDToStringID(got.getEnumerationValue(stringIDToTypeID('mode'))))"
            "+',\"opacity\":'+Math.round(got.getUnitDoubleValue(stringIDToTypeID('opacity'))/255*100)+'}';"
        )
        self.blend = {"mode": mode, "opacity": opacity, "kind": "grey" if "grey" in top else "colour"}

    def _retouch_dab(self, tool: str, options: dict[str, Any], points: list[list[int]]) -> None:
        """Set Dodge, Burn or Sponge (retouch_probe) and stroke it through `points`."""
        self.retouch = self._drive(lambda: tools.set_retouch_options(_OWN_APARTMENT, tool, **options))
        self._drive(lambda: tools.stroke(_OWN_APARTMENT, tool, [tuple(p) for p in points]))

    def _smudge_stroke(self, options: dict[str, Any], points: list[list[int]]) -> None:
        """Set the Smudge tool (smudge_probe: a hard round tip, strength, spacing, Finger Painting;
        paint dynamics, which tie strength to pen pressure, off) and stroke it through `points`."""
        brush = {"_obj": "computedBrush", "diameter": {"_unit": "pixelsUnit", "_value": float(options["size_px"])},
                 "hardness": {"_unit": "percentUnit", "_value": 100.0}, "angle": {"_unit": "angleUnit", "_value": 0.0},
                 "roundness": {"_unit": "percentUnit", "_value": 100.0},
                 "spacing": {"_unit": "percentUnit", "_value": float(options["spacing"])}}
        values = {"brush": brush, "pressure": int(options["strength"]), "SmdF": bool(options["finger_painting"]),
                  "mode": {"_enum": "blendMode", "_value": "normal"}, "usePaintDynamics": False, "useTipDynamics": False,
                  "useScatter": False, "smoothing": False}
        if "foreground" in options:  # Finger Painting starts with it; save_tool_state kept the person's colours
            tools.set_colours(self.ps, foreground=[options["foreground"]] * 3)
        read = self._drive(lambda: tools.set_tool_options(_OWN_APARTMENT, "smudge", values))
        self.smudge = {"options": options, "read_back": {"strength": read.get("pressure"), "finger_painting": read.get("SmdF"),
                                                         "spacing": read["brush"]["spacing"]["_value"],
                                                         "size_px": read["brush"]["diameter"]["_value"],
                                                         "paint_dynamics": read.get("usePaintDynamics")}}
        self._drive(lambda: tools.stroke(_OWN_APARTMENT, "smudge", [tuple(p) for p in points]))

    def _spot_heal(self, options: dict[str, Any], points: list[list[int]]) -> None:
        """Set the Spot Healing Brush (heal_probe: a hard round tip, one type) and stroke it through
        `points` by the stroke-path event naming the tool."""
        brush = {"_obj": "computedBrush", "diameter": {"_unit": "pixelsUnit", "_value": float(options["size_px"])},
                 "hardness": {"_unit": "percentUnit", "_value": 100.0}, "angle": {"_unit": "angleUnit", "_value": 0.0},
                 "roundness": {"_unit": "percentUnit", "_value": 100.0}, "spacing": {"_unit": "percentUnit", "_value": 25.0}}
        values = {"brush": brush, "SmmS": {"_enum": "SmmT", "_value": options["type"]}, "useTipDynamics": False,
                  "usePaintDynamics": False, "opacity": 100, "mode": {"_enum": "blendMode", "_value": "normal"}}
        read = self._drive(lambda: tools.set_tool_options(_OWN_APARTMENT, "spot_healing", values))
        self.heal = {"options": options, "read_back": {"type": read["SmmS"]["_value"], "size_px": read["brush"]["diameter"]["_value"]}}
        self._drive(lambda: tools.stroke_with(_OWN_APARTMENT, "spot_healing", [tuple(p) for p in points]))

    def _define_own_pattern(self) -> None:
        """Draw the harness's own pattern (tipmix_probe.pattern_image) on a throwaway canvas and
        define it as a pattern; one left by an interrupted spec is deleted first. The pattern list
        must gain exactly that one name."""
        self._delete_own_pattern()
        before = self._preset_names("pattern")
        size = tipmix_probe.PATTERN
        greys = json.dumps([tipmix_probe.pattern_grey(x) for x in range(size)])
        self.ps.js(
            f"app.documents.add(UnitValue({size},'px'),UnitValue({size},'px'),72,{json.dumps(photoshop.THROWAWAY_PREFIX + 'pattern')},"
            "NewDocumentMode.RGB,DocumentFill.WHITE);var d=app.activeDocument,g=" + greys + ";"
            f"for(var x=0;x<g.length;x++){{d.selection.select([[x,0],[x+1,0],[x+1,{size}],[x,{size}]]);var c=new SolidColor();"
            "c.rgb.red=g[x];c.rgb.green=g[x];c.rgb.blue=g[x];d.selection.fill(c);}d.selection.deselect();"
            "var a=new ActionDescriptor(),r=new ActionReference();r.putClass(charIDToTypeID('Ptrn'));a.putReference(charIDToTypeID('null'),r);"
            "var u=new ActionReference();u.putProperty(charIDToTypeID('Prpr'),charIDToTypeID('fsel'));"
            "u.putEnumerated(charIDToTypeID('Dcmn'),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));a.putReference(charIDToTypeID('Usng'),u);"
            f"a.putString(charIDToTypeID('Nm  '),{json.dumps(tipmix_probe.OWN_PATTERN_NAME)});executeAction(charIDToTypeID('Mk  '),a,DialogModes.NO);"
            "d.close(SaveOptions.DONOTSAVECHANGES);\"null\";")
        after = self._preset_names("pattern")
        if after[:len(before)] != before or after[len(before):] != [tipmix_probe.OWN_PATTERN_NAME]:
            raise RuntimeError("defining the own pattern did not add exactly that one pattern")

    def _delete_own_pattern(self) -> None:
        """Delete every pattern named tipmix_probe.OWN_PATTERN_NAME, by name, one at a time, each
        checked in the pattern list to have removed that one and nothing else."""
        name = tipmix_probe.OWN_PATTERN_NAME
        for _ in range(10):
            before = self._preset_names("pattern")
            if name not in before:
                return
            self.ps.js("var d=new ActionDescriptor(),r=new ActionReference();"
                       f"r.putName(charIDToTypeID('Ptrn'),{json.dumps(name)});"
                       "d.putReference(charIDToTypeID('null'),r);executeAction(charIDToTypeID('Dlt '),d,DialogModes.NO);\"null\";")
            after = self._preset_names("pattern")
            gone = [n for n in set(before) if before.count(n) != after.count(n)]
            if gone != [name] or len(after) != len(before) - 1:
                raise RuntimeError(f"deleting the own pattern removed {gone}; stopped")
        raise RuntimeError("own patterns still present after 10 deletions")

    def _tipmix_stroke(self, options: dict[str, Any], extra: dict[str, Any], points: list[list[int]]) -> None:
        """Set the brush (tipmix_probe: a hard round tip), put `extra` (Texture or Dual Brush
        settings) over its options and stroke it."""
        self._drive(lambda: tools.set_brush_options(_OWN_APARTMENT, "brush", **options))
        read = self._drive(lambda: tools.set_tool_options(_OWN_APARTMENT, "brush", extra)) if extra else {}
        dual = read.get("dualBrush") or {}
        self.tipmix = {"options": options, "read_back": {
            "texture": read.get("useTexture"), "texture_mode": (read.get("textureBlendMode") or {}).get("_value"),
            "texture_depth": (read.get("textureDepth") or {}).get("_value"), "invert": read.get("invertTexture"),
            "dual": dual.get("useDualBrush"), "dual_mode": (dual.get("blendMode") or {}).get("_value"),
            "dual_size": ((dual.get("brush") or {}).get("diameter") or {}).get("_value"),
            "dual_spacing": ((dual.get("brush") or {}).get("spacing") or {}).get("_value")}}
        self._drive(lambda: tools.stroke(_OWN_APARTMENT, "brush", [tuple(p) for p in points]))

    def _delete_own_tip(self) -> None:
        """Delete every brush preset named brush_probe.OWN_TIP_NAME, by name, one at a time, each
        checked to have removed that one preset and nothing else."""
        for _ in range(10):
            before = self._preset_names("brush")
            if brush_probe.OWN_TIP_NAME not in before:
                return
            self.ps.js("var d=new ActionDescriptor(),r=new ActionReference();"
                       f"r.putName(charIDToTypeID('Brsh'),{json.dumps(brush_probe.OWN_TIP_NAME)});"
                       "d.putReference(charIDToTypeID('null'),r);executeAction(charIDToTypeID('Dlt '),d,DialogModes.NO);\"null\";")
            after = self._preset_names("brush")
            gone = [n for n in set(before) if before.count(n) != after.count(n)]
            if gone != [brush_probe.OWN_TIP_NAME] or len(after) != len(before) - 1:
                raise RuntimeError(f"deleting the own tip removed {gone}; stopped")
        raise RuntimeError("own tip presets still present after 10 deletions")

    def _define_own_tip(self, tip: str = "blocks") -> None:
        """Draw the harness's own tip (brush_probe.OWN_TIPS[tip]) on a throwaway canvas and define it as
        a brush preset, which Photoshop also selects; the canvas closes and the brush canvas is
        active again. A tip left by an interrupted spec is deleted first; delete_own_tip (a
        clean-up step) removes this one by name."""
        self._delete_own_tip()
        width, height = brush_probe.OWN_TIP_CANVAS
        boxes = json.dumps([list(b) for b in brush_probe.OWN_TIPS[tip]])
        self.ps.js(
            f"var back=app.activeDocument;app.documents.add(UnitValue({width},'px'),UnitValue({height},'px'),72,"
            f"{json.dumps(photoshop.THROWAWAY_PREFIX + 'tip')},NewDocumentMode.RGB,DocumentFill.WHITE);"
            # One fill per run of boxes of one grey (their union selected first): 54 separate
            # fills left Photoshop hung right after (2026-11-25).
            f"var doc=app.activeDocument,bx={boxes};function fill(g){{var c=new SolidColor();"
            "c.rgb.red=g;c.rgb.green=g;c.rgb.blue=g;doc.selection.fill(c);}"
            "for(var i=0;i<bx.length;i++){var b=bx[i],first=i==0||bx[i-1][4]!=b[4];"
            "doc.selection.select([[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]],first?SelectionType.REPLACE:SelectionType.EXTEND);"
            "if(i==bx.length-1||bx[i+1][4]!=b[4])fill(b[4]);}doc.selection.selectAll();"
            "var d=new ActionDescriptor(),r=new ActionReference();r.putClass(charIDToTypeID('Brsh'));"
            "d.putReference(charIDToTypeID('null'),r);var u=new ActionReference();"
            "u.putProperty(charIDToTypeID('Prpr'),charIDToTypeID('fsel'));"
            "u.putEnumerated(charIDToTypeID('Dcmn'),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));"
            f"d.putReference(charIDToTypeID('Usng'),u);d.putString(charIDToTypeID('Nm  '),{json.dumps(brush_probe.OWN_TIP_NAME)});"
            "executeAction(charIDToTypeID('Mk  '),d,DialogModes.NO);doc.close(SaveOptions.DONOTSAVECHANGES);"
            "app.activeDocument=back;\"null\";"
        )

    # Selection probe (selection_probe) ----------------------------------------------------------
    def _wand_click(self, x: int, y: int, tolerance: int, anti_alias: bool, contiguous: bool) -> None:
        self._drive(lambda: tools.wand_select(_OWN_APARTMENT, x, y, tolerance=tolerance, anti_alias=anti_alias,
                                              contiguous=contiguous))

    def _bucket_click(self, x: int, y: int, tolerance: int, anti_alias: bool, contiguous: bool) -> None:
        """Fill red from pixel (x, y) by the bucket's own event (save_tool_state keeps the
        person's colours and bucket options to be written back)."""
        tools.set_colours(self.ps, foreground=(255, 0, 0))
        options = self._drive(lambda: tools.set_bucket_options(
            _OWN_APARTMENT, tolerance=tolerance, anti_alias=anti_alias, contiguous=contiguous, all_layers=False))
        self._drive(lambda: tools.bucket_fill(_OWN_APARTMENT, x, y, options))

    def _feather_rect(self, box: list[int], radius: float) -> None:
        left, top, right, bottom = box
        self.ps.js(f"var d=app.activeDocument;d.selection.select([[{left},{top}],[{right},{top}],[{right},{bottom}],"
                   f'[{left},{bottom}]]);d.selection.feather({radius});"null";')

    def _save_tool_state(self, tool: str) -> None:
        self.saved_tools = self._drive(lambda: tools.snapshot_tool_state(_OWN_APARTMENT, [tool]))

    def _restore_tool_state(self) -> None:
        saved, self.saved_tools = self.saved_tools, None
        if saved is None:
            return
        restored = self._drive(lambda: tools.restore_tool_state(_OWN_APARTMENT, saved))
        if not tools.all_restored(restored):
            raise RuntimeError(f"tool options or colours did not read back as they were: {restored}")

    def _select_all(self) -> None:
        self.ps.js('app.activeDocument.selection.selectAll();"null";')

    def _run_recipe(self, name: str) -> None:
        """Do a dialog's work by script (RECIPES) in `sandbox/recipes/<name>`: the chart as its
        input, an emptied `out/`; dialogs it opens are answered meanwhile, as for menu commands."""
        self.recipe = name
        folder = self.sandbox / "recipes" / name
        source, out = folder / "in", folder / "out"
        source.mkdir(parents=True, exist_ok=True)
        test_images.chart().save(source / f"{photoshop.THROWAWAY_PREFIX}chart.png")
        out.mkdir(parents=True, exist_ok=True)
        for stale in out.iterdir():
            if stale.is_file():
                stale.unlink()
        script = recipe_script(name, folder)
        self._drive(lambda: _js_in_own_apartment(script))

    def _answer_file_dialogs(self, mode: str, name: str) -> None:
        """The next file dialog of this spec is answered with a sandbox file: an input made
        now, or an output name cleared first (so no Replace? prompt asks)."""
        folder = self.sandbox / "work"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{photoshop.THROWAWAY_PREFIX}{name}"
        if mode == "input" and not path.exists():
            make_input(name, path)
        elif mode == "output":
            path.unlink(missing_ok=True)
        self.file_answer = path

    def _count_presets(self, kind: str) -> None:
        """How many presets of `kind` there are before a Define dialog adds one, and their names."""
        self.presets_before = int(self.ps.js(_PRESETS_JS % _PRESET_CLASS[kind] + "String(n);"))
        self.preset_names_before = self._preset_names(kind)

    def _preset_names(self, kind: str) -> list[str]:
        return self.ps.js(_PRESETS_JS % _PRESET_CLASS[kind] + (
            "var L=null;for(var k=0;k<m.count;k++)if(m.getObjectType(k)==cls)L=m.getObjectValue(k).getList(charIDToTypeID('Nm  '));"
            "var a=[];for(var i=0;i<L.count;i++)a.push(q(L.getString(i)));'['+a.join(',')+']';"))

    def _delete_added_presets(self, kind: str) -> None:
        """Delete the presets of `kind` added since they were counted, newest first; the
        person's own (the first `presets_before`) are never touched."""
        if self.presets_before is None:
            return
        # Deleting by index removed other presets after Photoshop restarted (2026-11-25): delete
        # only while the first presets_before are still the ones counted.
        if self._preset_names(kind)[: self.presets_before] != getattr(self, "preset_names_before", None):
            raise RuntimeError(f"the {kind} presets changed since they were counted; none deleted")
        self.ps.js(_PRESETS_JS % _PRESET_CLASS[kind] + (
            f"for(var i=n;i>{self.presets_before};i--){{var d=new ActionDescriptor(),r=new ActionReference();"
            "r.putIndex(cls,i);d.putReference(charIDToTypeID('null'),r);"
            "executeAction(charIDToTypeID('Dlt '),d,DialogModes.NO);}\"null\";"
        ))

    def _build_state(self, name: str) -> None:
        """Build one document state (document_states) on the chart just opened."""
        self.ps.js(STATES[name])

    def _test_image_file(self, name: str) -> Path:
        """A harness test image written to the sandbox under the harness's own prefix (so it
        counts as scratch work), made once."""
        source = self.sandbox / f"{photoshop.THROWAWAY_PREFIX}{name}.png"
        if not source.exists():
            self.sandbox.mkdir(parents=True, exist_ok=True)
            images = {"chart": test_images.chart, "icon": test_images.icon, **retouch_probe.images(),
                      "selection": lambda: Image.fromarray(selection_probe.selection_image()), **layer_probe.images(),
                      **lasso_probe.images(), **resample_probe.images(), **channel_probe.images(),
                      **smudge_probe.images(), **heal_probe.images()}
            images[name]().save(source)
        return source

    def _open_test_image(self, name: str) -> None:
        """Open a harness test image and read its pixels as Photoshop renders them."""
        source = self._test_image_file(name)
        self.ps.js(f'app.open(new File({json.dumps(source.as_posix())}));"null";')
        self.test_image = name
        self.pixels_before = self._export_pixels("before")

    def _export_pixels(self, label: str) -> np.ndarray:
        """The active document's visible pixels, through a PNG copy in the sandbox."""
        target = self.sandbox / "exports" / f"{label}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        script = _EXPORT_PNG % json.dumps(target.as_posix())
        # Dialogs answered meanwhile: a save Photoshop could not make silently opened a Save a
        # Copy, and a bare call waited on it (CMYK, 2026-11-24).
        self._drive(lambda: _js_in_own_apartment(script))
        with Image.open(target) as image:
            return np.asarray(image.convert("RGBA"))

    # Acting --------------------------------------------------------------------------------
    def _run_menu_command(self, command: int, dialogs: str = "cancel") -> None:
        """Run a menu command; its dialogs are cancelled, or with "accept" answered OK with
        their default settings (so the effect can be measured), or with "plane" a perspective
        plane is clicked in the workspace first (Vanishing Point's OK waits for one)."""
        self.accept_dialogs = dialogs in ("accept", "plane")
        self.dialog_task = "plane" if dialogs == "plane" else None
        if self.accept_dialogs and self.ps.open_documents():
            self.view = canvas.read_view(self.ps, self.identity)  # for an on-canvas mode's commit
        try:
            self._run_menu_command_once(command)
        finally:
            self.accept_dialogs, self.dialog_task, self.view = False, None, None

    def _drive_dialog_controls(self, command: int, path: str, where: str = "") -> None:
        """Run a menu command and drive every control of the dialog it opens (control_pass)
        before it is cancelled: keyboard controls found by Tab, the rest placed by the
        catalogue's labels. Rows go to control-actions.jsonl."""
        self.dialog_path, self.expected = path, self.catalogue(path)
        self.dialog_task = "controls"
        try:
            # The command returns only when its dialog closes: after every control is driven
            # (Levels took over 90 s, Place Linked over 30 min on 2026-11-10).
            self._run_menu_command_once(command, timeout_s=10800)
        finally:
            self.dialog_task = None

    def _drive_controls(self, dialog: photoshop.Dialog) -> dict[str, Any]:
        if self.should_stop():  # never take the foreground from the person
            raise Interrupted("the person is back")
        time.sleep(1.5)  # previews finish drawing
        if self.ocr is None:
            self.ocr = Ocr()
        surface = DialogSurface(dialog.hwnd, self.identity.pid, self.ocr, self.should_stop)
        try:
            if surface.is_file_dialog():
                # Windows' folder browser, not Photoshop: walking it mapped nothing, wandered to
                # C:\ and pressed Place (2026-11-24). The work pass picks the sandbox file and
                # presses Place or Save, which is the code worth following.
                rows = [{"dialog": self.dialog_path, "kind": "file_dialog", "source": "file dialog",
                         "skipped": "a Windows file dialog: left to the work pass"}]
            else:
                rows = drive_dialog(surface, self.expected, self.dialog_path)
        except Interrupted as stopped:
            self._record_control_rows(getattr(stopped, "rows", []))  # what was driven, and where it stopped
            raise
        self._record_control_rows(rows)
        return controls_summary(rows)

    def _record_control_rows(self, rows: list[dict[str, Any]]) -> None:
        at = time.strftime("%Y-%m-%dT%H:%M:%S")
        # Full rows (with the text read) stay beside the captures; the dataset gets no Adobe text.
        published = functools.partial(publishable, known=self.known_labels)
        for path, shape in ((self.captures.parent / "control-actions-full.jsonl", dict), (self.control_actions, published)):
            if path is None:
                continue
            with path.open("a", encoding="utf-8", newline="\n") as out:
                for row in rows:
                    stamp = {"item_id": self.item_id, "at": at, "parity": self.parity}  # REA link
                    out.write(json.dumps({**stamp, **shape(row)}) + "\n")

    def _run_menu_command_once(self, command: int, timeout_s: float = 90) -> None:
        self._drive(lambda: self.bridge.call("menu_command", {"command": command}, timeout_s=timeout_s))

    def _read_event_settings(self, event: str) -> None:
        """Run a command by its scripting event with its dialog shown, accept the dialog at
        defaults, and keep the settings Photoshop returns (built-ins have no plug-in file)."""
        self.accept_dialogs = True
        try:
            answer = self._drive(lambda: _js_in_own_apartment(event_script(event)))
        finally:
            self.accept_dialogs = False
        descriptor = answer.get("descriptor")
        self.event_settings = {
            "event": event,
            "settings": settings_of(descriptor) if descriptor else [],
            "error": answer.get("error") or None,
        }

    def _sweep_event(
        self, event: str, settings: list[dict[str, Any]], overrides: dict[str, Any]
    ) -> None:
        """Replay a command by script with no dialog: its recorded defaults, `overrides`
        changed. Photoshop's answer is the observation: the settings it says it used (a value
        it clamped shows there) or its message when it declined the value."""
        answer = self._drive(lambda: _js_in_own_apartment(replay_script(event, settings, overrides)))
        descriptor = answer.get("descriptor")
        self.sweep = {
            "event": event,
            "overrides": overrides,
            "used": settings_of(descriptor) if descriptor else None,
            "error": answer.get("error") or None,
        }

    def _drive(self, action: Callable[[], Any]) -> Any:
        """Run `action` in a worker thread while capturing and answering its dialogs, and
        leaving any on-canvas mode with Escape; return its value or raise its error."""
        outcome: dict[str, Any] = {}

        def call() -> None:
            try:
                outcome["value"] = action()
            except Exception as error:  # noqa: BLE001 - reported below
                outcome["error"] = error

        worker = threading.Thread(target=call, daemon=True)
        worker.start()
        started, escapes, last_dialog_at = time.monotonic(), 0, None
        hung_since: float | None = None
        while worker.is_alive():
            # Never message a hung window: capture and clicks would wait on it forever
            # (Fibers froze Photoshop on 2026-11-09 and took the harness with it).
            if _photoshop_hung(self.identity.pid):
                hung_since = hung_since or time.monotonic()
                if hung_too_long(hung_since, time.monotonic()):
                    raise TimeoutError("Photoshop stopped responding: its window hung for 60 s")
                worker.join(1.0)
                continue
            hung_since = None
            if self._capture_and_cancel_dialogs():
                last_dialog_at = time.monotonic()
            worker.join(0.3)
            waited = quiet_seconds(time.monotonic(), started, last_dialog_at)
            dialog_up = bool(photoshop.blocking(photoshop.list_dialogs(self.identity.pid)))
            due = escape_due(
                waited, escapes, person_is_back=self.should_stop(), dialog_showing=dialog_up
            )
            if worker.is_alive() and due:
                self._escape_modal_mode(leave_mode(accepting=self.accept_dialogs, escapes=escapes))
                escapes += 1
        if "error" in outcome:
            error = outcome["error"]
            if refusal := photoshop_refusal(str(error)):
                raise Refused(refusal) from error
            raise error
        time.sleep(0.3)
        self._capture_and_cancel_dialogs()
        return outcome.get("value")

    def _escape_modal_mode(self, how: str = "escape") -> None:
        """Leave an on-canvas editing mode (Perspective Warp, Free Transform...) with Escape,
        or with "commit" do its work: a drag on the chart, then Enter.

        Those modes open no window, so no dialog check sees them, yet Photoshop refuses
        scripting until they end (so the chart's place on screen was read before the command
        ran). The canvas is captured first: the mode is the observation.
        """
        commit = how == "commit" and self.view is not None
        path = self._capture_path("still-running")
        record = dialog_record(
            f"still running after 8 s, no dialog ({'drag and Enter' if commit else 'Escape'} pressed)",
            path.name,
            functools.partial(capture.capture_window, self.identity.hwnd, path),
        )
        self.dialogs_seen.append(record)
        if self.should_stop():  # never take the foreground from the person
            raise Interrupted("the person is back")
        # focus, not a bare SetForegroundWindow: Windows refuses that from a background program,
        # and after a force-quit Chrome kept the foreground through every Escape (2026-11-24).
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        if commit:
            view = self.view
            events = [*gesture_events("drag", lambda x, y: canvas.document_to_screen(view, x, y)), *chord("enter")]
        else:
            events = chord("escape")
        win_input.perform(events, pid=self.identity.pid, should_stop=self.should_stop)

    def _capture_path(self, label: str) -> Path:
        return (
            self.captures / f"{self.item_id.replace(':', '_')}-{label}-{len(self.dialogs_seen)}.png"
        )

    def _press(self, keys: str) -> None:
        if win_input.owned_elsewhere(keys.lower()):
            # Another program would act instead (Alt+F9: NVIDIA offered to record the desktop).
            raise Refused(f"another program on this machine owns {keys}; not pressed")
        self.ps.bring_to_front()
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        win_input.perform(chord(keys.lower()), pid=self.identity.pid, should_stop=self.should_stop)
        pressed = last_dialog_at = time.monotonic()
        while keep_watching(time.monotonic() - pressed, time.monotonic() - last_dialog_at):
            if self.should_stop():
                raise Interrupted("the person is back")
            if self._capture_and_cancel_dialogs():
                last_dialog_at = time.monotonic()
            time.sleep(0.5)

    def _use_tool(self, kind: str, commit: str) -> None:
        """Use the selected tool on the chart (tool_gestures): the gesture is planned in chart
        pixels and sent where Photoshop shows them now, then committed if the tool waits for it;
        any dialog it opens is captured and cancelled as after a key press."""
        view = canvas.read_view(self.ps, self.identity)
        events = gesture_events(kind, lambda x, y: canvas.document_to_screen(view, x, y))
        self.ps.bring_to_front()
        win_input.focus(self.identity.hwnd, self.identity.pid, should_stop=self.should_stop)
        win_input.perform(events, pid=self.identity.pid, should_stop=self.should_stop)
        if commit:
            win_input.perform(chord(commit), pid=self.identity.pid, should_stop=self.should_stop)
        used = last_dialog_at = time.monotonic()
        while keep_watching(time.monotonic() - used, time.monotonic() - last_dialog_at):
            if self.should_stop():
                raise Interrupted("the person is back")
            if self._capture_and_cancel_dialogs():
                last_dialog_at = time.monotonic()
            time.sleep(0.5)

    def _read_flyouts(self) -> None:
        """Open and read every visible panel group's flyout menu (panel_flyouts), Photoshop
        in front, through the guarded input."""
        pid, hwnd = self.identity.pid, self.identity.hwnd
        self.ps.bring_to_front()
        win_input.focus(hwnd, pid, should_stop=self.should_stop)
        self.flyouts = read_flyouts(
            pid, hwnd,
            click=lambda point: win_input.perform(click(point), pid=pid, should_stop=self.should_stop),
            escape=lambda: win_input.perform(chord("escape"), pid=pid, should_stop=self.should_stop),
        )

    def _select_tool_by_script(self, tool_id: str) -> None:
        self.ps.js(_SELECT_TOOL % json.dumps(tool_id) + '"null";')

    def _capture_and_cancel_dialogs(self) -> int:
        """Capture then answer every blocking dialog (Cancel, or OK while a command's dialogs
        are being accepted); how many there were. A hung Photoshop is left alone: capturing
        or clicking its windows would wait on it forever (Fibers, 2026-11-09)."""
        if _photoshop_hung(self.identity.pid):
            return 0
        dialogs = photoshop.blocking(photoshop.list_dialogs(self.identity.pid))
        for dialog in dialogs:
            path = self._capture_path("dialog")
            record = dialog_record(
                dialog.class_name,
                path.name,
                functools.partial(capture.capture_window, dialog.hwnd, path),
            )
            self.dialogs_seen.append(record)
            if not ctypes.windll.user32.IsWindow(dialog.hwnd):
                continue  # already gone: nothing to answer
            if self.dialog_task == "plane" and self.workspace is None and _waiting_for_input(dialog):
                self.workspace = self._draw_plane(dialog)
                continue  # its OK is answered next round, once listed afresh
            if self.dialog_task == "controls" and self.controls is None:
                self.controls = self._drive_controls(dialog)
                continue  # cancelled next round, once listed afresh
            if self.accept_dialogs and self.file_answer and is_file_dialog(dialog.hwnd):
                path, self.file_answer = self.file_answer, None  # once: a second ask is cancelled
                answered = answer_file_dialog(dialog.hwnd, path)
                record["answer"] = f"sandbox file {path.name}" if answered else "sandbox file not taken"
                continue  # still open: cancelled next round
            action, control = (
                photoshop.accept_action(dialog, never_press=self.never_press)
                if self.accept_dialogs
                else photoshop.cancel_action(dialog)
            )
            if not may_cancel_now(action, person_is_back=self.should_stop()):
                continue  # clean-up after they leave again cancels it
            record["answer"] = control.text.replace("&", "") if control else action
            photoshop.answer(dialog, action, control)
            time.sleep(0.5)
        return len(dialogs)

    def _draw_plane(self, dialog: photoshop.Dialog) -> dict[str, Any]:
        """Find the test image in the workspace and click a perspective plane on it."""
        shot = np.asarray(capture.grab(dialog.hwnd).convert("RGB"))
        height, width = shot.shape[:2]
        found = locate(shot, search=(60, 130, width - 10, height - 40))  # past the toolbars
        if found is None:
            return {"found": False}
        placement = trim_frame(shot, found)
        image = test_images.chart() if self.test_image == "chart" else test_images.icon()
        match = likeness(shot, placement, image)
        observed: dict[str, Any] = {
            "found": match >= 0.8,
            "placement": [placement.left, placement.top, placement.width, placement.height],
            "likeness": round(match, 3),
        }
        if match < 0.8:  # not sure it is the image: click nothing
            return observed
        if self.should_stop():
            raise Interrupted("the person is back")
        left, top, _, _ = capture.frame_bounds(dialog.hwnd)
        ctypes.windll.user32.SetForegroundWindow(dialog.hwnd)
        clicks = plane_clicks(placement, image_size=image.size, window_origin=(left, top))
        win_input.perform(clicks, pid=self.identity.pid, should_stop=self.should_stop)
        time.sleep(1.0)
        return {**observed, "clicks": 4}

    def _cancel_dialogs(self) -> None:
        self._capture_and_cancel_dialogs()

    # Recording -----------------------------------------------------------------------------
    def _record(self, *kinds: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for kind in kinds:
            if kind == "dialogs":
                # The spec's own list, not a copy: a dialog answered during clean-up is added.
                out["dialogs"] = self.dialogs_seen
            elif kind == "history":
                open_count = len(self.ps.open_documents())
                states = self.ps.history()["states"] if open_count else None
                out["history"] = history_observation(open_count, states)
            elif kind == "document":
                out["document"] = self.ps.js(
                    "var d=app.documents.length?app.activeDocument:null;d?"
                    """'{"width":'+d.width.as("px")+',"height":'+d.height.as("px")"""
                    """+',"layers":'+d.layers.length+',"mode":'+q(String(d.mode))+'}':"null";"""
                )
            elif kind == "current_tool":
                out["current_tool"] = self.ps.current_tool()
            elif kind == "sandbox_files":
                out["sandbox_files"] = sorted(p.name for p in self.sandbox.glob("*"))
            elif kind == "recipe_files":  # what this spec's recipe wrote into its out/ folder
                outs = self.sandbox / "recipes" / (self.recipe or "") / "out"
                out["recipe_files"] = sorted(p.name for p in outs.glob("*") if p.is_file()) if self.recipe else []
            elif kind == "panels":
                out["panels"] = self._visible_panels()
            elif kind == "new_windows":
                out.update(window_observation(self.windows_before, _top_windows()))
            elif kind == "pixels":
                out["pixels"] = self._pixel_change()
            elif kind == "event_settings":
                out["event_settings"] = self.event_settings
            elif kind == "sweep":
                out["sweep"] = self.sweep
            elif kind == "selection":
                mask, _ = self._drive(lambda: px.export_selection_mask(_OWN_APARTMENT))
                out["selection"] = selection_probe.measure_selection(mask)
            elif kind == "bucket":
                after = self._export_pixels("after")
                out["bucket"] = selection_probe.measure_selection(
                    selection_probe.bucket_coverage(self.pixels_before, after))
            elif kind == "brush":
                alpha = self._drive(lambda: px.export_layer(_OWN_APARTMENT, _PAINT_LAYER))[..., 3]
                out["brush"] = {"options": self.brush["read_back"],
                                **brush_probe.measure(alpha, self.brush["points"], self.brush["size"])}
            elif kind == "pen":
                alpha = self._drive(lambda: px.export_layer(_OWN_APARTMENT, _PAINT_LAYER))[..., 3]
                out["pen"] = {"options": self.brush["read_back"], "column_centres": pen_probe.column_centres(alpha),
                              **brush_probe.measure(alpha, self.brush["points"], self.brush["size"])}
            elif kind == "effect":
                out["effect"] = effect_probe.measure(self._export_pixels("after"))
            elif kind == "curve":
                out["curve"] = retouch_probe.measure(self._export_pixels("after"))
            elif kind == "resample":
                out["resample"] = resample_probe.measure(self._export_pixels("after"))
            elif kind == "mask":
                count = self._drive(lambda: tools.selection_pixel_count(_OWN_APARTMENT))
                mask, _ = self._drive(lambda: px.export_selection_mask(_OWN_APARTMENT))
                out["mask"] = channel_probe.measure(mask, count)
            elif kind == "blend":
                out["blend"] = {**self.blend, **layer_probe.measure(self._export_pixels("after"), self.blend["kind"])}
            elif kind == "tipmix":
                alpha = self._drive(lambda: px.export_layer(_OWN_APARTMENT, _PAINT_LAYER))[..., 3]
                out["tipmix"] = {**self.tipmix, **tipmix_probe.measure(alpha)}
            elif kind == "heal":
                out["heal"] = {**self.heal, "before": heal_probe.patch(self.pixels_before),
                               "after": heal_probe.patch(self._export_pixels("after"))}
            elif kind == "smudge":
                out["smudge"] = {**self.smudge, **smudge_probe.measure(self._export_pixels("after"))}
            elif kind == "retouch":
                out["retouch"] = {"options": self.retouch, **retouch_probe.measure(self._export_pixels("after"))}
            elif kind == "workspace":
                out["workspace"] = self.workspace
            elif kind == "controls":
                out["controls"] = self.controls
            elif kind == "flyouts":
                out["flyouts"] = self.flyouts
            else:
                raise NotImplementedError(f"cannot record {kind!r} yet")
        return out

    def _pixel_change(self) -> dict[str, Any]:
        if self.pixels_before is None:
            return {"no_test_image": True}
        if not self.ps.open_documents():
            return {"no_document_open": True}
        regions = test_images.CHART_REGIONS if self.test_image == "chart" else None
        after = self._export_pixels("after")
        return {
            "image": self.test_image,
            **canvas_change(self.pixels_before, after, regions),
            # Exact result identity: equal across runs = deterministic; equal to the default's
            # result = this setting value made no difference on the chart.
            "after_sha256": pixels_sha256(after),
        }

    # Panels and windows ---------------------------------------------------------------------
    def _visible_panels(self) -> list[str]:
        return self.ps.js(
            'var r=new ActionReference();r.putProperty(stringIDToTypeID("property"),stringIDToTypeID("panelList"));'
            'r.putEnumerated(charIDToTypeID("capp"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));'
            'var l=executeActionGet(r).getList(stringIDToTypeID("panelList")),out=[];'
            "for(var i=0;i<l.count;i++){var p=l.getObjectValue(i);"
            'if(p.getBoolean(stringIDToTypeID("visible")))out.push(q(p.getString(stringIDToTypeID("ID"))));}'
            '"["+out.join(",")+"]";'
        )

    def _snapshot_panels(self) -> None:
        self.panels_before = set(self._visible_panels())

    def _show_panel(self, panel_id: str) -> None:
        if panel_id in self._visible_panels():
            return
        command = self._panel_command(panel_id)
        if command is None:
            raise NotImplementedError(f"no Window menu command shows {panel_id}")
        self._run_menu_command(command)

    def _restore_panels(self) -> None:
        if self.panels_before is None:  # no snapshot: hiding panels could hide the user's own
            return
        for panel_id in set(self._visible_panels()) - self.panels_before:
            if (command := self._panel_command(panel_id)) is not None:
                self._run_menu_command(command)  # a Window menu command toggles its panel

    def _panel_command(self, panel_id: str) -> int | None:
        path = panel_menu_path(panel_id, self.panel_names.get(panel_id, ""), set(self.menu_commands))
        return self.menu_commands.get(path) if path else None

    def _snapshot_windows(self) -> None:
        self.windows_before = {window.hwnd for window in _top_windows()}

    def _new_program_windows(self) -> list[TopWindow]:
        return new_adobe_windows(self.windows_before, _top_windows())

    def _wait_for_new_program_window(self, seconds: float) -> None:
        """Give a launched program (Bridge takes seconds) time to show, so it is recorded and
        closed; stops at once if the person comes back."""
        if wait_until(lambda: bool(self._new_program_windows()), seconds, self.should_stop):
            # Let its main window finish appearing, still giving way the moment they are back.
            wait_until(lambda: False, 2, self.should_stop)

    def _close_new_program_windows(self) -> None:
        """Close windows another Adobe program opened during this probe (Bridge, or Creative
        Cloud offering it). Exact windows by handle: nothing that was already open is touched."""
        for window in self._new_program_windows():
            ctypes.windll.user32.PostMessageW(window.hwnd, WM_CLOSE, 0, 0)

    # Workspaces and view toggles ------------------------------------------------------------
    def _current_workspace(self) -> int | None:
        checked = [m for m in self.ps.menu_items(self.workspace_commands) if m["checked"]]
        return checked[0]["command"] if checked else None

    def _snapshot_workspace(self) -> None:
        self.workspace_before = self._current_workspace()

    def _restore_workspace(self) -> None:
        if self.workspace_before is not None and self._current_workspace() != self.workspace_before:
            self._run_menu_command(self.workspace_before)

    def _toggle_back(self, command: int) -> None:
        self._run_menu_command(command)  # View commands are toggles: running again undoes them

    # Quitting and recovering ----------------------------------------------------------------
    def _wait_for_app_exit(self) -> None:
        if not _wait_for_exit(self.identity.pid, 120):
            raise TimeoutError("Photoshop did not exit within 2 minutes")

    def _relaunch_app(self) -> None:
        """Make sure Photoshop 2026 runs and answers both scripting and the helper."""
        if not _alive(self.identity.pid):
            subprocess.Popen([str(EXE)])  # Photoshop's own executable
        for _ in range(60):
            try:
                self._connect()
                require_photoshop(self.bridge.call("ping", {}, timeout_s=10), major="27")
                self.observe_process()  # a new process: results after this name its observation
                return
            except Exception as error:  # noqa: BLE001 - still starting
                print(f"waiting for Photoshop to answer: {type(error).__name__}")
                time.sleep(5)
        raise TimeoutError("Photoshop did not come back within 5 minutes")

    def relaunch_if_gone(self) -> None:
        """Start Photoshop again before a spec if it is gone (the watchdog ended it): otherwise
        the next specs fail on a dead Photoshop and use up the restarts (2026-11-24)."""
        if not _alive(self.identity.pid):
            print("Photoshop is gone; starting it again before the next spec")
            self._relaunch_app()

    def observe_process(self) -> None:
        """Take the parity observation of the Photoshop process the runner is connected to."""
        self.parity = self.observe_parity(self.identity)

    def safe_to_quit(self) -> bool:
        """Only scratch work was open at a reading taken after the person's last input."""
        return may_force_quit(
            self.documents_seen,
            reading_age_s=time.monotonic() - self.documents_seen_at,
            idle_s=self.idle_s(),
        )

    def restart(self) -> None:
        """Recover from a stuck or vanished Photoshop: ask it to quit, force it if it won't.

        Runs only between specs, and only if the last reading of open documents (taken before
        every spec) showed nothing but harness scratch work: otherwise it refuses, which ends
        the session, because closing without saving could lose the person's work.
        """
        if not self.safe_to_quit():
            raise RuntimeError(
                "will not restart Photoshop: a document of the person's may be open "
                f"(last seen: {len(self.documents_seen or [])} open)"
            )
        print("restarting Photoshop after repeated failures")
        if not _photoshop_hung(self.identity.pid):  # a hung one would never answer the script
            try:
                self._close_throwaway_document()
            except Exception:  # noqa: BLE001, S110 - a stuck Photoshop refuses scripts; quit anyway
                pass
        ctypes.windll.user32.PostMessageW(self.identity.hwnd, WM_CLOSE, 0, 0)
        if not _wait_for_exit(self.identity.pid, 30):
            subprocess.run(["taskkill", "/PID", str(self.identity.pid), "/F"], check=False)
            _wait_for_exit(self.identity.pid, 30)
        self._relaunch_app()


def _watchdog(adapter: PhotoshopAdapter, stop: threading.Event) -> None:
    """End a Photoshop frozen for two minutes (when only scratch work is open): a script call
    blocked on it then fails, and the session's normal restart follows. Checks every 5 s."""
    hung_since: float | None = None
    while not stop.wait(5.0):
        pid = adapter.identity.pid
        if not (_alive(pid) and _photoshop_hung(pid)):
            hung_since = None
            continue
        hung_since = hung_since or time.monotonic()
        if watchdog_should_kill(hung_since, time.monotonic(), safe_to_quit=adapter.safe_to_quit()):
            end_frozen_photoshop(pid, sys.stdout)
            hung_since = None


def install_session_guard(idle_s: Callable[[], float], threshold_s: float) -> None:
    """Every focus and key press the runner makes, its own or the dialog answerer's, stops once
    the person is back (real input within `threshold_s`), and only then may it take back a
    foreground another program took: the answerer had no guard (File Info, 2026-11-24)."""
    win_input.set_session_guard(lambda: idle_s() < threshold_s)


def dump_stacks_if_asked(request: Path, out: Any) -> bool:
    """Every thread's stack to `out` if `request` exists (then removed): where a stuck runner
    waits, read without stopping it (a Save a Copy sat unanswered 5 minutes, 2026-11-24)."""
    if not request.exists():
        return False
    request.unlink(missing_ok=True)
    _write_stacks(out)
    return True


def _write_stacks(out: Any) -> None:
    names = {thread.ident: thread.name for thread in threading.enumerate()}
    for ident, frame in sys._current_frames().items():
        out.write(f"--- stack of thread {names.get(ident, ident)} ---\n")
        chain = []
        while frame is not None:
            chain.append(frame)
            frame = frame.f_back
        for each in reversed(chain):
            out.write("".join(traceback.format_stack(each, limit=1)))
            if "control" in each.f_locals:  # which dialog control a frame was driving
                # ASCII only: an OCR label can hold any character, and the log is cp1252.
                out.write(f"    control: {ascii(each.f_locals['control'])}\n")
    out.flush()


def end_frozen_photoshop(pid: int, out: Any) -> None:
    """Force-quit a frozen Photoshop, every runner thread's stack written first: what the
    runner was doing when it froze (Place Linked, after its folder was fixed, 2026-11-24)."""
    print("watchdog: Photoshop frozen for 2 min; force-quitting it", file=out, flush=True)
    try:
        _write_stacks(out)
    finally:  # the quit happens however the record fares
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)


def _stack_requests(request: Path) -> None:
    while True:
        dump_stacks_if_asked(request, sys.stdout)
        time.sleep(2)


def _waiting_for_input(dialog: photoshop.Dialog) -> bool:
    """A workspace whose OK is greyed out until the person does something in it."""
    return any(
        c.class_name == "Button" and c.text.replace("&", "") == "OK" and not c.enabled
        for c in dialog.controls
    )


def _photoshop_hung(pid: int) -> bool:
    """Whether any visible window of Photoshop is hung; asks Windows, sends Photoshop nothing."""
    user32 = ctypes.windll.user32
    hung = False

    def visit(hwnd: int, _: int) -> bool:
        nonlocal hung
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd) and user32.IsHungAppWindow(hwnd):
            hung = True
        return True

    user32.EnumWindows(win_input.WNDENUMPROC(visit), 0)
    return hung


def _js_in_own_apartment(script: str) -> Any:
    """Run ExtendScript from a worker thread: COM objects belong to the thread that made them."""
    import pythoncom  # type: ignore[import-untyped]

    pythoncom.CoInitialize()
    try:
        return photoshop.Photoshop().js(script)
    finally:
        pythoncom.CoUninitialize()


class _OwnApartment:
    """A Photoshop for helpers that only call js(), usable from _drive's worker thread."""

    def js(self, body: str) -> Any:
        return _js_in_own_apartment(body)


_OWN_APARTMENT = _OwnApartment()
_PAINT_LAYER = "observed-truth-paint"


def _alive(pid: int) -> bool:
    return not _wait_for_exit(pid, 0)


def _wait_for_exit(pid: int, seconds: float) -> bool:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return True  # no such process
    try:
        return kernel32.WaitForSingleObject(handle, int(seconds * 1000)) == 0  # WAIT_OBJECT_0
    finally:
        kernel32.CloseHandle(handle)


def escape_due(
    waited_s: float, escapes: int, *, person_is_back: bool = False, dialog_showing: bool = False
) -> bool:
    """Whether a command still running is stuck in an on-canvas editing mode (Perspective Warp):
    after 8 s, then every 8 s more, at most 3 Escapes; never while the person is back or while
    a dialog is up (the dialog handling deals with that)."""
    if person_is_back or dialog_showing or escapes >= 3:
        return False
    return waited_s > 8.0 * (escapes + 1)


def leave_mode(*, accepting: bool, escapes: int) -> str:
    """How to end an on-canvas mode (Free Transform, the warps open no window): "commit" (a
    drag on the chart, then Enter: their OK) once when the command's work is wanted, else, or
    when a commit did not end it, "escape"."""
    return "commit" if accepting and escapes == 0 else "escape"


@dataclass(frozen=True)
class TopWindow:
    hwnd: int
    class_name: str
    program: str  # executable file name; titles are never read (they can name private files)


def new_adobe_windows(before: set[int] | None, now: list[TopWindow]) -> list[TopWindow]:
    """Windows that appeared since `before` and belong to another Adobe program; with no
    snapshot nothing counts as new, so nothing that was already open can be closed."""
    if before is None:
        return []
    return [
        window
        for window in now
        if window.hwnd not in before and window.program.startswith(_OTHER_ADOBE_PROGRAMS)
    ]


def window_observation(before: set[int] | None, now: list[TopWindow]) -> dict[str, Any]:
    """New windows: Adobe's and Photoshop's own are named (that is the learning); any other
    program's are only counted, since what else runs on the machine is private."""
    if before is None:
        return {"new_windows": [], "other_new_windows": 0, "no_snapshot": True}
    new = [w for w in now if w.hwnd not in before]
    named = [w for w in new if w.program.startswith((*_OTHER_ADOBE_PROGRAMS, "Photoshop"))]
    return {
        "new_windows": sorted(f"{w.class_name}|{w.program}" for w in named),
        "other_new_windows": len(new) - len(named),
    }


def may_force_quit(open_documents: list[str] | None, *, reading_age_s: float, idle_s: float) -> bool:
    """Only if the last reading saw nothing but harness scratch documents and was taken after
    the person last touched the machine (they could have opened their own file since);
    never read means the person's unsaved work could be open."""
    if open_documents is None or reading_age_s >= idle_s:
        return False
    return session_blocker(open_documents) is None


def hung_too_long(hung_since: float | None, now: float, limit_s: float = 60.0) -> bool:
    """Whether Photoshop's window has been hung (Windows: not answering messages) for so long
    that it froze; a busy filter rendering is hung only for a while."""
    return hung_since is not None and now - hung_since >= limit_s


def keep_watching(
    elapsed_s: float, quiet_s: float, *, settle_s: float = 8.0, limit_s: float = 30.0
) -> bool:
    """After a key press, whether to keep answering dialogs: until nothing new has appeared
    for `settle_s` (slow dialogs open seconds later), never past `limit_s`."""
    return elapsed_s < limit_s and (elapsed_s < settle_s or quiet_s < settle_s)


def watchdog_should_kill(hung_since: float | None, now: float, *, safe_to_quit: bool) -> bool:
    """End a Photoshop frozen for two minutes, so a script call blocked on it returns; never
    when the person's own work may be open."""
    return safe_to_quit and hung_too_long(hung_since, now, limit_s=120.0)


def may_cancel_now(action: str, *, person_is_back: bool) -> bool:
    """Escape takes the foreground and sends a key, so never once the person is back."""
    return not (action in ("escape", "enter") and person_is_back)


def quiet_seconds(now: float, started: float, last_dialog_at: float | None) -> float:
    """Time a command has run with no dialog: the Escape clock restarts after each dialog."""
    return now - (last_dialog_at if last_dialog_at is not None else started)


def away_after_s(*, now: bool, idle_minutes: float) -> float:
    """How long without real input before the person counts as away. An attended run (--now)
    starts after a few quiet seconds rather than minutes, but the person's own keyboard or mouse
    still stops it at once: it is their desktop (2026-11-11, typing in another app while the
    harness kept taking the foreground)."""
    return ATTENDED_QUIET_S if now else idle_minutes * 60



def wait_until(
    condition: Callable[[], bool],
    seconds: float,
    should_stop: Callable[[], bool],
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Poll `condition` once a second for up to `seconds`; stop at once if the person is back."""
    for _ in range(max(1, int(seconds))):
        if should_stop():
            raise Interrupted("the person is back")
        if condition():
            return True
        sleep(1.0)
    return False


def photoshop_refusal(error: str) -> str | None:
    """Photoshop's own "Could not complete..." message, when a command was declined; a
    "program error" is Photoshop failing, not declining, so it stays a failure."""
    if "program error" in error:
        return None
    marker = error.find("Could not complete")
    if marker >= 0:
        return error[marker:].strip().removesuffix(".").removesuffix(" ^0").strip()
    # Photoshop answered that it will not do this here (a tool scripting cannot pick): it is
    # not stuck, so this must never count toward a restart.
    if unavailable := _UNAVAILABLE.search(error):
        return f'The command "{unavailable.group(1)}" is not currently available'
    if _NOT_IN_THIS_VERSION in error:
        return _NOT_IN_THIS_VERSION
    return None


# Photoshop quotes the command straight or curly ("Select" or “Select”).
_UNAVAILABLE = re.compile('The command ["“]([^"”]+)["”] is not currently available')
_NOT_IN_THIS_VERSION = "This functionality may not be available in this version of Photoshop"


def history_observation(documents_open: int, states: list[dict[str, Any]] | None) -> dict[str, Any]:
    """History after a command; a command that closed the document (File > Close) is a result."""
    if documents_open == 0 or states is None:
        return {"count": 0, "last": [], "no_document_open": True}
    return {"count": len(states), "last": [s["name"] for s in states[-3:]]}


def dialog_record(class_name: str, image: str, capture_image: Callable[[], str]) -> dict[str, Any]:
    """What was seen of a dialog; one that closed by itself before capture is noted, not fatal."""
    try:
        return {"class": class_name, "image": image, "sha256": capture_image()}
    except OSError as error:
        return {"class": class_name, "image": None, "capture_error": str(error)}


def _program(pid: int) -> str:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return "?"
    image = ctypes.create_unicode_buffer(1024)
    size = ctypes.c_ulong(1024)
    kernel32.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size))
    kernel32.CloseHandle(handle)
    return Path(image.value).name


def _top_windows() -> list[TopWindow]:
    user32 = ctypes.windll.user32
    found: list[TopWindow] = []

    def visit(hwnd: int, _: int) -> bool:
        if user32.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append(TopWindow(hwnd, photoshop.class_name(hwnd), _program(pid.value)))
        return True

    user32.EnumWindows(win_input.WNDENUMPROC(visit), 0)
    return found


def _connected_adapter(
    bridge: Bridge, inventory: list[Any], sandbox: Path, captures: Path
) -> PhotoshopAdapter:
    # Never force-quit here: at startup the runner cannot tell whose Photoshop this is or
    # whether it holds unsaved work, and it has not yet checked that the person is away.
    for _ in range(60):
        try:
            require_photoshop(bridge.call("ping", {}, timeout_s=10), major="27")
            return PhotoshopAdapter(bridge, inventory, sandbox, captures)
        except Exception as error:  # noqa: BLE001 - still starting
            print(f"waiting for Photoshop and its helper: {type(error).__name__}")
            time.sleep(5)
    raise TimeoutError("Photoshop 2026 and its helper did not answer within 5 minutes")


def main() -> None:
    import argparse
    import functools

    from .idle import RealInputWatcher

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--sandbox", type=Path, default=CORPUS / "sandbox"
    )
    parser.add_argument(
        "--captures", type=Path, default=CORPUS / "captures"
    )
    parser.add_argument("--limit", type=int, help="run at most this many specs")
    parser.add_argument("--only", help="comma-separated item ids to run (default: all)")
    parser.add_argument("--now", action="store_true", help="attended: do not wait to be away")
    parser.add_argument("--retry-failed", action="store_true", help="run failed specs again")
    parser.add_argument(
        "--again", action="store_true", help="with --only: run those specs even if they passed"
    )
    parser.add_argument(
        "--specs",
        default="scenario-families.jsonl",
        help="spec file in the dataset (sweep-families.jsonl for the setting sweeps)",
    )
    parser.add_argument(
        "--idle-minutes", type=float, default=20, help="minutes without local input before running"
    )
    parser.add_argument(
        "--sample",
        type=Path,
        help="sweep folder: stack-sample Photoshop's interface thread throughout, time every spec and "
        "control (sampled_sweep), and keep this sweep's results and control actions there, so every "
        "spec runs again and the dataset's are left alone",
    )
    args = parser.parse_args()
    args.captures.mkdir(parents=True, exist_ok=True)

    inventory = load_inventory(args.dataset / "inventory.jsonl")
    with (args.dataset / args.specs).open(encoding="utf-8") as handle:
        specs = [
            ScenarioSpec(
                **{
                    **s,
                    "steps": tuple(map(tuple, s["steps"])),
                    "never_press": tuple(s["never_press"]),
                }
            )
            for s in map(json.loads, handle)
        ]
    results_path = (args.sample or args.dataset) / "results.jsonl"
    if args.sample:
        args.sample.mkdir(parents=True, exist_ok=True)
    lines = results_path.read_text(encoding="utf-8").splitlines() if results_path.exists() else []
    done = done_items(lines, retry_failed=args.retry_failed)
    queue = plan_queue(specs, done)
    if args.only:
        wanted = set(args.only.split(","))
        pool = [s for s in specs if s.safety == "run"] if args.again else queue
        queue = [s for s in pool if s.item_id in wanted]
    queue = queue[: args.limit] if args.limit else queue
    print(f"{len(queue)} specs queued ({len(done)} already done)")

    # Create this file to stop after the current probe (never mid-command).
    stop_file = args.captures.parent / "STOP-RUNNER"
    stop_file.unlink(missing_ok=True)
    win_input.make_dpi_aware()
    # ES_CONTINUOUS | ES_SYSTEM_REQUIRED: no sleeping while probes are queued.
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    watcher = RealInputWatcher().start()
    install_session_guard(watcher.idle_s, away_after_s(now=args.now, idle_minutes=args.idle_minutes))
    with Bridge(PLUGIN_PORT) as bridge:
        if not photoshop.main_window_pids():
            subprocess.Popen([str(EXE)])  # Photoshop's own executable
            time.sleep(30)
        adapter = _connected_adapter(bridge, inventory, args.sandbox, args.captures)
        adapter.idle_s = watcher.idle_s  # real input even with --now: attended runs never kill
        from .control_catalogue import load
        from .ocr_correct import STRINGS_FILE

        catalogue = load(args.dataset / "dialog-controls.jsonl")
        adapter.catalogue = catalogued(catalogue)
        strings = STRINGS_FILE.read_text(encoding="utf-8").splitlines() if STRINGS_FILE.exists() else []
        adapter.known_labels = known_labels(catalogue, strings)
        adapter.control_actions = (args.sample or args.dataset) / "control-actions.jsonl"
        # Observations carry a screenshot of Photoshop's window: kept beside the captures.
        adapter.observe_parity = functools.partial(
            parity.observe, observations=args.captures.parent / "parity-observations.jsonl"
        )
        adapter.observe_process()
        print(f"parity observation: {json.dumps(adapter.parity)[:300]}")
        threading.Thread(
            target=_watchdog, args=(adapter, threading.Event()), daemon=True
        ).start()
        # Touch STACKS-RUNNER beside STOP-RUNNER: every thread's stack goes to the log.
        threading.Thread(
            target=_stack_requests, args=(args.captures.parent / "STACKS-RUNNER",), daemon=True
        ).start()

        def run_one(spec: ScenarioSpec, should_stop: Any) -> RunResult:
            adapter.relaunch_if_gone()
            if any(_photoshop_hung(pid) for pid in photoshop.main_window_pids()):
                # Stuck, so it counts toward a restart; refusing "behind a dialog" would not.
                error = "TimeoutError: Photoshop is not responding (Windows reports it hung)"
                print(f"{'failed':12} {spec.item_id}  {error}")
                return RunResult(spec.item_id, "failed", error=error)
            for pid in photoshop.main_window_pids():
                preflight(
                    spec.item_id, functools.partial(photoshop.list_dialogs, pid), photoshop.click
                )
            adapter.begin(spec, should_stop)
            adapter.step("check_documents")
            result = execute(spec, adapter, should_stop)
            print(f"{result.status:12} {spec.item_id}  {result.error or ''}")
            return result

        def write(result: RunResult) -> None:
            with results_path.open("a", encoding="utf-8", newline="\n") as out:
                row = parity.result_row(
                    result, adapter.parity, at=time.strftime("%Y-%m-%dT%H:%M:%S")
                )
                out.write(json.dumps(row) + "\n")

        sweep = _sampled_sweep(args.sample, lambda: adapter.dialog_path) if args.sample else None
        if sweep is not None:
            plain = run_one

            def run_one(spec: ScenarioSpec, should_stop: Any) -> RunResult:
                with sweep.spec(spec.item_id, spec.family):
                    return plain(spec, should_stop)

        with timed(sweep.control_acted) if sweep is not None else contextlib.nullcontext():
            try:
                stopped = run_session(
                    queue,
                    run_one,
                    watcher.idle_s,
                    threshold_s=away_after_s(now=args.now, idle_minutes=args.idle_minutes),
                    sleep=time.sleep,
                    write=write,
                    recover=adapter.restart,
                    should_quit=stop_file.exists,
                    tidy=_cancel_left_open,
                )
            finally:
                if sweep is not None:
                    sweep.close()
        print(stopped or "queue finished")


def _cancel_left_open() -> None:
    """Cancel what an interrupted spec left open in Photoshop (Escape, Cancel or Close; never OK)."""
    for pid in photoshop.main_window_pids():
        for dialog in photoshop.blocking(photoshop.list_dialogs(pid)):
            print(f"closing what an interrupted spec left open: {dialog.class_name} {dialog.text!r}")
            photoshop.answer(dialog, *photoshop.cancel_action(dialog))
    time.sleep(1)


def _sampled_sweep(folder: Path, dialog_of: Any) -> Any:
    """A SampledSweep sampling Photoshop's interface thread, and its busiest other thread, in
    every decompiled Photoshop binary."""
    from .sampled_sweep import SampledSweep, watched_binaries
    from .stack_sampler import sample_process, ui_thread

    watch, indexes = watched_binaries(CORPUS, "photoshop")
    print(f"sampling {len(watch)} decompiled Photoshop binaries")

    def start(pid: int, stop: threading.Event, out: Path) -> None:
        for _ in range(120):  # a restarted Photoshop draws its window after a while
            if (tid := ui_thread(pid, "Photoshop")) is not None:
                stats = sample_process(pid, tid, watch, indexes, out, stop)
                print(f"sampler for pid {pid} stopped: {json.dumps(stats)}")
                return
            if stop.wait(1):
                return

    return SampledSweep(folder, start, pids=photoshop.main_window_pids, dialog_of=dialog_of)


if __name__ == "__main__":
    main()
