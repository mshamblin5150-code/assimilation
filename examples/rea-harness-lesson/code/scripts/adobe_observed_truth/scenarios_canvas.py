"""Canvas and view scenarios: the view readback and proof of the document-to-screen mapping."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import canvas, capture, win_input
from .input_plan import drag
from .photoshop import Identity, Photoshop
from .scenarios import Spec


WIDTH, HEIGHT = 400, 300
WHITE = (255, 255, 255)

_TOOLS = r"""
function appKey(n){var r=new ActionReference();r.putProperty(stringIDToTypeID("property"),stringIDToTypeID(n));
 r.putEnumerated(charIDToTypeID("capp"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));return executeActionGet(r);}
function toolId(){return typeIDToStringID(appKey("tool").getEnumerationType(stringIDToTypeID("tool")));}
function selectTool(id){var d=new ActionDescriptor(),r=new ActionReference();r.putClass(stringIDToTypeID(id));
 d.putReference(charIDToTypeID("null"),r);executeAction(charIDToTypeID("slct"),d,DialogModes.NO);}
"""


def view_state_readback(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    zooms = ["100", "50", "200", "66.67"]
    levels, artifacts = [], []
    ps.new_document("view-state", WIDTH, HEIGHT)
    try:
        states_before = len(ps.history()["states"])
        for percent in zooms:
            canvas.set_zoom(ps, float(percent))
            view = canvas.read_view(ps, identity)
            path = Path("captures") / f"view-state-{percent.replace('.', '_')}.png"
            # The view rectangle holds only this throwaway canvas and its pasteboard.
            image = capture.grab(identity.hwnd, view.view_bounds)
            sha256 = capture.save_png(image, out_dir / path)
            artifacts.append(path.as_posix())
            observed_edges = _white_canvas_edges(image, view)
            mapped_edges = _mapped_canvas_edges(view)
            levels.append(
                {
                    "requested_zoom_percent": percent,
                    "view": _view_record(view),
                    "canvas_edges_mapped": mapped_edges,
                    "canvas_edges_rendered": observed_edges,
                    "largest_edge_difference_px": max(
                        abs(observed_edges[key] - mapped_edges[key]) for key in mapped_edges
                    ),
                    "capture": {"path": path.as_posix(), "sha256": sha256},
                }
            )
        states_after = len(ps.history()["states"])
    finally:
        ps.close_throwaway_document()
    return {
        "operation": "observe_view_state",
        "parameters": {
            "behaviour_id": "canvas_view_state_readback",
            "document_px": [WIDTH, HEIGHT],
            "zoom_percent_set_by_script": zooms,
        },
        "observed": {
            "levels": levels,
            "history_states_before_zoom": states_before,
            "history_states_after_zoom": states_after,
        },
        "limitations": [
            "Zoom was set by script about the view centre, not by UI input.",
            "Rendered edges come from PrintWindow pixels: where Photoshop draws the canvas, "
            "not which document point a mouse event hits; canvas_mapping_check measures that.",
            "Rotation, screen modes other than the current one, and floating windows were not exercised.",
        ],
        "artifact_paths": sorted(artifacts),
    }


def canvas_mapping_check(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    target = {"left": 100, "top": 75, "right": 300, "bottom": 225}
    zooms = ["100", "200"]
    attempts = []
    ps.new_document("canvas-mapping", WIDTH, HEIGHT)
    try:
        previous_tool = ps.js(_TOOLS + "q(toolId());")
        ps.js(_TOOLS + 'selectTool("marqueeRectTool");"null";')
        try:
            options = _marquee_options(ps)
            ps.bring_to_front()
            win_input.focus(identity.hwnd, identity.pid)
            for percent in zooms:
                canvas.set_zoom(ps, float(percent))
                ps.js('app.activeDocument.selection.deselect();"null";')
                view = canvas.read_view(ps, identity)
                start = canvas.document_to_screen(view, target["left"], target["top"])
                end = canvas.document_to_screen(view, target["right"], target["bottom"])
                win_input.perform(drag(start, end, steps=12), pid=identity.pid)
                time.sleep(0.5)
                bounds = _selection_bounds(ps)
                attempts.append(
                    {
                        "zoom_percent": percent,
                        "view": _view_record(view),
                        "screen_start": list(start),
                        "screen_end": list(end),
                        "screen_points_as_document": [
                            _point_text(canvas.screen_to_document(view, *start)),
                            _point_text(canvas.screen_to_document(view, *end)),
                        ],
                        "selection_bounds": bounds,
                        "error_document_px": None
                        if bounds is None
                        else {key: bounds[key] - target[key] for key in target},
                    }
                )
            ps.js('app.activeDocument.selection.deselect();"null";')
        finally:
            ps.js(_TOOLS + f"selectTool({json.dumps(previous_tool)});\"null\";")
    finally:
        ps.close_throwaway_document()
    return {
        "operation": "observe_canvas_mapping",
        "parameters": {
            "behaviour_id": "canvas_document_to_screen_mapping",
            "document_px": [WIDTH, HEIGHT],
            "tool": "marqueeRectTool",
            "target_document_bounds": target,
            "zoom_percent_set_by_script": zooms,
            "drag_steps": 12,
        },
        "observed": {"marquee_options": options, "attempts": attempts},
        "limitations": [
            "Marquee style and feather are read, not set; a non-Normal style or a feather invalidates the error.",
            "Selection bounds are whole document pixels, so sub-pixel error is not observable.",
            "One monitor and one window layout; rotation and floating windows are not exercised.",
        ],
    }


def _view_record(view: canvas.View) -> dict[str, Any]:
    # Floats become strings: evidence parameters and observations hold no floats.
    return {
        "zoom": repr(view.zoom),
        "document_px": list(view.document_size),
        "view_bounds": list(view.view_bounds),
        "view_to_document": [repr(value) for value in view.view_to_document],
        "monitor_dpi": round(view.dpi_scale * 96),
        "rulers_visible": view.rulers_visible,
    }


def _mapped_canvas_edges(view: canvas.View) -> dict[str, int]:
    left, top = canvas.document_to_screen(view, 0, 0)
    right, bottom = canvas.document_to_screen(view, WIDTH, HEIGHT)
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def _white_canvas_edges(image: Any, view: canvas.View) -> dict[str, int]:
    """Screen edges of the white canvas along the row and column through its centre."""
    origin_x, origin_y = view.view_bounds[:2]
    centre_x, centre_y = canvas.document_to_screen(view, WIDTH / 2, HEIGHT / 2)
    row = [x for x in range(image.width) if image.getpixel((x, centre_y - origin_y)) == WHITE]
    column = [y for y in range(image.height) if image.getpixel((centre_x - origin_x, y)) == WHITE]
    if not row or not column:
        raise RuntimeError("No white canvas pixels through the canvas centre; the capture shows no canvas.")
    return {
        "left": origin_x + row[0],
        "top": origin_y + column[0],
        "right": origin_x + row[-1] + 1,
        "bottom": origin_y + column[-1] + 1,
    }


def _marquee_options(ps: Photoshop) -> dict[str, Any]:
    return ps.js(
        _TOOLS
        + 'var o=appKey("currentToolOptions").getObjectValue(stringIDToTypeID("currentToolOptions"));'
        '"{\\"style\\":"+o.getObjectValue(charIDToTypeID("MrqI")).getInteger(charIDToTypeID("MrqM"))'
        '+",\\"feather\\":"+q(o.getUnitDoubleValue(charIDToTypeID("MrqF"))+" px")'
        '+",\\"anti_alias\\":"+o.getBoolean(charIDToTypeID("MrqA"))'
        '+",\\"selection_mode\\":"+o.getInteger(stringIDToTypeID("selectionEnum"))+"}";'
    )


def _selection_bounds(ps: Photoshop) -> dict[str, int] | None:
    bounds = ps.js(
        'var b;try{b=app.activeDocument.selection.bounds;}catch(e){b=null;}'
        'b?"["+b[0].as("px")+","+b[1].as("px")+","+b[2].as("px")+","+b[3].as("px")+"]":"null";'
    )
    if bounds is None:
        return None
    return dict(zip(("left", "top", "right", "bottom"), (round(edge) for edge in bounds)))


def _point_text(point: tuple[float, float]) -> str:
    return f"{point[0]:.3f},{point[1]:.3f}"


SCENARIOS: dict[str, Spec] = {
    "view_state_readback": Spec(view_state_readback, needs_input=False),
    "canvas_mapping_check": Spec(canvas_mapping_check, needs_input=True),
}
