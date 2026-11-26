"""The smudge probe: how far Photoshop's Smudge tool carries colour, and how it fades.

The image is the harness's own (400 x 300): white, with a black band at columns BAND. Each spec
sets the Smudge tool (a hard round tip of SIZE px, dynamics off) to one strength, spacing or
Finger Painting setting and strokes it once along row ROW from START, inside the band, out into
the white to END, by a scripted stroke path (ps_tools.stroke). What it leaves on the stroke's row,
and on the rows the tip covered, shows the colour the finger picked up and how each dab hands it
on: the trail's fall-off with distance against strength and spacing.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .families import ScenarioSpec

WIDTH, HEIGHT = 400, 300
BAND = (60, 100)  # black columns
ROW = 150
START, END = (80, ROW), (340, ROW)
SIZE = 21
ROWS = (ROW - SIZE // 2 - 2, ROW + SIZE // 2 + 3)  # the rows kept: the tip's height and a margin


def image() -> Any:
    from PIL import Image

    grey = np.full((HEIGHT, WIDTH), 255, np.uint8)
    grey[:, BAND[0]:BAND[1]] = 0
    return Image.fromarray(np.repeat(grey[..., None], 3, axis=2))


def images() -> dict[str, Any]:
    return {"smudge_band": image}


def measure(pixels: np.ndarray) -> dict[str, Any]:
    """The stroke's row and the rows the tip covered (one channel: the image is grey)."""
    grey = np.asarray(pixels)[..., 0].astype(int)
    return {"row": grey[ROW].tolist(), "rows": grey[ROWS[0]:ROWS[1]].tolist(), "rows_top": ROWS[0]}


FINGER_GREY = 128  # the foreground Finger Painting starts with: neither the band's black nor the white


def _spec(name: str, strength: int, spacing: int = 25, finger: bool = False) -> ScenarioSpec:
    options = {"size_px": SIZE, "strength": strength, "spacing": spacing, "finger_painting": finger,
               **({"foreground": FINGER_GREY} if finger else {})}
    steps = (("open_test_image", "smudge_band"), ("save_tool_state", "smudge"),
             ("smudge_stroke", options, [list(START), list(END)]), ("record", "smudge"),
             ("restore_tool_state",), ("close_throwaway_document",))
    return ScenarioSpec(f"smudge:{name}", "smudge_probe", "run", False, steps)


def smudge_specs() -> list[ScenarioSpec]:
    specs = [_spec(f"strength={s}", s) for s in (10, 25, 50, 75, 90, 100)]
    specs += [_spec(f"strength=50:spacing={p}", 50, p) for p in (5, 10, 50, 100)]
    specs += [_spec(f"strength={s}:finger", s, finger=True) for s in (50, 90)]
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("smudge:") and row.get("status") == "ok" and "smudge" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["smudge"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.smudge_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "smudge-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} smudge probe rows written")
        return
    specs = smudge_specs()
    with (args.dataset / "smudge-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} smudge probe specs")


if __name__ == "__main__":
    main()
