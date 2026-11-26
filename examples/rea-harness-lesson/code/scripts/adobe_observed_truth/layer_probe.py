"""The layer probe: Photoshop's layer blend modes measured as full 8-bit truth tables.

Two of the harness's own images are stacked: the base has grey x in column x and the top grey y
in row y (256 x 256), so the composite read back at (x, y) is mode(base x, top y) for every pair
of levels. For the modes that mix channels (hue, saturation, colour, luminosity, darker and
lighter colour) the pair is two 64 x 64 images of fixed pseudo-random colours. Each spec opens
the base, adds the top as a layer with one blend mode and opacity, and records the composite.
"""

from __future__ import annotations

import base64
from typing import Any

import numpy as np

from .families import ScenarioSpec

SEPARABLE = ("normal", "darken", "multiply", "colorBurn", "linearBurn", "lighten", "screen", "colorDodge",
             "linearDodge", "overlay", "softLight", "hardLight", "vividLight", "linearLight", "pinLight", "hardMix",
             "difference", "exclusion", "blendSubtraction", "blendDivide")
MIXING = ("darkerColor", "lighterColor", "hue", "saturation", "color", "luminosity")
COLOUR_SIZE = 64


def images() -> dict[str, Any]:
    """The probe images (PIL), by the name the runner opens them under."""
    from PIL import Image

    levels = np.arange(256, dtype=np.uint8)
    grey_base = np.repeat(np.tile(levels[None, :], (256, 1))[..., None], 3, axis=2)
    grey_top = np.repeat(np.tile(levels[:, None], (1, 256))[..., None], 3, axis=2)
    rng = np.random.default_rng(20261125)
    colour_base = rng.integers(0, 256, (COLOUR_SIZE, COLOUR_SIZE, 3), dtype=np.uint8)
    colour_top = rng.integers(0, 256, (COLOUR_SIZE, COLOUR_SIZE, 3), dtype=np.uint8)
    arrays = {"blend_grey_base": grey_base, "blend_grey_top": grey_top,
              "blend_colour_base": colour_base, "blend_colour_top": colour_top}
    return {name: (lambda a=a: Image.fromarray(a)) for name, a in arrays.items()}


def colour_pair() -> tuple[np.ndarray, np.ndarray]:
    """The colour base and top as arrays (as the probe drew them)."""
    made = images()
    return np.asarray(made["blend_colour_base"]()), np.asarray(made["blend_colour_top"]())


def measure(pixels: np.ndarray, kind: str) -> dict[str, Any]:
    """The composite: for grey, one channel (all three equal) as base64 bytes, rows = top level,
    columns = base level; for colour, the three channels' bytes."""
    rgb = pixels[..., :3]
    if kind == "grey":
        same = bool((rgb[..., 0] == rgb[..., 1]).all() and (rgb[..., 1] == rgb[..., 2]).all())
        return {"table": base64.b64encode(rgb[..., 0].astype(np.uint8).tobytes()).decode(), "channels_equal": same}
    return {"rgb": base64.b64encode(rgb.astype(np.uint8).tobytes()).decode(), "shape": list(rgb.shape)}


def table(row: dict[str, Any]) -> np.ndarray:
    """A recorded composite back as an array."""
    if "table" in row:
        return np.frombuffer(base64.b64decode(row["table"]), dtype=np.uint8).reshape(256, 256)
    return np.frombuffer(base64.b64decode(row["rgb"]), dtype=np.uint8).reshape(row["shape"])


def _spec(item_id: str, kind: str, mode: str, opacity: int) -> ScenarioSpec:
    steps = (
        ("open_test_image", f"blend_{kind}_base"),
        ("blend_layer", f"blend_{kind}_top", mode, opacity),
        ("record", "blend"),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(item_id, "layer_probe", "run", False, steps)


def layer_specs() -> list[ScenarioSpec]:
    specs = [_spec(f"blend:grey:{mode}", "grey", mode, 100) for mode in SEPARABLE]
    specs += [_spec(f"blend:grey:{mode}:opacity=50", "grey", mode, 50) for mode in ("normal", "multiply", "screen")]
    specs += [_spec(f"blend:colour:{mode}", "colour", mode, 100) for mode in SEPARABLE + MIXING]
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("blend:") and row.get("status") == "ok" and "blend" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["blend"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.layer_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "blend-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} blend probe rows written")
        return
    specs = layer_specs()
    with (args.dataset / "blend-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} layer probe specs")


if __name__ == "__main__":
    main()
