"""Behaviours that need real keyboard and mouse input; they run only on an unlocked workstation.

Every gesture is aimed through canvas.document_to_screen, so run canvas_mapping_check first.
Results are read back by script, never inferred from the input sent.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from . import win_input
from .canvas import document_to_screen, read_view
from .input_plan import chord, click, drag
from .photoshop import Identity, Photoshop
from .scenarios import Spec

SETTLE_S = 0.5


def _act(identity: Identity, plan) -> None:
    win_input.perform(plan, pid=identity.pid)
    time.sleep(SETTLE_S)


def _screen(ps: Photoshop, identity: Identity, x: int, y: int) -> tuple[int, int]:
    return document_to_screen(read_view(ps, identity), x, y)


MARQUEE_DRAG = ((100, 100), (300, 200))  # 200 x 100 document pixels: not square
EXISTING_SELECTION = [[400, 50], [550, 50], [550, 120], [400, 120]]
MARQUEE_CASES = [
    ("plain", False, (), "before_press"),
    ("shift_before_press_no_selection", False, ("shift",), "before_press"),
    ("shift_mid_drag_no_selection", False, ("shift",), "mid_drag"),
    ("shift_before_press_with_selection", True, ("shift",), "before_press"),
    ("shift_mid_drag_with_selection", True, ("shift",), "mid_drag"),
]


def marquee_shift_timing(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    original_tool = ps.current_tool()
    ps.new_document("marquee-shift-timing", 600, 400)
    results = []
    try:
        ps.select_tool("marqueeRectTool")
        win_input.focus(identity.hwnd, identity.pid)
        for name, existing, hold, hold_from in MARQUEE_CASES:
            ps.js("app.activeDocument.selection.deselect();\"null\";")
            if existing:
                ps.js(f"app.activeDocument.selection.select({EXISTING_SELECTION});\"null\";")
            start, end = (_screen(ps, identity, *point) for point in MARQUEE_DRAG)
            _act(identity, drag(start, end, steps=8, hold=hold, hold_from=hold_from))
            results.append({"case": name, "selection_bounds": ps.selection_bounds()})
    finally:
        ps.close_throwaway_document()
        ps.select_tool(original_tool)
    return {
        "operation": "observe_marquee_shift_timing",
        "parameters": {
            "behaviour_id": "selection_marquee_shift_before_vs_after_drag_start",
            "drag_document_px": [list(point) for point in MARQUEE_DRAG],
            "existing_selection_px": EXISTING_SELECTION,
            "cases": [case[0] for case in MARQUEE_CASES],
        },
        "observed": {"cases": results},
        "limitations": [
            "Rectangular Marquee options (style, feather, anti-alias) were not set or read.",
            "Only selection bounds were read; union versus constrained shape is told apart by bounds.",
        ],
    }


# The last segment runs at about 27 degrees, so a 45-degree constraint moves it visibly.
PEN_CLICKS = [(100, 100), (300, 120), (460, 200)]
SQUARE_PATH = [[100, 100], [300, 100], [300, 300], [100, 300]]


def _square_work_path(ps: Photoshop) -> None:
    points = ",".join(
        f"(function(){{var p=new PathPointInfo();p.kind=PointKind.CORNERPOINT;"
        f"p.anchor=[{x},{y}];p.leftDirection=[{x},{y}];p.rightDirection=[{x},{y}];return p;}})()"
        for x, y in SQUARE_PATH
    )
    ps.js(
        "var s=new SubPathInfo();s.closed=true;s.operation=ShapeOperation.SHAPEXOR;"
        f"s.entireSubPath=[{points}];"
        'var item=app.activeDocument.pathItems.add("observed-truth-square",[s]);item.select();"null";'
    )


def anchor_clicks(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    original_tool = ps.current_tool()
    observed: dict[str, Any] = {}
    try:
        ps.new_document("pen-clicks", 600, 400)
        try:
            ps.select_tool("penTool")
            win_input.focus(identity.hwnd, identity.pid)
            for index, point in enumerate(PEN_CLICKS):
                hold = ("shift",) if index == len(PEN_CLICKS) - 1 else ()
                _act(identity, click(_screen(ps, identity, *point), hold=hold))
            _act(identity, chord("escape"))
            observed["pen_shift_click_last"] = ps.path_anchors()
        finally:
            ps.close_throwaway_document()

        # Which anchors are selected is not scriptable: nudge right and see which moved.
        for name, modifier in (("shift_click_second", "shift"), ("ctrl_click_second", "ctrl")):
            ps.new_document(f"direct-select-{modifier}", 600, 400)
            try:
                _square_work_path(ps)
                ps.select_tool("directSelectTool")
                win_input.focus(identity.hwnd, identity.pid)
                _act(identity, click(_screen(ps, identity, *SQUARE_PATH[0])))
                _act(identity, click(_screen(ps, identity, *SQUARE_PATH[1]), hold=(modifier,)))
                before = ps.path_anchors()
                _act(identity, chord("right") * 10)
                observed[name] = {"before_nudge": before, "after_10_right_arrows": ps.path_anchors()}
            finally:
                ps.close_throwaway_document()
    finally:
        ps.select_tool(original_tool)
    return {
        "operation": "observe_anchor_clicks",
        "parameters": {
            "behaviour_id": "path_anchor_shift_click",
            "pen_clicks_document_px": [list(point) for point in PEN_CLICKS],
            "pen_last_click_hold": ["shift"],
            "direct_select_path_px": SQUARE_PATH,
            "direct_select_sequence": "click anchor 0, modifier-click anchor 1, 10 right arrows",
        },
        "observed": observed,
        "limitations": [
            "Anchor selection state is not readable by script; it is inferred from which anchors moved.",
            "Pen tool mode (Path vs Shape) was not set; anchors are read from every path item.",
        ],
    }


TRANSFORM_LAYER = [[200, 150], [300, 150], [300, 200], [200, 200]]  # 100 x 50 pixels
CORNER_DRAG = ((300, 200), (360, 210))
TRANSFORM_CASES = [("corner_drag_plain", (), "before_press"), ("corner_drag_shift_mid_drag", ("shift",), "mid_drag")]


def free_transform_proportional(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    original_tool = ps.current_tool()
    results = []
    try:
        for name, hold, hold_from in TRANSFORM_CASES:
            ps.new_document(f"free-transform-{name}", 600, 400)
            try:
                ps.js(
                    "var doc=app.activeDocument;doc.artLayers.add();"
                    f"doc.selection.select({TRANSFORM_LAYER});var c=new SolidColor();"
                    'c.rgb.red=0;c.rgb.green=0;c.rgb.blue=0;doc.selection.fill(c);doc.selection.deselect();"null";'
                )
                ps.select_tool("moveTool")
                before = ps.layer_bounds()
                win_input.focus(identity.hwnd, identity.pid)
                _act(identity, chord("ctrl+t"))
                start, end = (_screen(ps, identity, *point) for point in CORNER_DRAG)
                _act(identity, drag(start, end, steps=8, hold=hold, hold_from=hold_from))
                _act(identity, chord("enter"))
                results.append({"case": name, "layer_bounds_before": before, "layer_bounds_after": ps.layer_bounds()})
            finally:
                ps.close_throwaway_document()
    finally:
        ps.select_tool(original_tool)
    return {
        "operation": "observe_free_transform_proportional",
        "parameters": {
            "behaviour_id": "transform_free_transform_proportional_default",
            "layer_rect_px": TRANSFORM_LAYER,
            "corner_drag_document_px": [list(point) for point in CORNER_DRAG],
            "cases": [case[0] for case in TRANSFORM_CASES],
        },
        "observed": {"legacy_free_transform": ps.legacy_free_transform(), "cases": results},
        "limitations": [
            "Proportionality is judged from layer bounds after commit, not from the live preview.",
            "The handle is grabbed at the mapped corner point; a miss would show as unchanged bounds.",
        ],
    }


SCENARIOS: dict[str, Spec] = {
    "marquee_shift_timing": Spec(marquee_shift_timing, needs_input=True),
    "anchor_clicks": Spec(anchor_clicks, needs_input=True),
    "free_transform_proportional": Spec(free_transform_proportional, needs_input=True),
}
