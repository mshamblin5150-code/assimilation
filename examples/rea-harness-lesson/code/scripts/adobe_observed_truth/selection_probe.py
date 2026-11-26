"""The selection probe: Magic Wand, Paint Bucket and Feather measured on an image built for them.

The 400x300 image (selection_image) has: a grey ramp (column x is grey x, rows 0-39), a red ramp
(red x, green and blue 128, rows 40-79), a 16x16 grid of 12-pixel cells whose red is 16 * column
and green 16 * row (blue 128), and, on a grey-200 field, two grey-100 patches with a wall between
them and two touching only at a corner. A wand click or bucket fill on a ramp shows the tolerance
rule and the anti-aliased edge; on the grid, which cells it takes shows how colour distance is
measured; on the patches, contiguity and which neighbours count. Feather is applied to a
rectangle and its edge read across. The Magic Wand and the bucket are applied by their recorded
events, so no tool is selected and no mouse input is sent.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .families import ScenarioSpec

WIDTH, HEIGHT = 400, 300
BANDS = {"grey": 20, "red": 60, "feather": 240}  # the row read across each band
GRID = {"left": 0, "top": 80, "cell": 12, "count": 16}
PATCHES = {"apart": ((229, 109), (289, 109)), "corner": ((219, 159), (239, 179))}
FEATHER_BOX = [320, 200, 380, 280]  # left, top, right, bottom
GRID_CENTRE = (GRID["left"] + 8 * GRID["cell"] + 6, GRID["top"] + 8 * GRID["cell"] + 6)


def selection_image() -> np.ndarray:
    """The probe image, RGB uint8."""
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    ramp = np.minimum(np.arange(WIDTH), 255).astype(np.uint8)
    image[0:40] = ramp[None, :, None]
    image[40:80, :, 0] = ramp
    image[40:80, :, 1:] = 128
    cell, top, left = GRID["cell"], GRID["top"], GRID["left"]
    for j in range(GRID["count"]):
        for i in range(GRID["count"]):
            image[top + j * cell:top + (j + 1) * cell, left + i * cell:left + (i + 1) * cell] = (16 * i, 16 * j, 128)
    image[80:300, 200:400] = 200
    image[90:130, 210:250] = 100  # two alike patches with a grey-200 wall between them
    image[90:130, 270:310] = 100
    image[150:170, 210:230] = 100  # two squares touching only at a corner
    image[170:190, 230:250] = 100
    return image


def _spec(item_id: str, action: tuple, record: str) -> ScenarioSpec:
    steps: tuple = (("open_test_image", "selection"), action, ("record", record), ("close_throwaway_document",))
    if record == "bucket":  # the bucket paints the foreground colour and keeps its options: written back after
        steps = (steps[0], ("save_tool_state", "bucket"), action, ("record", record), ("restore_tool_state",),
                 ("close_throwaway_document",))
    return ScenarioSpec(item_id, "selection_probe", "run", False, steps)


def selection_specs() -> list[ScenarioSpec]:
    """Every probe: (wand_click x, y, tolerance, anti_alias, contiguous), bucket_click the same,
    feather_rect box, radius."""
    grey = (128, BANDS["grey"])
    specs = [_spec(f"wand:grey:tolerance={t}:anti_alias=false", ("wand_click", *grey, t, False, True), "selection")
             for t in (0, 1, 5, 10, 32, 64, 128)]
    specs += [_spec(f"wand:grey:tolerance={t}:anti_alias=true", ("wand_click", *grey, t, True, True), "selection")
              for t in (10, 32)]
    specs += [_spec(f"wand:red:tolerance={t}:anti_alias=false", ("wand_click", 128, BANDS["red"], t, False, True), "selection")
              for t in (*range(1, 13), 16, 32)]
    specs += [_spec(f"wand:grid:tolerance={t}:anti_alias=false", ("wand_click", *GRID_CENTRE, t, False, True), "selection")
              for t in (20, 40, 60)]
    seed = PATCHES["apart"][0]
    specs += [_spec(f"wand:apart:contiguous={str(c).lower()}", ("wand_click", *seed, 0, False, c), "selection")
              for c in (False, True)]
    specs += [_spec("wand:corner:contiguous=true", ("wand_click", *PATCHES["corner"][0], 0, False, True), "selection")]
    specs += [_spec(f"bucket:grey:tolerance={t}:anti_alias=true", ("bucket_click", *grey, t, True, True), "bucket")
              for t in (10, 32)]
    specs += [_spec(f"feather:radius={r}", ("feather_rect", FEATHER_BOX, r), "selection") for r in (1, 2, 5, 10, 25)]
    return specs


def measure_selection(mask: np.ndarray) -> dict[str, Any]:
    """A selection (or a bucket's coverage) as 0..255: read along each band's row, as each grid
    cell's mean, and at each patch's seed."""
    cell, top, left, count = GRID["cell"], GRID["top"], GRID["left"], GRID["count"]
    grid = [[round(float(mask[top + j * cell:top + (j + 1) * cell, left + i * cell:left + (i + 1) * cell].mean()))
             for i in range(count)] for j in range(count)]
    return {
        "rows": {name: mask[row].astype(int).tolist() for name, row in BANDS.items()},
        "grid": grid,
        "patches": {name: [int(mask[y, x]) for x, y in seeds] for name, seeds in PATCHES.items()},
    }


def published_rows(results: Any) -> list[dict[str, Any]]:
    """Each selection probe's measures from its latest successful run (results.jsonl rows):
    numbers from the harness's own image; nothing else of the run is carried."""
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        observed = row.get("observations") or {}
        measured = observed.get("selection") or observed.get("bucket")
        if row["item_id"].split(":")[0] in ("wand", "bucket", "feather") and row.get("status") == "ok" and measured:
            latest[row["item_id"]] = {"item_id": row["item_id"], **measured}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.selection_probe --dataset <dir>

    Write selection-families.jsonl; run it with runner_photoshop --specs selection-families.jsonl.
    With --results <sweep>/results.jsonl, write selection-probe.jsonl: each probe's measures."""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines()
                              if line.strip())
        with (args.dataset / "selection-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} selection probe rows written to selection-probe.jsonl")
        return
    specs = selection_specs()
    with (args.dataset / "selection-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} selection probe specs")


def bucket_coverage(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """How much of the red foreground the bucket laid on each pixel (0..255): the red channel's
    move toward 255 as a share of the way it had to go."""
    start = before[..., 0].astype(float)
    room = 255 - start
    moved = after[..., 0].astype(float) - start
    return np.round(np.where(room > 0, np.clip(moved / np.maximum(room, 1), 0, 1), 0) * 255).astype(np.uint8)


if __name__ == "__main__":
    main()
