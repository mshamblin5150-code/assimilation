"""The texture and dual-tip probe: what a brush's Texture and Dual Brush do to a stroke.

Each spec paints one horizontal stroke on the brush canvas (brush_probe's, 400 x 300) along row
ROW with a hard round tip (SIZE px, spacing 5%, dynamics off) and keeps the painted layer's
alpha over the rows BAND.

- Texture: the harness's own pattern (OWN_PATTERN_NAME, PATTERN px square, column x holding grey
  pattern_grey(x)), defined for the spec and deleted after by name, each checked in Photoshop's
  pattern list (the preset manager's PttR entry), and picked as the brush's texture in the Brush
  Settings panel (runner pick_texture_pattern; a script cannot choose it). With the pattern tiled from the document's
  corner, each column of the stroke shows the texture's effect on one known grey, per mode, depth
  and invert.
- Dual Brush: a second hard round tip (DUAL_SIZE px by default) laid along the stroke at its own
  spacing, no scatter, one per step, combined by a blend mode.
- A plain stroke with neither, as the reference.
"""

from __future__ import annotations

import base64
from typing import Any

import numpy as np

from .brush_probe import ROW
from .families import ScenarioSpec

SIZE = 41
X0, X1 = 40, 360
BAND = (ROW - 30, ROW + 31)
PATTERN = 16
OWN_PATTERN_NAME = "observed-truth-pattern"
DUAL_SIZE = 9


def pattern_grey(x: int) -> int:
    return round(255 * (x % PATTERN) / (PATTERN - 1))


def pattern_image() -> Any:
    from PIL import Image

    row = np.array([pattern_grey(x) for x in range(PATTERN)], np.uint8)
    return Image.fromarray(np.repeat(np.repeat(row[None, :], PATTERN, 0)[..., None], 3, 2))


def measure(alpha: np.ndarray) -> dict[str, Any]:
    band = np.ascontiguousarray(np.asarray(alpha, np.uint8)[BAND[0]:BAND[1]])
    return {"alpha": base64.b64encode(band.tobytes()).decode("ascii"), "shape": list(band.shape), "top": BAND[0]}


def _spec(name: str, extra: dict[str, Any], textured: bool, **base: Any) -> ScenarioSpec:
    options = {"size_px": SIZE, "hardness": 100, "opacity": 100, "flow": 100, "spacing": 5, **base}
    stroke = ("tipmix_stroke", options, extra, [[X0, ROW], [X1, ROW]])
    define = (("define_own_pattern",),) if textured else ()
    pick = (("pick_texture_pattern",),) if textured else ()
    after = (("restore_brush_panel",), ("delete_own_pattern",)) if textured else ()
    steps = define + (("brush_canvas",),) + pick + (stroke, ("record", "tipmix"), ("brush_restore",)) + after + (("close_throwaway_document",),)
    return ScenarioSpec(f"tipmix:{name}", "tipmix_probe", "run", False, steps)


def _unit(value: float) -> dict[str, Any]:
    return {"_unit": "percentUnit", "_value": float(value)}


def _texture(mode: str, depth: int, invert: bool = False, each_tip: bool = False) -> dict[str, Any]:
    """Texture settings; the pattern itself is picked in the panel (pick_texture_pattern): the
    tool options carry no pattern key. textClickPoint is Texture Each Tip."""
    return {"useTexture": True, "textureBlendMode": {"_enum": "blendMode", "_value": mode}, "textureDepth": _unit(depth),
            "textureScale": _unit(100), "invertTexture": invert, "textureBrightness": 0, "textureContrast": 0, "textClickPoint": each_tip}


def _dual(mode: str, size: int = DUAL_SIZE, spacing: int = 100) -> dict[str, Any]:
    tip = {"_obj": "computedBrush", "diameter": {"_unit": "pixelsUnit", "_value": float(size)}, "hardness": _unit(100),
           "angle": {"_unit": "angleUnit", "_value": 0.0}, "roundness": _unit(100), "spacing": _unit(spacing)}
    return {"dualBrush": {"_obj": "dualBrush", "useDualBrush": True, "flip": False, "brush": tip,
                          "blendMode": {"_enum": "blendMode", "_value": mode}, "useScatter": False, "count": 1.0, "bothAxes": False}}


def tipmix_specs() -> list[ScenarioSpec]:
    specs = [_spec("plain", {}, False), _spec("plain:flow=30", {}, False, flow=30), _spec("plain:hardness=0", {}, False, hardness=0)]
    specs += [_spec(f"texture:{mode}:depth=100", _texture(mode, 100), True)
              for mode in ("height", "multiply", "subtract", "darken", "linearHeight", "colorBurn")]
    specs += [_spec(f"texture:{mode}:depth=50", _texture(mode, 50), True) for mode in ("height", "multiply", "subtract")]
    specs += [_spec("texture:multiply:depth=100:invert", _texture("multiply", 100, invert=True), True),
              _spec("texture:multiply:depth=100:each_tip", _texture("multiply", 100, each_tip=True), True),
              _spec("texture:multiply:depth=100:flow=50", _texture("multiply", 100), True, flow=50)]
    # Height modes on partial ink: thin dabs (flow 30) built up per tip, and a soft tip's edge.
    specs += [_spec(f"texture:{mode}:depth={d}:flow=30:each_tip", _texture(mode, d, each_tip=True), True, flow=30)
              for mode, d in (("height", 100), ("height", 50), ("linearHeight", 100), ("colorBurn", 100), ("multiply", 100))]
    specs += [_spec("texture:height:depth=100:hardness=0", _texture("height", 100), True, hardness=0)]
    specs += [_spec(f"dual:{mode}", _dual(mode), False) for mode in ("multiply", "darken", "colorBurn", "subtract", "hardMix")]
    specs += [_spec("dual:multiply:spacing=25", _dual("multiply", spacing=25), False),
              _spec("dual:multiply:size=21", _dual("multiply", size=21), False)]
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("tipmix:") and row.get("status") == "ok" and "tipmix" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["tipmix"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.tipmix_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "tipmix-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} tipmix probe rows written")
        return
    specs = tipmix_specs()
    with (args.dataset / "tipmix-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} tipmix probe specs")


if __name__ == "__main__":
    main()
