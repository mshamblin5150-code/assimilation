"""The channel probe: selections saved to and loaded from alpha channels, combined, modified and
counted, measured on the selection probe's image (selection_probe.selection_image).

Each spec runs a short list of selection operations (selection_ops_js) and records the final
selection as 8-bit coverage, with Photoshop's histogram pixel count for it:

- channels: a selection stored to an alpha channel and loaded back; two feathered bands crossing
  at right angles (one ramps across x, the other across y, so their overlap holds every pair of
  coverages) combined by loading the second with add, subtract or intersect;
- modify: Expand, Contract, Smooth, Border and Grow on hard and anti-aliased shapes;
- counting: anti-aliased and feathered selections, to compare Photoshop's pixel count with the
  coverage's sum and its 50% count.
"""

from __future__ import annotations

import base64
from typing import Any

import numpy as np

from .families import ScenarioSpec

COLUMN_BAND = ["rect", 120, 60, 280, 240, False, "replace"]  # feathered: ramps across x at its sides
ROW_BAND = ["rect", 60, 120, 340, 180, False, "replace"]  # feathered: ramps across y at its top and bottom
FEATHER = 30
COLOUR_RANGE_SAMPLES = {"grey128": [53.585, 0.0, 0.0], "red_band_160": [60.17, 18.73, 9.58], "grid_12_4": [47.5, 54.6, -6.2]}


AXES_SAMPLE = [50.0, 0.0, 0.0]  # mid grey
AXES_DIRECTIONS = {"L+": (1, 0, 0), "L-": (-1, 0, 0), "a+": (0, 1, 0), "a-": (0, -1, 0), "b+": (0, 0, 1), "b-": (0, 0, -1),
                   "a+b+": (0, 0.7071, 0.7071), "a+b-": (0, 0.7071, -0.7071), "L+a+": (0.7071, 0.7071, 0)}
AXES_STEP, AXES_COUNT, AXES_PATCH = 2.0, 30, 10  # Delta E per patch, patches per direction, patch px


def axes_image() -> Any:
    """Colour range's own test image (400 x 300): the sample colour everywhere, and one row of
    AXES_COUNT patches per direction in AXES_DIRECTIONS, stepping AXES_STEP further from the
    sample each (in Lab; out-of-gamut patches are clipped, so analyses read each patch's colour)."""
    from PIL import Image

    from .channel_model import lab_to_srgb

    image = np.zeros((300, 400, 3), float)
    image[:] = lab_to_srgb(np.array(AXES_SAMPLE))
    for row, direction in enumerate(AXES_DIRECTIONS.values()):
        for k in range(AXES_COUNT):
            lab = np.array(AXES_SAMPLE) + (k + 1) * AXES_STEP * np.array(direction)
            y, x = 20 + row * 30, 20 + k * 12
            image[y:y + AXES_PATCH, x:x + AXES_PATCH] = lab_to_srgb(lab)
    return Image.fromarray(np.clip(np.round(image), 0, 255).astype(np.uint8))


def images() -> dict[str, Any]:
    return {"color_axes": axes_image}


def _spec(item_id: str, ops: list[list[Any]], image: str = "selection") -> ScenarioSpec:
    steps = (("open_test_image", image), ("selection_ops", ops), ("record", "mask"), ("close_throwaway_document",))
    return ScenarioSpec(item_id, "channel_probe", "run", False, steps)


def channel_specs() -> list[ScenarioSpec]:
    bands = [COLUMN_BAND, ["feather", FEATHER], ["store", "a"], ROW_BAND, ["feather", FEATHER], ["store", "b"]]
    specs = [
        _spec("channel:band_a", bands + [["load", "a", "replace"]]),
        _spec("channel:band_b", bands + [["load", "b", "replace"]]),
        _spec("channel:round_trip", [["ellipse", 100, 50, 300, 250, True, "replace"], ["feather", 12], ["store", "a"],
                                     ["deselect"], ["load", "a", "replace"]]),
        _spec("channel:round_trip:before_store", [["ellipse", 100, 50, 300, 250, True, "replace"], ["feather", 12]]),
    ]
    specs += [_spec(f"channel:combine:{mode}", bands + [["load", "a", "replace"], ["load", "b", mode]])
              for mode in ("extend", "diminish", "intersect")]
    shapes = {"rect": ["rect", 150, 100, 250, 200, False, "replace"],
              "ellipse": ["ellipse", 140, 90, 260, 210, True, "replace"]}
    for name, shape in shapes.items():
        specs.append(_spec(f"modify:{name}:none", [shape]))
        for op, values in (("expand", (1, 5, 20)), ("contract", (1, 5, 20)), ("smooth", (1, 5, 20)), ("border", (2, 10))):
            specs += [_spec(f"modify:{name}:{op}={v}", [shape, [op, v]]) for v in values]
    specs += [_spec(f"modify:grow:tolerance={t}", [["rect", 100, 15, 110, 25, False, "replace"], ["grow", t, True]]) for t in (0, 8, 32)]
    for name, ops in (("rect", [shapes["rect"]]), ("ellipse:anti_alias", [shapes["ellipse"]]),
                      ("ellipse:hard", [["ellipse", 140, 90, 260, 210, False, "replace"]]),
                      ("rect:feather=10", [shapes["rect"], ["feather", 10]]), ("ellipse:feather=25", [shapes["ellipse"], ["feather", 25]])):
        specs.append(_spec(f"count:{name}", ops))
    # Colour Range around three of the image's own colours (as Lab, D50: grey 128; red band
    # x = 160 (160, 128, 128); grid cell (8, 8) (128, 128, 128) is grey too, so cell (12, 4)
    # (192, 64, 128)), at fuzziness 0 to 200.
    for name, lab in COLOUR_RANGE_SAMPLES.items():
        specs += [_spec(f"color_range:{name}:fuzziness={f}", [["color_range", f, lab, lab, 0]]) for f in (0, 10, 40, 100, 200)]
    specs += [_spec(f"color_range:axes:fuzziness={f}", [["color_range", f, AXES_SAMPLE, AXES_SAMPLE, 0]], "color_axes") for f in (20, 40, 100, 200)]
    return specs


def measure(mask: np.ndarray, histogram_pixels: int | None) -> dict[str, Any]:
    return {"mask": base64.b64encode(mask.astype(np.uint8).tobytes()).decode(), "shape": list(mask.shape),
            "coverage_sum": round(float(mask.sum()) / 255.0, 3), "count_half": int((mask >= 128).sum()),
            "count_any": int((mask > 0).sum()), "histogram_pixels": histogram_pixels}


def mask_of(row: dict[str, Any]) -> np.ndarray:
    return np.frombuffer(base64.b64decode(row["mask"]), dtype=np.uint8).reshape(row["shape"])


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row.get("status") == "ok" and "mask" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["mask"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.channel_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "channel-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} channel probe rows written")
        return
    specs = channel_specs()
    with (args.dataset / "channel-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} channel probe specs")


if __name__ == "__main__":
    main()
