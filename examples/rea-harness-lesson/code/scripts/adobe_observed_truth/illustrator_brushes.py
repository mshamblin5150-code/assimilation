"""Illustrator's art, pattern and scatter brushes along a path, measured with the harness's own art.

Scripting can apply a brush (Brush.applyTo) but cannot make one, so each spec (runner_illustrator)
draws the harness's own arrow (ARROW, filled, no stroke) in a scratch document, makes a brush of it
through the Brushes panel's New Brush button and its dialogs at their defaults (define_brush: the
dialogs are self-drawn, so their words are found by OCR and clicked), then applies the brush to
each test path, expands it and keeps every path's anchors and handles. The brush lives in the
scratch document and goes with it.
"""

from __future__ import annotations

import json
import math
from typing import Any

from .families import ScenarioSpec

# The harness's own art: an arrow 120 pt long and 30 pt across (document coordinates, y up),
# its tip at the right; filled black, no stroke.
ARROW = ((0, 0), (100, 0), (100, -8), (120, 15), (100, 38), (100, 30), (0, 30))
ART_ORIGIN = (40, 260)
ART_LENGTH, ART_WIDTH = 120.0, 46.0  # bounds of ARROW: x 0..120, y -8..38
KAPPA = 0.5522847498

# Test paths: (name, anchors as (x, y, left handle, right handle)).
PATHS = {
    "line": [((30, 100), None, None), ((270, 100), None, None)],
    "arc": [((70, 150), None, (70, 150 + KAPPA * 80)), ((150, 230), (150 - KAPPA * 80, 230), (150 + KAPPA * 80, 230)),
            ((230, 150), (230, 150 + KAPPA * 80), None)],
    "corner": [((40, 40), None, None), ((160, 40), None, None), ((160, 140), None, None)],
    # 2.5 and 2.75 art lengths: how a pattern brush rounds its tile count.
    "line_300": [((0, 20), None, None), ((300, 20), None, None)],
    "line_330": [((-15, 280), None, None), ((315, 280), None, None)],
    # A closed square, 120 pt a side: four corners and no ends.
    "square": [((170, 140), None, None), ((290, 140), None, None), ((290, 260), None, None), ((170, 260), None, None)],
}
CLOSED = {"square"}
ARC_CENTRE, ARC_RADIUS = (150, 150), 80.0


def path_length(name: str) -> float:
    if name == "line":
        return 240.0
    if name == "corner":
        return 220.0
    if name in ("line_300", "line_330"):
        return float(name.removeprefix("line_"))
    if name == "square":
        return 480.0
    return math.pi * ARC_RADIUS  # the Bezier semicircle is within 0.03% of this


def document_js() -> str:
    """ExtendScript: a scratch document with the arrow drawn and selected (the art to make a brush of)."""
    ox, oy = ART_ORIGIN
    points = ",".join(f"[{ox + x},{oy + y}]" for x, y in ARROW)
    return (
        "var d=app.documents.add(DocumentColorSpace.RGB,300,300);d.selection=null;"
        f"var a=d.pathItems.add();a.setEntirePath([{points}]);a.closed=true;a.filled=true;a.stroked=false;"
        "var k=new RGBColor();k.red=0;k.green=0;k.blue=0;a.fillColor=k;a.selected=true;return q(d.name);"
    )


def apply_js(brush: str) -> str:
    """ExtendScript applying brush `brush` to every test path, expanding each and returning its
    paths as JSON; the scratch document is then closed unsaved."""
    builds = []
    for name, anchors in PATHS.items():
        pts = ",".join(f"[{a[0][0]},{a[0][1]}]" for a in anchors)
        handles = "".join(
            (f"p.pathPoints[{i}].leftDirection=[{l[0]},{l[1]}];" if l else "")
            + (f"p.pathPoints[{i}].rightDirection=[{r[0]},{r[1]}];" if r else "")
            for i, (_, l, r) in enumerate(anchors))
        closed = "p.closed=true;" if name in CLOSED else ""
        builds.append(f"var p=d.pathItems.add();p.setEntirePath([{pts}]);{closed}{handles}p.filled=false;p.stroked=true;todo.push([{json.dumps(name)},p]);")
    return (
        "var d=app.activeDocument;try{var br=d.brushes.getByName(" + json.dumps(brush) + ");var todo=[];"
        + "".join(builds) +
        "var out=[];for(var n=0;n<todo.length;n++){var p=todo[n][1];br.applyTo(p);d.selection=null;p.selected=true;"
        "app.executeMenuCommand('expandStyle');var s=d.selection,paths=[];"
        "function walk(it){if(it.typename=='PathItem'){var pp=it.pathPoints,a=[];"
        "for(var i=0;i<pp.length;i++){var q1=pp[i].anchor,l=pp[i].leftDirection,r=pp[i].rightDirection;"
        "a.push('['+[q1[0],q1[1],l[0],l[1],r[0],r[1]].join(',')+']');}"
        "paths.push('{\"closed\":'+it.closed+',\"area\":'+it.area+',\"points\":['+a.join(',')+']}');}"
        "else if(it.typename=='CompoundPathItem'){for(var j=0;j<it.pathItems.length;j++)walk(it.pathItems[j]);}"
        "else if(it.pageItems){for(var j=0;j<it.pageItems.length;j++)walk(it.pageItems[j]);}}"
        "for(var i=0;i<s.length;i++)walk(s[i]);for(var i=s.length-1;i>=0;i--)s[i].remove();"
        "out.push(q(todo[n][0])+':['+paths.join(',')+']');}"
        "return '{'+out.join(',')+'}';}finally{d.close(SaveOptions.DONOTSAVECHANGES);}"
    )


KINDS = {"art": ("Art", "Art Brush 1", "Art Brush Options"), "pattern": ("Pattern", "Pattern Brush 1", "Pattern Brush Options"),
         "scatter": ("Scatter", "Scatter Brush 1", "Scatter Brush Options")}


# One Pattern Brush Options setting changed per spec, typed or clicked in its dialog
# (runner_illustrator define_brush): scale and spacing in percent, the fit, flip along.
PATTERN_OPTIONS = {"scale=50": {"scale": 50}, "spacing=25": {"spacing": 25}, "fit=add_space": {"fit": "add_space"},
                   "fit=approximate": {"fit": "approximate"}, "flip_along": {"flip_along": True}}


def brush_specs() -> list[ScenarioSpec]:
    specs = [ScenarioSpec(f"brush:{kind}:defaults", "illustrator_brushes", "run", True,
                          (("brush_document",), ("define_brush", kind), ("brush_paths", KINDS[kind][1]), ("record", "brushes")))
             for kind in KINDS]
    specs += [ScenarioSpec(f"brush:pattern:{name}", "illustrator_brushes", "run", True,
                           (("brush_document",), ("define_brush", "pattern", settings), ("brush_paths", KINDS["pattern"][1]), ("record", "brushes")))
              for name, settings in PATTERN_OPTIONS.items()]
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("brush:") and row.get("status") == "ok" and "brushes" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["brushes"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_brushes --dataset <illustrator dir> [--results <sweep>/results.jsonl]"""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "brush-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} brush probe rows written")
        return
    specs = brush_specs()
    with (args.dataset / "brush-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} brush probe specs")


if __name__ == "__main__":
    main()
