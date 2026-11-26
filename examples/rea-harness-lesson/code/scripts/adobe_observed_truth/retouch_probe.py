"""The retouch probe: Dodge, Burn and Sponge measured as transfer curves, one dab at a time.

The probe image (ramp_image) is the harness's own: on a 400x300 canvas, the top half is a grey ramp
(column 72 + v holds grey v, v = 0..255) and the bottom half a saturation ramp of one hue (red
255, green and blue v: column 72 is pure red, column 327 white). One hard dab of size 400 at the
centre covers both measuring rows (75 and 225) across the whole ramp at full strength, so each
row read back is the tool's output for every input level at that exposure (or flow): its
transfer curve. Dynamics are off so pen pressure does not scale the exposure.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .families import ScenarioSpec

WIDTH, HEIGHT = 400, 300
RAMP_LEFT = 72
GREY_ROW, COLOUR_ROW = 75, 225
CENTRE = (200, 150)
DAB_SIZE = 400


def ramp_image() -> Any:
    """The probe image (a PIL image)."""
    from PIL import Image

    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    levels = np.clip(np.arange(WIDTH) - RAMP_LEFT, 0, 255).astype(np.uint8)
    image[: HEIGHT // 2, :, :] = levels[None, :, None]
    image[HEIGHT // 2:, :, 0] = 255
    image[HEIGHT // 2:, :, 1] = levels[None, :]
    image[HEIGHT // 2:, :, 2] = levels[None, :]
    return Image.fromarray(image)


def muted_image() -> Any:
    """The probe image with room to saturate: the same grey ramp on top; below it, column 72 + v
    holds the hue v * 360 / 256 at moderate saturation (each channel 128 + 48 cos(hue - 120 k))."""
    from PIL import Image

    image = np.array(ramp_image())
    hue = 2 * np.pi * np.clip(np.arange(WIDTH) - RAMP_LEFT, 0, 255) / 256
    for k in range(3):
        image[HEIGHT // 2:, :, k] = np.round(128 + 48 * np.cos(hue - 2 * np.pi * k / 3))[None, :].astype(np.uint8)
    return Image.fromarray(image)


def images() -> dict[str, Any]:
    return {"ramp": ramp_image, "ramp_muted": muted_image}


def measure(pixels: np.ndarray) -> dict[str, Any]:
    """The tool's output for every input level: the grey row (one channel; all three are kept
    when they differ) and the colour row's three channels."""
    columns = slice(RAMP_LEFT, RAMP_LEFT + 256)
    grey = pixels[GREY_ROW, columns, :3].astype(int)
    colour = pixels[COLOUR_ROW, columns, :3].astype(int)
    same = bool((grey[:, 0] == grey[:, 1]).all() and (grey[:, 1] == grey[:, 2]).all())
    return {"grey": grey[:, 0].tolist() if same else grey.T.tolist(), "grey_channels_equal": same,
            "colour": colour.T.tolist()}


def _spec(item_id: str, tool: str, options: dict[str, Any], image: str = "ramp") -> ScenarioSpec:
    steps = (
        ("open_test_image", image),
        ("save_tool_state", tool),
        ("retouch_dab", tool, {"size_px": DAB_SIZE, **options}, [list(CENTRE)]),
        ("record", "retouch"),
        ("restore_tool_state",),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(item_id, "retouch_probe", "run", False, steps)


def retouch_specs() -> list[ScenarioSpec]:
    specs = []
    for tool, prefix in (("dodge", "dodge"), ("burn", "burnIn")):
        for band, code in (("shadows", "S"), ("midtones", "M"), ("highlights", "H")):
            for exposure in (25, 50, 100):
                for legacy in (False, True):
                    specs.append(_spec(f"retouch:{tool}:{band}:exposure={exposure}" + (":legacy" if legacy else ""), tool,
                                       {"mode": f"{prefix}{code}", "strength": exposure, "legacy": legacy}))
    for mode in ("saturate", "desaturate"):
        for flow in (25, 50, 100):
            for vibrance in (False, True):
                specs.append(_spec(f"retouch:sponge:{mode}:flow={flow}" + (":vibrance" if vibrance else ""), "sponge",
                                   {"mode": mode, "strength": flow, "legacy": not vibrance}))
    for mode, vibrances in (("saturate", (False, True)), ("desaturate", (True,))):
        for flow in (25, 50, 100):
            for vibrance in vibrances:
                specs.append(_spec(f"retouch:sponge:{mode}:flow={flow}" + (":vibrance" if vibrance else "") + ":muted", "sponge",
                                   {"mode": mode, "strength": flow, "legacy": not vibrance}, "ramp_muted"))
    return specs


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("retouch:") and row.get("status") == "ok" and "retouch" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["retouch"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.retouch_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
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
        with (args.dataset / "retouch-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} retouch probe rows written")
        return
    specs = retouch_specs()
    with (args.dataset / "retouch-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} retouch probe specs")


if __name__ == "__main__":
    main()
