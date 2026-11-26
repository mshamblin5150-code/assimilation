"""Illustrator's Pathfinder on curves: two overlapping circles combined by every Pathfinder
command value, expanded and measured as full geometry (runner_illustrator pathfinder_curves).

The circles (radius R, centres D apart on one row, drawn by the DOM as four-anchor ellipses) have
exact booleans to compare against: lens (intersection) area 2R^2 acos(D/2R) - (D/2)sqrt(4R^2 -
D^2), and the two crossing points at x = mid, y = centre +- sqrt(R^2 - (D/2)^2).
"""

from __future__ import annotations

import json
import math
from typing import Any

from .families import ScenarioSpec

R, D = 50.0, 60.0
LEFT = (100.0, 100.0)  # centre x, y (document coordinates, y up)
RIGHT = (LEFT[0] + D, LEFT[1])
COMMANDS = tuple(range(13))


def lens_area() -> float:
    return 2 * R * R * math.acos(D / (2 * R)) - (D / 2) * math.sqrt(4 * R * R - D * D)


def crossings() -> list[tuple[float, float]]:
    h = math.sqrt(R * R - (D / 2) ** 2)
    mid = (LEFT[0] + RIGHT[0]) / 2
    return [(mid, LEFT[1] + h), (mid, LEFT[1] - h)]


def pathfinder_js(command: int) -> str:
    """ExtendScript drawing the two circles as a group in a new document, applying Pathfinder with
    `command`, expanding, and returning every path as JSON; the document is closed unsaved."""
    xml = f'<LiveEffect name="Adobe Pathfinder"><Dict data="I Command {int(command)} "/></LiveEffect>'
    (lx, ly), (rx, ry) = LEFT, RIGHT
    return (
        "var doc=app.documents.add(DocumentColorSpace.RGB,300,300);"
        "try{var g=doc.groupItems.add();"
        f"g.pathItems.ellipse({ly + R},{lx - R},{2 * R},{2 * R});g.pathItems.ellipse({ry + R},{rx - R},{2 * R},{2 * R});"
        f"var err='';try{{g.applyEffect({json.dumps(xml)});}}catch(e){{err=String(e);}}"
        "doc.selection=null;g.selected=true;app.executeMenuCommand('expandStyle');var paths=[];"
        "function walk(it){if(it.typename=='PathItem'){var pp=it.pathPoints,a=[];"
        "for(var i=0;i<pp.length;i++){var q1=pp[i].anchor,l=pp[i].leftDirection,r=pp[i].rightDirection;"
        "a.push('['+[q1[0],q1[1],l[0],l[1],r[0],r[1]].join(',')+']');}"
        "paths.push('{\"closed\":'+it.closed+',\"filled\":'+it.filled+',\"area\":'+it.area+',\"points\":['+a.join(',')+']}');}"
        "else if(it.typename=='CompoundPathItem'){for(var j=0;j<it.pathItems.length;j++)walk(it.pathItems[j]);}"
        "else if(it.pageItems){for(var j=0;j<it.pageItems.length;j++)walk(it.pageItems[j]);}}"
        "var s=doc.selection;for(var k=0;k<s.length;k++)walk(s[k]);"
        "return '{\"error\":'+q(err)+',\"paths\":['+paths.join(',')+']}';"
        "}finally{doc.close(SaveOptions.DONOTSAVECHANGES);}"
    )


def pathfinder_specs() -> list[ScenarioSpec]:
    return [ScenarioSpec(f"pathfinder:circles:command={c}", "illustrator_pathfinder", "run", False,
                         (("pathfinder_curves", c), ("record", "pathfinder"))) for c in COMMANDS]


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("pathfinder:") and row.get("status") == "ok" and "pathfinder" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["pathfinder"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_pathfinder --dataset <illustrator dir> [--results <sweep>/results.jsonl]"""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "pathfinder-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} pathfinder probe rows written")
        return
    specs = pathfinder_specs()
    with (args.dataset / "pathfinder-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} pathfinder probe specs")


if __name__ == "__main__":
    main()
