"""Illustrator's tools used on the fixture, each with the gesture its work needs (runner_illustrator).

Selecting a tool runs almost none of its code; using it does. Each toolbar tool gets a gesture
planned on the 400 x 300 pt artboard with Photoshop's tool_gestures shapes (scaled from its
600 x 400 chart): a drag (shapes, transforms, selections, graphs, slices, the view tools), a
stroke (brushes, pencils, erasers, the liquify tools, Width, Shape Builder, the symbol tools),
corners clicked (Pen, Curvature, Blend), a click (anchor point tools, the eyedropper, Magic Wand,
the live paint bucket, mesh, touch type) or a click then typed text (type tools); what the tool
started is then ended with Escape where it waits (an open path, a text edit). The CC Charts tool
(a cloud feature) and the print tiling tool are never used.
"""

from __future__ import annotations

from .families import ScenarioSpec
from .inventory import Item

CANVAS = ("stroke", "drag", "click", "polygon", "type")
_NEVER = ("CC Charts Tool", "Adobe Page Tool")
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("type", ("Type Tool",)),
    ("polygon", ("Pen Tool", "Curvature Tool", "Blend Tool")),
    ("click", ("Anchor Point Tool", "Eyedropper", "Magic Wand", "Paintbucket", "Mesh", "Touch Type")),
    ("stroke", ("Brush", "Freehand", "Erase", "Smooth", "Width", "Shape Builder", "Symbol", "Warp", "Twirl",
                "Pucker", "Bloat", "Scallop", "Cyrstallize", "Wrinkle", "Knife", "Shaper")),
)
_COMMIT = {"type": "escape", "polygon": "escape"}


def gesture_for(name: str) -> str:
    """The gesture a tool's work needs (CANVAS), or never."""
    if name in _NEVER:
        return "never"
    if name == "Adobe Touch Type Tool":
        return "click"
    for kind, words in _RULES:
        if any(word in name for word in words):
            return kind
    return "drag"


def tool_specs(tools: list[Item]) -> list[ScenarioSpec]:
    """Each canvas tool selected by its own name and used once on the fixture."""
    specs = []
    for tool in tools:
        kind = gesture_for(tool.name)
        if kind not in CANVAS:
            continue
        steps = (("new_fixture",), ("select_tool", tool.facts.get("tool_id", tool.name)),
                 ("use_tool", kind, _COMMIT.get(kind, "")), ("record", "dialogs", "document"),
                 ("cancel_dialogs",), ("close_throwaway_document",))
        specs.append(ScenarioSpec(f"{tool.id}@use", "tool_use", "run", True, steps))
    return specs


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_tools --dataset <dir>: write tool-families.jsonl."""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    from .inventory import load_inventory

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    specs = tool_specs([i for i in load_inventory(args.dataset / "inventory.jsonl") if i.kind == "tool"])
    with (args.dataset / "tool-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} tool-use specs")


if __name__ == "__main__":
    main()
