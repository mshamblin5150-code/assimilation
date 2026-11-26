"""Illustrator's Image Trace measured on the harness's own raster images (runner_illustrator
trace_image).

Each spec places one of the images below (200 x 200 px, embedded, 1 px = 1 pt), traces it by
script (RasterItem.trace) with its tracing options set one at a time from the defaults, expands
the result and records every path: closed, filled, its fill colour, area, and each anchor with
its two handles. The images have known geometry, so a path can be compared with the shape it
came from: a circle, a square turned 30 degrees, a five-point star, a ring 6 px wide, a grey
ramp (left to right), three colour blobs and speckles of 1 to 16 px.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from .families import ScenarioSpec

SIZE = 200
CIRCLE = (100, 100, 60)  # centre x, y, radius
SQUARE = (100, 100, 50, 30)  # centre x, y, half side, turn in degrees
STAR = (100, 100, 80, 32, 5)  # centre x, y, outer and inner radius, points
RING = (100, 100, 60, 6)  # centre x, y, radius to the middle of the band, band width
BLOBS = (((60, 70, 35), (220, 40, 40)), ((140, 70, 35), (40, 160, 60)), ((100, 140, 40), (40, 70, 200)))
SPECKLES = ((30, 30, 1), (60, 30, 2), (90, 30, 3), (120, 30, 4), (150, 30, 6), (30, 100, 8), (80, 100, 12), (140, 100, 16))
# Eight flat colours in 40 px squares (two rows of four, from (20, 40)), for colour-count reduction.
PALETTE = ((220, 40, 40), (240, 140, 30), (230, 220, 40), (40, 160, 60), (40, 170, 200), (40, 70, 200), (150, 60, 190), (90, 90, 90))
# Black horizontal bars (top row, height px) across x 20..180, for stroke tracing.
BARS = ((20, 2), (40, 4), (60, 6), (85, 8), (115, 12), (150, 16))
# Three discs that overlap, the later painted over the earlier: four flat regions with white.
BLOBS_OVERLAP = (((80, 80, 45), (220, 40, 40)), ((120, 80, 45), (40, 160, 60)), ((100, 120, 45), (40, 70, 200)))


def _star_polygon() -> np.ndarray:
    cx, cy, outer, inner, points = STAR
    angles = np.arange(2 * points) * np.pi / points - np.pi / 2
    radii = np.where(np.arange(2 * points) % 2 == 0, outer, inner)
    return np.stack([cx + radii * np.cos(angles), cy + radii * np.sin(angles)], axis=1)


def _inside_polygon(poly: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    inside = np.zeros(xs.shape, dtype=bool)
    for (x1, y1), (x2, y2) in zip(poly, np.roll(poly, -1, axis=0)):
        crosses = (y1 > ys) != (y2 > ys)
        with np.errstate(divide="ignore", invalid="ignore"):
            at = (x2 - x1) * (ys - y1) / (y2 - y1) + x1
        inside ^= crosses & (xs < at)
    return inside


def raster(name: str) -> np.ndarray:
    """One probe image, RGB uint8 (pixel centres at +0.5)."""
    ys, xs = np.mgrid[0:SIZE, 0:SIZE] + 0.5
    image = np.full((SIZE, SIZE, 3), 255, dtype=np.uint8)
    if name == "circle":
        cx, cy, r = CIRCLE
        image[(xs - cx) ** 2 + (ys - cy) ** 2 <= r * r] = 0
    elif name == "square":
        cx, cy, half, turn = SQUARE
        a = np.radians(turn)
        u = (xs - cx) * np.cos(a) + (ys - cy) * np.sin(a)
        v = -(xs - cx) * np.sin(a) + (ys - cy) * np.cos(a)
        image[(np.abs(u) <= half) & (np.abs(v) <= half)] = 0
    elif name == "star":
        image[_inside_polygon(_star_polygon(), xs, ys)] = 0
    elif name == "ring":
        cx, cy, r, width = RING
        d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        image[np.abs(d - r) <= width / 2] = 0
    elif name == "ramp":
        image[:] = np.floor(np.arange(SIZE) * 256 / SIZE).astype(np.uint8)[None, :, None]
    elif name == "blobs":
        for (cx, cy, r), colour in BLOBS:
            image[(xs - cx) ** 2 + (ys - cy) ** 2 <= r * r] = colour
    elif name == "palette":
        for k, colour in enumerate(PALETTE):
            x, y = 20 + 40 * (k % 4), 40 + 60 * (k // 4)
            image[y:y + 40, x:x + 40] = colour
    elif name == "bars":
        for top, height in BARS:
            image[top:top + height, 20:180] = 0
    elif name == "blobs_overlap":
        for (cx, cy, r), colour in BLOBS_OVERLAP:
            image[(xs - cx) ** 2 + (ys - cy) ** 2 <= r * r] = colour
    elif name == "speckles":
        for x, y, side in SPECKLES:
            image[y:y + side, x:x + side] = 0
    else:
        raise ValueError(name)
    return image


IMAGES = ("circle", "square", "star", "ring", "ramp", "blobs", "speckles", "palette", "bars", "blobs_overlap")

# Tracing option values as the DOM takes them; strings are enumerations, written as such.
BLACK_AND_WHITE = {"tracingMode": "TracingModeType.TRACINGMODEBLACKANDWHITE", "ignoreWhite": True}


def trace_js(png: str, options: dict[str, Any]) -> str:
    """ExtendScript placing `png` in a new harness document, tracing it with `options`, expanding,
    and returning every path as JSON; the document is closed unsaved."""
    preset = f"o.loadFromPreset({json.dumps(options['preset'])});" if "preset" in options else ""  # first: the rest override it
    sets = preset + "".join(
        f"o.{k}={v};" if isinstance(v, str) and v.startswith("TracingModeType.") or isinstance(v, str) and "." in v
        else f"o.{k}={json.dumps(v)};" for k, v in options.items() if k != "preset")
    return (
        f"var doc=app.documents.add(DocumentColorSpace.RGB,{SIZE},{SIZE});"
        "try{var p=doc.placedItems.add();"
        f"p.file=new File({json.dumps(png)});p.position=[0,{SIZE}];p.embed();"
        "var t=doc.rasterItems[0].trace();var o=t.tracing.tracingOptions;" + sets +
        "app.redraw();var read={};for(var k in o){try{read[k]=String(o[k]);}catch(e){}}"
        "var g=t.tracing.expandTracing();var paths=[];"
        "function c(f){try{if(f.typename=='RGBColor')return '['+Math.round(f.red)+','+Math.round(f.green)+','+Math.round(f.blue)+']';"
        "if(f.typename=='GrayColor')return '{\"gray\":'+f.gray+'}';}catch(e){}return 'null';}"
        "function walk(it){if(it.typename=='PathItem'){var pp=it.pathPoints,a=[];"
        "for(var i=0;i<pp.length;i++){var q1=pp[i].anchor,l=pp[i].leftDirection,r=pp[i].rightDirection;"
        "a.push('['+[q1[0],q1[1],l[0],l[1],r[0],r[1]].join(',')+']');}"
        "paths.push('{\"closed\":'+it.closed+',\"filled\":'+it.filled+',\"fill\":'+(it.filled?c(it.fillColor):'null')"
        "+',\"stroked\":'+it.stroked+',\"stroke_width\":'+(it.stroked?it.strokeWidth:0)+',\"area\":'+it.area+',\"points\":['+a.join(',')+']}');}"
        "else if(it.typename=='CompoundPathItem'){for(var j=0;j<it.pathItems.length;j++)walk(it.pathItems[j]);}"
        "else if(it.pageItems){for(var j=0;j<it.pageItems.length;j++)walk(it.pageItems[j]);}}"
        "walk(g);var keys=[];for(var k in read)keys.push(q(k)+':'+q(read[k]));"
        "return '{\"options\":{'+keys.join(',')+'},\"paths\":['+paths.join(',')+']}';"
        "}finally{doc.close(SaveOptions.DONOTSAVECHANGES);}"
    )


def _spec(item_id: str, image: str, options: dict[str, Any]) -> ScenarioSpec:
    steps = (("trace_image", image, options), ("record", "trace"))
    return ScenarioSpec(item_id, "illustrator_trace", "run", False, steps)


def trace_specs() -> list[ScenarioSpec]:
    specs = []
    for image in ("circle", "square", "star", "ring", "speckles"):
        specs.append(_spec(f"trace:{image}:bw", image, BLACK_AND_WHITE))
        for key, values in (("pathFidelity", (0, 25, 75, 100)), ("cornerFidelity", (0, 25, 75, 100)), ("noiseFidelity", (1, 10, 100))):
            specs += [_spec(f"trace:{image}:bw:{key}={v}", image, {**BLACK_AND_WHITE, key: v}) for v in values]
        specs.append(_spec(f"trace:{image}:bw:snapCurveToLines", image, {**BLACK_AND_WHITE, "snapCurveToLines": True}))
    specs += [_spec(f"trace:ramp:bw:threshold={t}", "ramp", {**BLACK_AND_WHITE, "threshold": t}) for t in (1, 64, 128, 192, 255)]
    specs += [_spec(f"trace:blobs:color:tracingColors={n}", "blobs",
                    {"tracingMode": "TracingModeType.TRACINGMODECOLOR", "ignoreWhite": True, "tracingColors": n}) for n in (2, 3, 4, 6)]
    specs += [_spec("trace:circle:default", "circle", {}), _spec("trace:ring:bw:strokes", "ring", {**BLACK_AND_WHITE, "fills": False, "strokes": True})]
    # Colour-count reduction: tracingColors alone kept every colour, so colorFidelity (the
    # panel's Colors slider in limited mode, it may be) is tried too, and full colour.
    colour, limited = {"tracingMode": "TracingModeType.TRACINGMODECOLOR", "ignoreWhite": True}, "TracingColorType.TRACINGLIMITEDCOLOR"
    specs += [_spec(f"trace:palette:limited:tracingColors={n}", "palette", {**colour, "tracingColorTypeValue": limited, "tracingColors": n})
              for n in (2, 4, 8)]
    specs += [_spec(f"trace:palette:limited:colorFidelity={f}", "palette", {**colour, "tracingColorTypeValue": limited, "colorFidelity": f})
              for f in (0, 25, 50, 75)]
    specs += [_spec(f"trace:palette:full:colorFidelity={f}", "palette",
                    {**colour, "tracingColorTypeValue": "TracingColorType.TRACINGFULLCOLOR", "colorFidelity": f}) for f in (0, 50)]
    abutting = {"tracingMethod": "TracingMethodType.TRACINGMETHODABUTTING"}
    specs += [_spec("trace:ring:bw:abutting", "ring", {**BLACK_AND_WHITE, **abutting}),
              _spec("trace:blobs_overlap:color:overlapping", "blobs_overlap", colour),
              _spec("trace:blobs_overlap:color:abutting", "blobs_overlap", {**colour, **abutting})]
    specs += [_spec(f"trace:bars:strokes:maxStrokeWeight={w}", "bars", {**BLACK_AND_WHITE, "fills": False, "strokes": True, "maxStrokeWeight": w})
              for w in (4, 10, 20)]
    specs += [_spec("trace:bars:strokes_and_fills", "bars", {**BLACK_AND_WHITE, "fills": True, "strokes": True})]
    # Colour count through Illustrator's own presets: the options alone did not reduce colours.
    specs += [_spec(f"trace:palette:preset={name.strip('[]').lower().replace(' ', '_').replace('-', '_')}", "palette", {"preset": name})
              for name in ("3 Colors", "6 Colors", "16 Colors", "[Low Color]", "[Auto-Color]")]
    # The presets reduce; they differ from the specs above in colour type, white and method: one
    # of each changed, at three colours.
    three = {**colour, "tracingColorTypeValue": limited, "tracingColors": 3}
    specs += [_spec("trace:palette:tracingColors=3:full", "palette", {**three, "tracingColorTypeValue": "TracingColorType.TRACINGFULLCOLOR"}),
              _spec("trace:palette:tracingColors=3:white_kept", "palette", {**three, "ignoreWhite": False}),
              _spec("trace:palette:tracingColors=3:abutting", "palette", {**three, **abutting})]
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("trace:") and row.get("status") == "ok" and "trace" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["trace"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_trace --dataset <illustrator dir> [--results <sweep>/results.jsonl]"""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "trace-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} trace probe rows written")
        return
    specs = trace_specs()
    with (args.dataset / "trace-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} trace probe specs")


if __name__ == "__main__":
    main()
