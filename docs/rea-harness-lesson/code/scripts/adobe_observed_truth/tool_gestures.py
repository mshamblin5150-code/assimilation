"""Every Photoshop tool used on the canvas, not only selected.

Selecting a tool runs almost none of its code; using it does. Each toolbar tool gets the gesture
its work needs, planned on the 600x400 test chart: a stroke (brushes, erasers, toning and
retouching tools), a stroke after an Alt-click source (Clone Stamp, Healing Brush), a drag
(marquees, lassos, crop, gradient, shapes, move), a click (wand, bucket, eyedroppers, path and
anchor tools), corners clicked and closed (polygonal lasso, pens) or a click then typed text
(type tools); then committed where Photoshop waits for it (Enter, Ctrl+Enter). Tools that work
only inside a workspace or dialog (Select and Mask, Content-Aware Fill, the galleries and warps,
the eyedroppers of Levels and Curves) are covered where those are driven; the Neural Filters,
generative Remove and 3D tools are never used. tool_use_specs() runs each canvas tool on the
chart and in every document state, so the sampled sweep sees it work on every kind of layer.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import pairwise

from .document_states import STATES
from .families import ScenarioSpec, Step
from .input_plan import Event, MouseDown, MouseMove, MouseUp, chord, click, drag
from .inventory import Item

CANVAS = ("stroke", "source_stroke", "drag", "click", "polygon", "type")

_NEVER_NAMES = ("Remove Tool", "Place", "Edit Toolbar...", "Neural Filters")
_NEVER_IDS = ("neural", "prompt", "3d")  # id prefixes, matched without case
_WORKSPACE_IDS = ("selectionLab", "patchMatch", "targetedAdjustor", "PointTool", "blackAndWhiteTool",
                  "hueSatTool", "curvesTool", "eyedropper2Tool", "eyedropperPlusTool", "eyedropperMinusTool",
                  "ColorVibrancePointTool", "BlurGalleryTool", "PuppetWarpTool", "PerspectiveWarpTool")
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("source_stroke", ("Clone Stamp",)),
    ("type", ("Type",)),
    ("polygon", ("Polygonal Lasso", "Magnetic Lasso", "Pen Tool", "Curvature Pen", "Content-Aware Tracing")),
    ("click", ("Single Row", "Single Column", "Magic Wand", "Paint Bucket", "Magic Eraser", "Red Eye", "Eyedropper",
               "Color Sampler", "Note Tool", "Zoom", "Count", "Path Selection", "Direct Selection", "Anchor Point",
               "Convert Point", "Slice Select")),
    ("stroke", ("Brush", "Pencil", "Eraser", "Smudge", "Blur Tool", "Sharpen", "Dodge", "Burn", "Sponge",
                "Pattern Stamp", "Quick Selection", "Freeform Pen", "Color Replacement")),
)
_COMMIT = {"Crop Tool": "enter", "Perspective Crop Tool": "enter", "Free Transform": "enter",
           "Content-Aware Move Tool": "enter"}
_COMMIT_KIND = {"type": "ctrl+enter", "polygon": "enter"}


def gesture_for(name: str, tool_id: str) -> str:
    """The gesture a tool's work needs (CANVAS), or workspace (used inside a workspace or
    dialog, driven there) or never (AI on Adobe's servers, generative, 3D)."""
    if name in _NEVER_NAMES or tool_id.lower().startswith(_NEVER_IDS):
        return "never"
    if name == "Healing Brush Tool":  # not the Spot Healing Brush, which needs no source
        return "source_stroke"
    if tool_id.startswith(_WORKSPACE_IDS) or tool_id.endswith(_WORKSPACE_IDS):
        return "workspace"
    for kind, words in _RULES:
        if any(word in name for word in words):
            return kind
    return "drag"


Point = tuple[float, float]
ToScreen = Callable[[float, float], tuple[int, int]]
_STROKE: tuple[Point, ...] = ((100, 120), (250, 180), (400, 120), (500, 250), (300, 320))
_SOURCE: Point = (150, 150)
_DRAG: tuple[Point, Point] = ((120, 90), (380, 260))
_CLICK: Point = (300, 150)
_CORNERS: tuple[Point, ...] = ((120, 90), (380, 90), (380, 260), (120, 260))
_TYPE_AT: Point = (60, 330)
_TEXT = "Observed 123"


def _stroke(points: tuple[Point, ...], to_screen: ToScreen) -> list[Event]:
    screen = [to_screen(*p) for p in points]
    moves = [move for a, b in pairwise(screen) for move in drag(a, b, steps=8)[2:-1]]
    return [MouseMove(*screen[0]), MouseDown(), *moves, MouseUp()]


def gesture_events(kind: str, to_screen: ToScreen) -> list[Event]:
    """The input for one gesture on the chart, in screen points (`to_screen` maps chart pixels)."""
    if kind == "stroke":
        return _stroke(_STROKE, to_screen)
    if kind == "source_stroke":
        return [*click(to_screen(*_SOURCE), hold=("alt",)), *_stroke(_STROKE[2:], to_screen)]
    if kind == "drag":
        return drag(to_screen(*_DRAG[0]), to_screen(*_DRAG[1]), steps=16)
    if kind == "click":
        return click(to_screen(*_CLICK))
    if kind == "polygon":
        return [e for corner in (*_CORNERS, _CORNERS[0]) for e in click(to_screen(*corner))]
    if kind == "type":
        typed = [e for ch in _TEXT for e in (chord("shift+" + ch.lower()) if ch.isupper() else
                                             chord("space" if ch == " " else ch))]
        return [*click(to_screen(*_TYPE_AT)), *typed]
    raise ValueError(f"no gesture {kind!r}")


def _commit(name: str, kind: str) -> str:
    return _COMMIT.get(name) or _COMMIT_KIND.get(kind, "")


def tool_use_specs(tools: list[Item]) -> list[ScenarioSpec]:
    """Pass C: each canvas tool selected and used on the chart, then in every document state."""
    specs = []
    for tool in tools:
        kind = gesture_for(tool.name, tool.facts["tool_id"])
        if kind not in CANVAS:
            continue
        # The tool itself, by id: a shortcut selects whichever tool of its group was used last
        # (J could be the generative Remove tool), and the shortcuts have specs of their own.
        select: Step = ("select_tool_by_script", tool.facts["tool_id"])
        use: tuple[Step, ...] = (
            select,
            ("use_tool", kind, _commit(tool.name, kind)),
            ("record", "dialogs", "history", "pixels", "current_tool"),
            ("cancel_dialogs",),
            ("close_throwaway_document",),
        )
        opened: Step = ("open_test_image", "chart")
        specs.append(ScenarioSpec(f"{tool.id}@use", "tool_use", "run", True, (opened, *use)))
        specs += [ScenarioSpec(f"{tool.id}@use@{state}", "tool_use", "run", True, (opened, ("build_state", state), *use))
                  for state in STATES]
    return specs


def main() -> None:
    """python -m scripts.adobe_observed_truth.tool_gestures --dataset <dir>

    Write tool-families.jsonl (pass C) from the inventory; run it with
    runner_photoshop --specs tool-families.jsonl."""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    from .inventory import load_inventory

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    tools = [i for i in load_inventory(args.dataset / "inventory.jsonl") if i.kind == "tool"]
    specs = tool_use_specs(tools)
    with (args.dataset / "tool-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    used = len({s.item_id.split("@")[0] for s in specs})
    print(f"{len(specs)} tool-use specs: {used} of {len(tools)} tools on the canvas, {len(STATES) + 1} documents each")


if __name__ == "__main__":
    main()

