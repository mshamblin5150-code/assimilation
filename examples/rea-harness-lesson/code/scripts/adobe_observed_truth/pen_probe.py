"""The pen probe: Photoshop's brush driven by a pen through Windows pointer input (pen_input),
not by a brush pose, so pen values go the way a tablet's do.

Each spec paints one horizontal stroke on the brush canvas (brush_probe's, 400 x 300) with a plain
round tip (size SIZE, hardness 100, spacing 5%) whose size, opacity, roundness or angle follows a
pen value. A ramp takes that value from its least to its most along the stroke; a constant spec
holds it, so the dab cannot carry a value from another point of the stroke. The painted layer is
read as brush_probe.measure reads it (painted rows per column, the centre line).

Smoothing is off unless a spec names it: with it on (the person's 26% when first run), the dabs
trail the pen, so a ramp's dab carries a later, higher pen value than where it lands, and the
stroke stops short of the pen's last point.
"""

from __future__ import annotations

from typing import Any

from .brush_probe import ROW, _variation
from .families import ScenarioSpec

SIZE = 41
X0, X1 = 40, 360
N = 161  # pen frames along the stroke, one every 2 px


def stroke_points() -> list[list[int]]:
    return [[X0 + (X1 - X0) * k // (N - 1), ROW] for k in range(N)]


def ramp(low: float, high: float) -> list[float]:
    return [low + (high - low) * k / (N - 1) for k in range(N)]


def _tip(**variations: dict[str, Any]) -> dict[str, Any]:
    return {"useTipDynamics": True, "szVr": _variation(**variations.get("size", {})),
            "angleDynamics": _variation(**variations.get("angle", {})),
            "roundnessDynamics": _variation(**variations.get("roundness", {}))}


SMOOTHING_OFF = {"smoothing": False}


def _spec(name: str, dynamics: dict[str, Any], pen: dict[str, list], extra: dict[str, Any] | None = None,
          smoothing: dict[str, Any] = SMOOTHING_OFF) -> ScenarioSpec:
    options = {"size_px": SIZE, "hardness": 100, "opacity": 100, "flow": 100, "spacing": 5, **(extra or {}),
               "dynamics": {**smoothing, **dynamics}}
    steps = (("brush_canvas",), ("pen_stroke", options, stroke_points(), pen), ("record", "pen"),
             ("brush_restore",), ("close_throwaway_document",))
    return ScenarioSpec(f"pen:{name}", "pen_probe", "run", True, steps)


def pen_specs() -> list[ScenarioSpec]:
    full = [1.0] * N
    pressure = {"pressures": ramp(0.0, 1.0)}
    tilt = {"pressures": full, "tilts": [[round(t), 0] for t in ramp(0, 90)]}
    rotation = {"pressures": full, "rotations": [round(r) for r in ramp(0, 180)]}
    held = lambda **v: {"pressures": [v.get("p", 1.0)] * N, "tilts": [list(v.get("tilt", (0, 0)))] * N, "rotations": [v.get("r", 0)] * N}
    smoothing_on = {"smoothing": True, "smoothingValue": 26, "smoothingCatchupAtEnd": False}
    step = {"pressures": [0.25 if x < 200 else 1.0 for x, _ in stroke_points()]}
    specs = [_spec(f"size=pressure:held={p}", _tip(size={"control": 2}), held(p=p)) for p in (0.1, 0.25, 0.5, 0.75, 0.9, 1000 / 1024, 1.0)]
    specs += [_spec(f"opacity=pressure:held={p}", {"usePaintDynamics": True, "opVr": _variation(control=2), "prVr": _variation()}, held(p=p))
              for p in (0.1, 0.25, 0.5, 0.75, 0.9)]
    specs += [_spec(f"size=tilt:held={t}", _tip(size={"control": 3}), held(tilt=(t, 0))) for t in (30, 60, 90)]
    specs += [_spec(f"roundness=tilt:held={tx},{ty}", _tip(roundness={"control": 3}), held(tilt=(tx, ty)))
              for tx, ty in ((30, 0), (60, 0), (90, 0), (0, 45), (45, 45))]
    specs += [_spec(f"angle=tilt:roundness=50:held={tx},{ty}", _tip(angle={"control": 3}), held(tilt=(tx, ty)), {"roundness": 50})
              for tx, ty in ((45, 0), (0, 45), (45, 45), (-45, 45))]
    specs += [_spec(f"angle=rotation:roundness=50:held={r}", _tip(angle={"control": 8}), held(r=r), {"roundness": 50}) for r in (0, 45, 90, 135)]
    specs += [_spec(f"size=tilt:held={tx},{ty}", _tip(size={"control": 3}), held(tilt=(tx, ty)))
              for tx, ty in [(t, 0) for t in (10, 20, 40, 50, 70, 80)] + [(0, t) for t in (30, 60, 90)] + [(-30, 0), (30, 30)]]
    specs += [_spec(f"angle=rotation:roundness=20:held={r}", _tip(angle={"control": 8}), held(r=r), {"roundness": 20}) for r in (30, 150)]
    specs += [_spec(f"angle=tilt:roundness=20:held={tx},{ty}", _tip(angle={"control": 3}), held(tilt=(tx, ty)), {"roundness": 20})
              for tx, ty in ((30, 30), (-30, 30), (30, -30))]
    specs += [_spec(f"size=tilt:pressure={p}:held={t},0", _tip(size={"control": 3}), held(p=p, tilt=(t, 0)))
              for p in (1000 / 1024, 0.5) for t in (0, 30, 60)]
    floor0 = {**_tip(roundness={"control": 3}), "minimumRoundness": {"_unit": "percentUnit", "_value": 0}}
    specs += [_spec(f"roundness=tilt:minimum=0:size=101:held={t},0", floor0, held(tilt=(t, 0)), {"size_px": 101}) for t in (0, 20, 40, 60, 80)]
    specs += [_spec("size=pressure:step:smoothing=26", _tip(size={"control": 2}), step, smoothing=smoothing_on),
              _spec("size=pressure:step", _tip(size={"control": 2}), step),
              _spec("size=off:smoothing=26", _tip(), pressure, smoothing=smoothing_on)]
    return specs + [
        _spec("size=pressure", _tip(size={"control": 2}), pressure),
        _spec("size=pressure:minimum=50", _tip(size={"control": 2, "minimum": 50}), pressure),
        _spec("opacity=pressure", {"usePaintDynamics": True, "opVr": _variation(control=2), "prVr": _variation()}, pressure),
        _spec("size=tilt", _tip(size={"control": 3}), tilt),
        _spec("roundness=tilt", _tip(roundness={"control": 3}), tilt),
        _spec("angle=tilt:roundness=50", _tip(angle={"control": 3}), tilt, {"roundness": 50}),
        _spec("angle=rotation:roundness=50", _tip(angle={"control": 8}), rotation, {"roundness": 50}),
        _spec("size=off", _tip(), pressure),
    ]


def column_centres(alpha: Any) -> list[float | None]:
    """The mean row of each column's painted pixels (alpha over 127), None where none are: at a
    stroke's ends, which way a turned tip leans."""
    import numpy as np

    painted = np.asarray(alpha) > 127
    rows = np.arange(painted.shape[0])[:, None]
    count = painted.sum(axis=0)
    centre = (painted * rows).sum(axis=0) / np.maximum(count, 1)
    return [round(float(c), 2) if n else None for c, n in zip(centre, count)]


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        observations = row.get("observations") or {}
        kind = "pen" if "pen" in observations else "brush"
        if row["item_id"].startswith("pen:") and row.get("status") == "ok" and kind in observations:
            latest[row["item_id"]] = {"item_id": row["item_id"], **observations[kind]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.pen_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "pen-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} pen probe rows written")
        return
    specs = pen_specs()
    with (args.dataset / "pen-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} pen probe specs")


if __name__ == "__main__":
    main()
