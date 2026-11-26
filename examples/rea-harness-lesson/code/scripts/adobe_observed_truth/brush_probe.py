"""The brush probe: Photoshop's brush engine measured from scripted dabs and strokes.

Each spec paints black with a plain round brush (dynamics off) on an empty layer of a 400x300
throwaway document, changing one setting from size 21, hardness 100, opacity 100, flow 100,
spacing 25, and keeps numbers from the painted layer's transparency (measure()):

- a dab (one anchor): its falloff from the centre, at every hardness and across sizes, and at
  the smallest sizes where anti-aliasing decides the dab;
- a stroke (two anchors along ROW): its transparency along the centre line, where the dabs land
  (spacing, for a hard and a soft tip), across the line, and its level in the middle (flow and
  opacity, each alone: flow builds up per dab, opacity caps the stroke).

Strokes are scripted (a work path stroked with the brush), so pen pressure and smoothing are not
exercised; pressure needs pen input of its own. The runner brings Photoshop to the front first,
as tool selection by script is refused in the background (2026-11-25), and the brush options and
colours are written back afterwards (brush_restore).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from . import ps_pixels as px
from .families import ScenarioSpec

WIDTH, HEIGHT = 400, 300
CENTRE = (200, 150)
ROW = 150
STROKE = [[40, ROW], [360, ROW]]
BASE = {"size_px": 21, "hardness": 100, "opacity": 100, "flow": 100, "spacing": 25}
# The harness's own sampled tip, drawn on a white 64x48 canvas: (left, top, right, bottom, grey), in
# order. Black body, a mid-grey band on its left, a white hole near its top right: no symmetry,
# so scaling, turning and flipping all show. Photoshop crops a tip to its non-white content.
OWN_TIP_CANVAS = (64, 48)
OWN_TIP_BOXES = ((8, 8, 56, 40, 0), (8, 8, 20, 40, 128), (44, 10, 52, 18, 255))
# Single black pixels at uneven spacing (their places fall at every phase of a scaled grid), the
# corner ones fixing the tip's bounds to 48 x 32: each scaled dab shows the resampling filter's
# impulse response at many phases.
IMPULSE_XS = (8, 13, 19, 24, 30, 37, 43, 50, 55)
IMPULSE_YS = (8, 15, 21, 28, 34, 39)
OWN_TIPS = {
    "blocks": OWN_TIP_BOXES,
    "impulses": tuple((x, y, x + 1, y + 1, 0) for y in IMPULSE_YS for x in IMPULSE_XS),
}
OWN_TIP_NAME = "observed-truth-tip"


def _spec(item_id: str, options: dict[str, int], points: list[list[int]]) -> ScenarioSpec:
    steps = (
        ("brush_canvas",),
        ("brush_stroke", {**BASE, **options}, points),
        ("record", "brush"),
        ("brush_restore",),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(item_id, "brush_probe", "run", False, steps)


def brush_specs() -> list[ScenarioSpec]:
    """Every probe, one setting changed at a time."""
    specs = [_spec(f"brush:dab:size={size}:hardness={hardness}", {"size_px": size, "hardness": hardness}, [list(CENTRE)])
             for size in (9, 21, 99) for hardness in (0, 10, 25, 50, 75, 90, 100)]
    specs += [_spec(f"brush:dab:size={size}:hardness=100", {"size_px": size}, [list(CENTRE)]) for size in (1, 2, 3, 5)]
    specs += [_spec(f"brush:stroke:size=21:hardness={hardness}:spacing={spacing}",
                    {"hardness": hardness, "spacing": spacing}, STROKE)
              for hardness in (0, 100) for spacing in (1, 10, 25, 50, 100, 150, 200, 400)]
    specs += [_spec(f"brush:stroke:size=21:flow={flow}", {"flow": flow}, STROKE) for flow in (5, 10, 25, 50)]
    specs += [_spec(f"brush:stroke:size=21:opacity={opacity}", {"opacity": opacity}, STROKE) for opacity in (10, 25, 50)]
    specs += [_spec("brush:stroke:size=21:flow=25:opacity=50", {"flow": 25, "opacity": 50}, STROKE)]
    # Simulated pen pressure (Photoshop tapers it along the stroke) through the options bar's
    # switches: pressure sets size, opacity, or both.
    specs += [_spec(f"brush:pressure:size={size}:controls={controls}", {"size_px": size, "pressure": controls}, STROKE)
              for size in (21, 99) for controls in ("size", "opacity", "both")]
    specs += [_spec("brush:pressure:size=21:hardness=0:controls=opacity", {"hardness": 0, "pressure": "opacity"}, STROKE)]
    return specs


def _variation(control: int = 0, jitter: int = 0, minimum: int = 0, steps: int = 25) -> dict[str, Any]:
    """One dynamics variation as the brush options hold it: control (0 off, 1 fade, 2 pen
    pressure, 3 pen tilt, 4 stylus wheel, higher: rotation and direction sources), fade steps,
    jitter and minimum (per cent)."""
    return {"_obj": "brVr", "bVTy": control, "fStp": steps,
            "jitter": {"_unit": "percentUnit", "_value": jitter}, "minimum": {"_unit": "percentUnit", "_value": minimum}}


def _pose(pressure: int | None = None, tilt_x: int | None = None, tilt_y: int | None = None,
          angle: int | None = None) -> dict[str, Any]:
    """A brush pose: fixed pen values that override the stylus, so a scripted stroke carries them."""
    pose: dict[str, Any] = {"useBrushPose": True}
    for name, value in (("Pressure", pressure), ("TiltX", tilt_x), ("TiltY", tilt_y), ("Angle", angle)):
        pose[f"overridePose{name}"] = value is not None
        if value is not None:
            pose[f"brushPose{name}"] = {"_unit": "percentUnit", "_value": value} if name == "Pressure" else value
    return pose


DYNAMICS_BASE = {"spacing": 10}


def dynamics_specs() -> list[ScenarioSpec]:
    """Dynamics and pose probes: one setting changed at a time from size 21, hardness 100,
    spacing 10 (153 dabs along the stroke), each dab read from the tip kernels' buffers."""
    tip = lambda **v: {"useTipDynamics": True, "szVr": _variation(**v.pop("size", {})),
                       "angleDynamics": _variation(**v.pop("angle", {})),
                       "roundnessDynamics": _variation(**v.pop("roundness", {})), **v}
    probes: dict[str, dict[str, Any]] = {
        "size:jitter=100": {"dynamics": tip(size={"jitter": 100})},
        "size:jitter=50": {"dynamics": tip(size={"jitter": 50})},
        "size:jitter=100:minimum=50": {"dynamics": tip(size={"jitter": 100, "minimum": 50})},
        "size:fade=25": {"dynamics": tip(size={"control": 1})},
        "size:fade=25:minimum=50": {"dynamics": tip(size={"control": 1, "minimum": 50})},
        "angle:jitter=100:roundness=50": {"roundness": 50, "dynamics": tip(angle={"jitter": 100})},
        "roundness:jitter=100:minimum=25": {"dynamics": tip(roundness={"jitter": 100}, minimumRoundness={"_unit": "percentUnit", "_value": 25})},
        "scatter=100": {"dynamics": {"useScatter": True, "bothAxes": False, "scatterDynamics": _variation(jitter=100), "count": 1, "countDynamics": _variation()}},
        "scatter=300:both_axes": {"dynamics": {"useScatter": True, "bothAxes": True, "scatterDynamics": _variation(jitter=300), "count": 1, "countDynamics": _variation()}},
        "count=3": {"dynamics": {"useScatter": True, "bothAxes": False, "scatterDynamics": _variation(), "count": 3, "countDynamics": _variation()}},
        "count=4:count_jitter=100": {"dynamics": {"useScatter": True, "bothAxes": False, "scatterDynamics": _variation(), "count": 4, "countDynamics": _variation(jitter=100)}},
        "opacity:jitter=100": {"dynamics": {"usePaintDynamics": True, "opVr": _variation(jitter=100), "prVr": _variation()}},
        "flow:jitter=100": {"dynamics": {"usePaintDynamics": True, "opVr": _variation(), "prVr": _variation(jitter=100)}},
    }
    for pressure in (25, 50, 75, 100):
        probes[f"pose:pressure={pressure}:size=pressure"] = {"dynamics": {**tip(size={"control": 2}), **_pose(pressure=pressure)}}
        probes[f"pose:pressure={pressure}:size=pressure:minimum=50"] = {"dynamics": {**tip(size={"control": 2, "minimum": 50}), **_pose(pressure=pressure)}}
        probes[f"pose:pressure={pressure}:opacity=pressure"] = {"dynamics": {"usePaintDynamics": True, "opVr": _variation(control=2), "prVr": _variation(), **_pose(pressure=pressure)}}
    for tilt_x, tilt_y in ((0, 0), (30, 0), (60, 0), (90, 0), (0, 45), (45, 45), (-45, 0)):
        pose = _pose(tilt_x=tilt_x, tilt_y=tilt_y)
        probes[f"pose:tilt={tilt_x},{tilt_y}:angle=tilt:roundness=50"] = {"roundness": 50, "dynamics": {**tip(angle={"control": 3}), **pose}}
        probes[f"pose:tilt={tilt_x},{tilt_y}:roundness=tilt"] = {"dynamics": {**tip(roundness={"control": 3}), **pose}}
        probes[f"pose:tilt={tilt_x},{tilt_y}:size=tilt"] = {"dynamics": {**tip(size={"control": 3}), **pose}}
    for control in (4, 5, 6, 7, 8):
        for angle in (0, 45, 90):
            probes[f"pose:angle={angle}:angle_control={control}:roundness=50"] = {
                "roundness": 50, "dynamics": {**tip(angle={"control": control}), **_pose(angle=angle)}}
    return [_spec(f"brush:dyn:{name}", {**DYNAMICS_BASE, **options}, STROKE) for name, options in probes.items()]


def tip_specs() -> list[ScenarioSpec]:
    """The harness's own sampled tips (OWN_TIPS, defined as a preset for the spec and deleted after):
    single dabs at their own size (48), scaled down and up, turned and squashed, and two strokes."""
    def spec(name: str, options: dict[str, Any], points: list[list[int]], tip: str = "blocks") -> ScenarioSpec:
        steps = (
            ("brush_canvas",),
            ("define_own_tip", tip),
            ("brush_stroke", {**BASE, "sampled": True, **options}, points),
            ("record", "brush"),
            ("brush_restore",),
            ("delete_own_tip",),
            ("close_throwaway_document",),
        )
        prefix = "brush:tip:" if tip == "blocks" else f"brush:tip:{tip}:"
        return ScenarioSpec(f"{prefix}{name}", "brush_probe", "run", False, steps)

    specs = [spec(f"dab:size={size}", {"size_px": size}, [list(CENTRE)]) for size in (48, 24, 12, 96, 37, 61)]
    specs += [spec(f"dab:size=48:angle={angle}", {"size_px": 48, "angle": angle}, [list(CENTRE)]) for angle in (30, 90, -45)]
    specs += [spec(f"dab:size=48:roundness={r}", {"size_px": 48, "roundness": r}, [list(CENTRE)]) for r in (50, 25)]
    specs += [spec(f"stroke:size=48:spacing={sp}", {"size_px": 48, "spacing": sp}, STROKE) for sp in (25, 100)]
    specs += [spec(f"dab:size={size}", {"size_px": size}, [list(CENTRE)], "impulses")
              for size in (48, 24, 36, 12, 61, 96, 30)]
    specs += [spec(f"dab:size=48:angle={angle}", {"size_px": 48, "angle": angle}, [list(CENTRE)], "impulses") for angle in (30, 90)]
    specs += [spec("dab:size=48:roundness=50", {"size_px": 48, "roundness": 50}, [list(CENTRE)], "impulses")]
    return specs


def _peaks(line: np.ndarray) -> list[int]:
    """Where the line has a local maximum (the middle of a flat top): a dab's centre on a stroke."""
    peaks, x, n = [], 1, len(line)
    while x < n - 1:
        end = x
        while end + 1 < n and line[end + 1] == line[x]:
            end += 1
        if line[x] > 0 and line[x] > line[x - 1] and (end + 1 >= n or line[x] > line[end + 1]):
            peaks.append((x + end) // 2)
        x = end + 1
    return peaks


def measure(alpha: np.ndarray, points: list[Any], size: int) -> dict[str, Any]:
    """Numbers from a painted layer's transparency: a dab's falloff (one point), or a stroke's
    profile along and across its centre line, its dab centres and its level in the middle."""
    x0, y0 = (int(v) for v in points[0])
    if len(points) == 1:
        return {"radial": px.radial_profile(alpha, (x0, y0), range(size // 2 + 4)),
                "zero_radius": px.zero_radius(alpha, (x0, y0)),
                "bounds": px.nonzero_bounds(alpha)}
    x1 = int(points[-1][0])
    line = alpha[y0, :].astype(int)
    third = (x1 - x0) // 3
    middle = (x0 + x1) // 2
    return {"centreline": line.tolist(),
            "cross_section": alpha[:, middle].astype(int).tolist(),
            "widths": (alpha > 127).sum(axis=0).astype(int).tolist(),  # painted rows per column
            "dab_centres": _peaks(line),
            "plateau": round(float(np.mean(line[x0 + third:x1 - third + 1]))),
            "bounds": px.nonzero_bounds(alpha)}


def published_rows(results: Any) -> list[dict[str, Any]]:
    """Each brush probe's numbers from its latest successful run (results.jsonl rows): what was
    painted, as numbers from the harness's own strokes; nothing else of the run is carried."""
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("brush:") and row.get("status") == "ok" and "brush" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["brush"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.brush_probe --dataset <dir>

    Write brush-families.jsonl; run it with runner_photoshop --specs brush-families.jsonl.
    With --results <sweep>/results.jsonl, write brush-probe.jsonl: each probe's numbers."""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--dynamics", action="store_true", help="write brush-dynamics-families.jsonl instead")
    parser.add_argument("--tips", action="store_true", help="write brush-tip-families.jsonl instead")
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines()
                              if line.strip())
        with (args.dataset / "brush-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} brush probe rows written to brush-probe.jsonl")
        return
    specs, name = ((dynamics_specs(), "brush-dynamics-families.jsonl") if args.dynamics else
                   (tip_specs(), "brush-tip-families.jsonl") if args.tips else (brush_specs(), "brush-families.jsonl"))
    with (args.dataset / name).open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} brush probe specs")


if __name__ == "__main__":
    main()
