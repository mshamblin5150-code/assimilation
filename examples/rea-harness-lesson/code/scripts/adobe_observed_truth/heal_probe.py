"""The healing probe: what Photoshop's Spot Healing Brush puts over a blemish on a smooth image.

The images are the harness's own (WIDTH x HEIGHT): a smooth base with a black dot of radius DOT
at CENTRE. The base is a linear ramp (any smooth fill restores it), a bowl (grey rising with the
square of the distance from the centre, so a harmonic fill from the edge of the healed area
misses its curve while a copied patch blended by its gradients keeps it), or vertical stripes (a
texture, which a fill would blur and a copy would keep). Each spec sets the Spot Healing Brush
(a hard round tip, one type: Content-Aware CntW, Proximity Match PrxM, Create Texture CrtT) and
paints one dab on the dot by a stroke-path event naming the tool (ps_tools.stroke_with; the
Healing Brush itself needs an Alt-click source, which a script cannot give). The PATCH-wide square
round the dot is kept before and after.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .families import ScenarioSpec

WIDTH, HEIGHT = 200, 150
CENTRE = (100, 75)  # the dot's pixel (its centre at the pixel's centre)
DOT = 4.0
PATCH = 30  # half-width of the square kept round the dot
IMAGES = ("heal_ramp", "heal_bowl", "heal_stripes")
TYPES = {"content_aware": "CntW", "proximity": "PrxM", "texture": "CrtT"}
STRIPE_PERIOD = 12


def base(name: str) -> np.ndarray:
    """The smooth image under the dot (float grey)."""
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH] + 0.5
    if name == "heal_ramp":
        return 60 + 0.6 * xx
    if name == "heal_bowl":
        return np.minimum(255.0, 40 + 0.05 * ((xx - CENTRE[0] - 0.5) ** 2 + (yy - CENTRE[1] - 0.5) ** 2))
    if name == "heal_stripes":
        return 128 + 60 * np.sin(2 * math.pi * xx / STRIPE_PERIOD)
    raise ValueError(f"no healing image {name!r}")


def image(name: str) -> Any:
    from PIL import Image

    grey = base(name)
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH] + 0.5
    grey[(xx - CENTRE[0] - 0.5) ** 2 + (yy - CENTRE[1] - 0.5) ** 2 <= DOT ** 2] = 0
    return Image.fromarray(np.repeat(np.round(grey).astype(np.uint8)[..., None], 3, axis=2))


def images() -> dict[str, Any]:
    return {name: (lambda n=name: image(n)) for name in IMAGES}


def patch(pixels: np.ndarray) -> list[list[int]]:
    """The square round the dot (one channel: the images are grey)."""
    x, y = CENTRE
    return np.asarray(pixels)[y - PATCH:y + PATCH + 1, x - PATCH:x + PATCH + 1, 0].astype(int).tolist()


def _spec(name: str, image_name: str, kind: str, size: int, repeat: str = "") -> ScenarioSpec:
    options = {"size_px": size, "type": TYPES[kind]}
    points = [list(CENTRE), [CENTRE[0] + 1, CENTRE[1]]]
    steps = (("open_test_image", image_name), ("save_tool_state", "spot_healing"), ("spot_heal", options, points),
             ("record", "heal"), ("restore_tool_state",), ("close_throwaway_document",))
    return ScenarioSpec(f"heal:{name}:{kind}:size={size}{repeat}", "heal_probe", "run", False, steps)


def heal_specs() -> list[ScenarioSpec]:
    specs = [_spec(img.removeprefix("heal_"), img, kind, 21) for img in IMAGES for kind in TYPES]
    specs += [_spec(img.removeprefix("heal_"), img, kind, 31) for img in ("heal_ramp", "heal_bowl") for kind in ("content_aware", "proximity")]
    specs += [_spec("bowl", "heal_bowl", "content_aware", 21, ":repeat"), _spec("stripes", "heal_stripes", "content_aware", 21, ":repeat")]
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("heal:") and row.get("status") == "ok" and "heal" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["heal"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.heal_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "heal-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} healing probe rows written")
        return
    specs = heal_specs()
    with (args.dataset / "heal-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} healing probe specs")


if __name__ == "__main__":
    main()
