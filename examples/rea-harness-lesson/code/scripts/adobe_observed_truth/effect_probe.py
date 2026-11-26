"""The layer effect probe: Photoshop's Stroke, Outer Glow and Drop Shadow measured as profiles.

Each spec makes a 200 x 200 document: a white background and, on its own layer, the harness's
own black square (SQUARE). One effect is applied to that layer in pure red at full opacity, normal
mode, and the composite is read along three lines through the square's centre (row, column and
the diagonal through a corner). Outside the square the effect's coverage is 1 - green / 255; inside
(a stroke over the square) it is red / 255.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from .families import ScenarioSpec

SIZE = 200
SQUARE = (70, 70, 130, 130)  # left, top, right, bottom


def document_js() -> str:
    l, t, r, b = SQUARE
    return (f"var d=app.documents.add(UnitValue({SIZE},'px'),UnitValue({SIZE},'px'),72,'observed-truth-effect',"
            "NewDocumentMode.RGB,DocumentFill.WHITE);var lay=d.artLayers.add();lay.name='observed-truth-shape';"
            f"d.selection.select([[{l},{t}],[{r},{t}],[{r},{b}],[{l},{b}]]);var c=new SolidColor();c.rgb.red=0;c.rgb.green=0;c.rgb.blue=0;"
            "d.selection.fill(c);d.selection.deselect();'null';")


def _red(var: str) -> str:
    return (f"var {var}=new ActionDescriptor();{var}.putDouble(charIDToTypeID('Rd  '),255);{var}.putDouble(charIDToTypeID('Grn '),0);"
            f"{var}.putDouble(charIDToTypeID('Bl  '),0);")


def effect_js(kind: str, p: dict[str, Any]) -> str:
    """ExtendScript applying one layer effect to the active layer."""
    c = "charIDToTypeID"
    s = "stringIDToTypeID"
    common = (f"e.putBoolean({c}('enab'),true);e.putEnumerated({c}('Md  '),{c}('BlnM'),{c}('Nrml'));"
              f"e.putUnitDouble({c}('Opct'),{c}('#Prc'),100);" + _red("rgb") + f"e.putObject({c}('Clr '),{c}('RGBC'),rgb);")
    if kind == "stroke":
        style = {"outside": "OutF", "inside": "InsF", "center": "CtrF"}[p["position"]]
        body = (f"var e=new ActionDescriptor();{common}e.putEnumerated({c}('Styl'),{c}('FStl'),{c}('{style}'));"
                f"e.putEnumerated({c}('PntT'),{c}('FrFl'),{c}('SClr'));e.putUnitDouble({c}('Sz  '),{c}('#Pxl'),{p['size']});"
                f"fx.putObject({c}('FrFX'),{c}('FrFX'),e);")
    elif kind == "glow":
        technique = "SfBL" if p["technique"] == "softer" else "PrBL"
        body = (f"var e=new ActionDescriptor();{common}e.putEnumerated({c}('GlwT'),{c}('BETE'),{c}('{technique}'));"
                f"e.putUnitDouble({c}('Ckmt'),{c}('#Pxl'),{p['spread']});e.putUnitDouble({c}('blur'),{c}('#Pxl'),{p['size']});"
                f"e.putUnitDouble({c}('Nose'),{c}('#Prc'),0);e.putUnitDouble({c}('ShdN'),{c}('#Prc'),0);e.putBoolean({c}('AntA'),false);"
                f"e.putUnitDouble({c}('Inpr'),{c}('#Prc'),50);fx.putObject({c}('OrGl'),{c}('OrGl'),e);")
    elif kind == "shadow":
        body = (f"var e=new ActionDescriptor();{common}e.putBoolean({c}('uglg'),false);e.putUnitDouble({c}('lagl'),{c}('#Ang'),90);"
                f"e.putUnitDouble({c}('Dstn'),{c}('#Pxl'),{p['distance']});e.putUnitDouble({c}('Ckmt'),{c}('#Pxl'),{p['spread']});"
                f"e.putUnitDouble({c}('blur'),{c}('#Pxl'),{p['size']});e.putUnitDouble({c}('Nose'),{c}('#Prc'),0);"
                f"e.putBoolean({c}('AntA'),false);e.putBoolean({s}('layerConceals'),true);fx.putObject({c}('DrSh'),{c}('DrSh'),e);")
    else:
        raise ValueError(kind)
    return ("var d=new ActionDescriptor(),r=new ActionReference();r.putProperty(charIDToTypeID('Prpr'),charIDToTypeID('Lefx'));"
            "r.putEnumerated(charIDToTypeID('Lyr '),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));d.putReference(charIDToTypeID('null'),r);"
            f"var fx=new ActionDescriptor();fx.putUnitDouble({c}('Scl '),{c}('#Prc'),100);" + body +
            f"d.putObject({c}('T   '),{c}('Lefx'),fx);executeAction({c}('setd'),d,DialogModes.NO);'null';")


CASES: list[tuple[str, str, dict[str, Any]]] = [
    *(("stroke", f"size={s}:position={pos}", {"size": s, "position": pos}) for s in (1, 3, 10) for pos in ("outside", "inside", "center")),
    *(("glow", f"size={s}:spread={sp}:{t}", {"size": s, "spread": sp, "technique": t})
      for s in (5, 20) for sp in (0, 50) for t in ("softer", "precise")),
    *(("shadow", f"distance={d}:size={s}:spread={sp}", {"distance": d, "size": s, "spread": sp})
      for d, s, sp in ((0, 0, 0), (10, 0, 0), (0, 5, 0), (0, 20, 0), (10, 20, 0), (0, 20, 50))),
]


def effect_specs() -> list[ScenarioSpec]:
    return [ScenarioSpec(f"effect:{kind}:{name}", "effect_probe", "run", False,
                         (("effect_document",), ("layer_effect", kind, params), ("record", "effect"), ("close_throwaway_document",)))
            for kind, name, params in CASES]


def measure(pixels: np.ndarray) -> dict[str, Any]:
    """Red and green along the row and column through the centre and the diagonal through (0, 0)."""
    mid = SIZE // 2
    idx = np.arange(SIZE)
    lines = {"row": pixels[mid, :, :3], "column": pixels[:, mid, :3], "diagonal": pixels[idx, idx, :3]}
    return {name: {"red": line[:, 0].astype(int).tolist(), "green": line[:, 1].astype(int).tolist()} for name, line in lines.items()}


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("effect:") and row.get("status") == "ok" and "effect" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["effect"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.effect_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "effect-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} effect probe rows written")
        return
    specs = effect_specs()
    with (args.dataset / "effect-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} effect probe specs")


if __name__ == "__main__":
    main()
