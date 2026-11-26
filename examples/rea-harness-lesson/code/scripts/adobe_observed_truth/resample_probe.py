"""The resample probe: Photoshop's Image Size resampling methods, read as impulse responses.

The image is the harness's own 64 x 64 black field with single white pixels 16 apart (IMPULSES),
far enough apart that each one's image after Image Size is the method's own 2D response at its
place. Each spec resizes the image to one size with one method (Document.resizeImage) and records
the result's grey bytes.
"""

from __future__ import annotations

import base64
from typing import Any

import numpy as np

from .families import ScenarioSpec

SIZE = 64
IMPULSES = [(x, y) for y in (7, 23, 40, 56) for x in (8, 25, 41, 57)]  # uneven, so phases differ
METHODS = ("NEARESTNEIGHBOR", "BILINEAR", "BICUBIC", "BICUBICSMOOTHER", "BICUBICSHARPER", "BICUBICAUTOMATIC")
SIZES = (128, 192, 88, 32, 24)


def image() -> np.ndarray:
    grey = np.zeros((SIZE, SIZE), dtype=np.uint8)
    for x, y in IMPULSES:
        grey[y, x] = 255
    return np.repeat(grey[..., None], 3, axis=2)


def images() -> dict[str, Any]:
    from PIL import Image

    return {"resample_impulses": lambda: Image.fromarray(image())}


def resize_js(size: int, method: str) -> str:
    return (f"app.activeDocument.resizeImage(UnitValue({size},'px'),UnitValue({size},'px'),72,ResampleMethod.{method});"
            "'null';")


def resample_specs() -> list[ScenarioSpec]:
    return [ScenarioSpec(f"resample:{method.lower()}:size={size}", "resample_probe", "run", False,
                         (("open_test_image", "resample_impulses"), ("resize_image", size, method), ("record", "resample"),
                          ("close_throwaway_document",)))
            for method in METHODS for size in SIZES]


def measure(pixels: np.ndarray) -> dict[str, Any]:
    grey = pixels[..., 0].astype(np.uint8)
    return {"shape": list(grey.shape), "grey": base64.b64encode(grey.tobytes()).decode()}


def grey_of(row: dict[str, Any]) -> np.ndarray:
    return np.frombuffer(base64.b64decode(row["grey"]), dtype=np.uint8).reshape(row["shape"])


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("resample:") and row.get("status") == "ok" and "resample" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["resample"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.resample_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "resample-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} resample probe rows written")
        return
    specs = resample_specs()
    with (args.dataset / "resample-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} resample probe specs")


if __name__ == "__main__":
    main()
