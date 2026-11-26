"""Illustrator's Width tool, Pencil and Simplify, measured with the harness's own paths and drags
(runner_illustrator freehand_document, drag_points, outline_paths, simplify_selected).

- Width: a straight path (WIDTH_PATH, stroke 4 pt) gets a width point dragged out from one of its
  points by the Width tool; a live Outline Stroke is applied and expanded, and the outline is kept,
  so the stroke's width can be read along the path.
- Pencil: the Pencil tool is dragged through a known curve (a sine wave or a circle) at its
  default fidelity and at each other Fidelity stop, set through the Pencil options dialog
  (pencil_fidelity; a preference set by script neither shows there nor reaches the tool); the
  path it makes is kept, to compare with the points the mouse passed.
- Simplify: a 200-point noisy sine (seeded) is simplified by Object > Path > Simplify at its
  automatic amount; the path before and after is kept.
Coordinates are document points (y up) on a 300 x 300 pt artboard.

Drags are fitted into the part of the canvas no floating panel covers (runner_illustrator
drag_points, canvas_room): a first run sent its drags under floating docks, which took them, and
looked as if the tools ignored synthetic drags.
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np

from .families import ScenarioSpec

SIZE = 300
WIDTH_PATH = ((50, 150), (250, 150))
STROKE = 4.0


def sine(n: int = 60) -> list[list[float]]:
    return [[50 + 200 * k / (n - 1), 150 + 40 * math.sin(2 * math.pi * k / (n - 1))] for k in range(n)]


def circle(n: int = 72) -> list[list[float]]:
    return [[150 + 70 * math.cos(2 * math.pi * k / n), 150 + 70 * math.sin(2 * math.pi * k / n)] for k in range(n + 1)]


def noisy_sine() -> list[list[float]]:
    rng = np.random.default_rng(20261126)
    base = sine(200)
    return [[x, y + float(rng.normal(0, 1.0))] for x, y in base]


def document_js(kind: str) -> str:
    """ExtendScript making the probe's scratch document; returns its name."""
    head = ("var pr=new DocumentPreset();pr.title=PREFIX+'freehand';"
            f"pr.width={SIZE};pr.height={SIZE};pr.units=RulerUnits.Points;pr.colorMode=DocumentColorSpace.RGB;"
            "var d=app.documents.addDocument('',pr,false);d.selection=null;")
    black = "var k=new RGBColor();k.red=0;k.green=0;k.blue=0;"
    if kind == "width":
        (x0, y0), (x1, y1) = WIDTH_PATH
        body = (f"var p=d.pathItems.add();p.setEntirePath([[{x0},{y0}],[{x1},{y1}]]);p.filled=false;p.stroked=true;"
                f"{black}p.strokeColor=k;p.strokeWidth={STROKE};")
    elif kind == "simplify":
        pts = ",".join(f"[{x:.3f},{y:.3f}]" for x, y in noisy_sine())
        body = f"var p=d.pathItems.add();p.setEntirePath([{pts}]);p.filled=false;p.stroked=true;{black}p.strokeColor=k;p.selected=true;"
    else:
        body = ""
    return head + body + "return q(d.name);"


PATHS_JS = (
    "var d=app.activeDocument,paths=[];"
    "function walk(it){if(it.typename=='PathItem'){var pp=it.pathPoints,a=[];"
    "for(var i=0;i<pp.length;i++){var q1=pp[i].anchor,l=pp[i].leftDirection,r=pp[i].rightDirection;"
    "a.push('['+[q1[0],q1[1],l[0],l[1],r[0],r[1]].join(',')+']');}"
    "paths.push('{\"closed\":'+it.closed+',\"area\":'+it.area+',\"points\":['+a.join(',')+']}');}"
    "else if(it.typename=='CompoundPathItem'){for(var j=0;j<it.pathItems.length;j++)walk(it.pathItems[j]);}"
    "else if(it.pageItems){for(var j=0;j<it.pageItems.length;j++)walk(it.pageItems[j]);}}"
)

OUTLINE_JS = (
    "var d=app.activeDocument;d.selection=null;var p=d.pathItems[0];p.selected=true;"
    "p.applyEffect('<LiveEffect name=\"Adobe Outline Stroke\"><Dict data=\"\"/></LiveEffect>');"
    "d.selection=null;p.selected=true;app.executeMenuCommand('expandStyle');"
    + PATHS_JS + "var s=d.selection;for(var i=0;i<s.length;i++)walk(s[i]);return '['+paths.join(',')+']';"
)

ALL_PATHS_JS = PATHS_JS + "for(var i=0;i<d.pathItems.length;i++)walk(d.pathItems[i]);return '['+paths.join(',')+']';"


FIDELITY_STOPS = 5  # the Pencil options dialog's Fidelity slider: Accurate (0) to Smooth (4)


def fidelity_slider(image: Any) -> tuple[int, list[float], int]:
    """Read the Fidelity slider from a capture of the Pencil options dialog: the stop the knob is
    on, every stop's x and the track's row (image pixels). The knob is the topmost blue disc (the
    checkboxes below are blue too); the stops are the light tick marks just above the track, the
    knob standing in for the one it covers."""
    a = np.asarray(image, int)
    ys, xs = np.nonzero((a[..., 2] > 200) & (a[..., 0] < 120))
    knob = ys < ys.min() + 20
    knob_x, y = float(xs[knob].mean()), int(round(ys[knob].mean()))
    band = a[y - 9:y - 2]
    light = ((band[..., 0] > 110) & (np.abs(band[..., 0] - band[..., 2]) < 15)).any(axis=0)
    marks = [float(x) for x in np.nonzero(light)[0] if abs(x - knob_x) > 8]
    positions = sorted(marks + [knob_x])
    first, last = positions[0], positions[-1]
    step = min(b - a2 for a2, b in zip(positions, positions[1:]) if b - a2 > 30)
    step = (last - first) / round((last - first) / step)
    stops = [first + step * k for k in range(FIDELITY_STOPS)]
    return int(round((knob_x - first) / step)), stops, y


def _spec(item_id: str, steps: tuple) -> ScenarioSpec:
    return ScenarioSpec(item_id, "illustrator_freehand", "run", True,
                        steps + (("record", "freehand"), ("close_throwaway_document",)))


def freehand_specs() -> list[ScenarioSpec]:
    specs = []
    for x, d in ((150, 10), (150, 20), (100, 15)):
        specs.append(_spec(f"width:x={x}:drag={d}", (("freehand_document", "width"), ("select_tool", "Adobe Width Tool"),
                                                      ("drag_points", [[x, 150], [x, 150 + d / 2], [x, 150 + d]]), ("outline_paths",))))
    specs.append(_spec("width:none", (("freehand_document", "width"), ("outline_paths",))))
    for name, pts in (("sine", sine()), ("circle", circle())):
        specs.append(_spec(f"pencil:{name}", (("freehand_document", "pencil"), ("select_tool", "Adobe Freehand Tool"),
                                              ("drag_points", pts), ("all_paths",))))
    for x, d in ((150, 20), (100, 16)):  # Alt+drag: one side only
        specs.append(_spec(f"width:x={x}:drag={d}:one_side", (("freehand_document", "width"), ("select_tool", "Adobe Width Tool"),
                                                               ("drag_points", [[x, 150], [x, 150 + d / 2], [x, 150 + d]], ["alt"]),
                                                               ("outline_paths",))))
    for fidelity in (0, 1, 3, 4):
        for name, pts in (("sine", sine()), ("circle", circle())):
            specs.append(ScenarioSpec(f"pencil:{name}:fidelity={fidelity}", "illustrator_freehand", "run", True, (
                ("freehand_document", "pencil"), ("pencil_fidelity", fidelity), ("drag_points", pts), ("all_paths",),
                ("record", "freehand"), ("restore_pencil_fidelity",), ("close_throwaway_document",))))
    specs.append(_spec("simplify:auto", (("freehand_document", "simplify"), ("all_paths",), ("simplify_selected",), ("all_paths",))))
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith(("width:", "pencil:", "simplify:")) and row.get("status") == "ok" and "freehand" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["freehand"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_freehand --dataset <illustrator dir> [--results <sweep>/results.jsonl]"""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "freehand-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} freehand probe rows written")
        return
    specs = freehand_specs()
    with (args.dataset / "freehand-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} freehand probe specs")


if __name__ == "__main__":
    main()
