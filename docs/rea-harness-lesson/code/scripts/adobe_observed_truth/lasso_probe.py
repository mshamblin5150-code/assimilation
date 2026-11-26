"""The magnetic lasso probe: how Photoshop's Magnetic Lasso pulls a hand-drawn outline onto an edge.

The images are the harness's own (400 x 300): a disc of radius RADIUS at CENTRE, dark (60) on a
light field (200), the same at low contrast (180 on 200), and the high-contrast disc with seeded
noise. Each spec selects the Magnetic Lasso with one option changed (detection width MgWd,
contrast MgEd), clicks every 10 degrees round a circle `offset` pixels outside (or inside) the
edge, closes with Enter, and records the selection as 8-bit coverage. Where the
outline lands, against the true edge, shows how far and how strongly the tool snaps.
"""

from __future__ import annotations

import base64
import math
from typing import Any

import numpy as np

from .families import ScenarioSpec

WIDTH, HEIGHT = 400, 300
CENTRE = (200.0, 150.0)
RADIUS = 80.0
STEPS = 36  # clicks round the circle, one every 10 degrees


SOFT_SIGMA = 3.0  # the refine-edge disc's edge blur, px


def soft_matte() -> np.ndarray:
    """The refine-edge image's true matte (0..1): the disc's coverage blurred by SOFT_SIGMA."""
    from math import erf

    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH] + 0.5
    d = np.hypot(xs - CENTRE[0], ys - CENTRE[1]) - RADIUS
    return 0.5 * (1 - np.vectorize(erf)(d / (SOFT_SIGMA * math.sqrt(2))))


RING = 92.0  # the two-edge image's outer, strong edge

# Refine Edge beyond a grey two-tone edge: each image lays a foreground over a background by the
# soft disc's matte, and each breaks one thing a grey two-tone edge cannot show.
REFINE_IMAGES = (
    "refine_colour",  # red over blue: the matte from colour, not only grey
    "refine_equiluminant",  # red over green of the same L* (and b*): invisible to lightness alone
    "refine_gradient",  # a dark disc over a background ramping 120 to 240 across: no single background
    "refine_texture",  # a disc of 4 px stripes (40, 110) over 220: a foreground of two colours
)


def refine_layers(name: str) -> tuple[np.ndarray, np.ndarray]:
    """The foreground and background (HEIGHT x WIDTH x 3, 0..255) a refine image is made of."""
    def flat(rgb: tuple[int, int, int]) -> np.ndarray:
        return np.broadcast_to(np.array(rgb, float), (HEIGHT, WIDTH, 3)).copy()

    xs = np.arange(WIDTH) + 0.5
    if name == "refine_colour":
        return flat((200, 40, 40)), flat((40, 70, 200))
    if name == "refine_equiluminant":
        return flat((220, 60, 70)), flat((40, 140, 60))
    if name == "refine_gradient":
        ramp = np.broadcast_to((120 + 120 * xs / WIDTH)[None, :, None], (HEIGHT, WIDTH, 3)).copy()
        return flat((40, 40, 40)), ramp
    if name == "refine_texture":
        stripes = np.where((np.arange(WIDTH) // 4) % 2 == 0, 40.0, 110.0)
        return np.broadcast_to(stripes[None, :, None], (HEIGHT, WIDTH, 3)).copy(), flat((220, 220, 220))
    raise ValueError(f"no refine image {name!r}")


def image(name: str) -> np.ndarray:
    if name in REFINE_IMAGES:
        foreground, background = refine_layers(name)
        alpha = soft_matte()[..., None]
        return np.round(alpha * foreground + (1 - alpha) * background).astype(np.uint8)
    if name == "lasso_two_edge":  # a weak edge (160 to 200) at RADIUS, a strong one (200 to 40) at RING
        ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH] + 0.5
        r = np.hypot(xs - CENTRE[0], ys - CENTRE[1])
        grey = np.where(r <= RADIUS, 160, np.where(r <= RING, 200, 40)).astype(np.uint8)
        return np.repeat(grey[..., None], 3, axis=2)
    if name == "refine_soft":
        grey = np.round(200 - 140 * soft_matte()).astype(np.uint8)
        return np.repeat(grey[..., None], 3, axis=2)
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH] + 0.5
    inside = (xs - CENTRE[0]) ** 2 + (ys - CENTRE[1]) ** 2 <= RADIUS ** 2
    fg, bg = (180, 200) if name == "lasso_low" else (60, 200)
    grey = np.where(inside, fg, bg).astype(float)
    if name == "lasso_noisy":
        grey += np.random.default_rng(20261126).normal(0, 20, grey.shape)
    grey = np.clip(np.round(grey), 0, 255).astype(np.uint8)
    return np.repeat(grey[..., None], 3, axis=2)


def images() -> dict[str, Any]:
    from PIL import Image

    return {name: (lambda n=name: Image.fromarray(image(n))) for name in ("lasso_high", "lasso_low", "lasso_noisy", "refine_soft", "lasso_two_edge", *REFINE_IMAGES)}


MOVE_STEPS = 180  # mouse positions round the circle when the tool lays its own anchors


def mouse_path(offset: float, steps: int = STEPS, arc: float = 1.0) -> list[list[float]]:
    """Document points round `arc` of the disc (1: all the way back to the start), `offset` px
    outside its edge (negative: inside)."""
    r = RADIUS + offset
    return [[CENTRE[0] + r * math.cos(2 * math.pi * arc * k / steps), CENTRE[1] + r * math.sin(2 * math.pi * arc * k / steps)]
            for k in range(steps + 1)]


def _spec(item_id: str, image_name: str, options: dict[str, Any], offset: float, mode: str = "clicks", arc: float = 1.0) -> ScenarioSpec:
    path = mouse_path(offset, MOVE_STEPS if mode == "moves" else STEPS, arc)
    steps = (("open_test_image", image_name), ("save_tool_state", "magnetic_lasso"),
             ("lasso_trace", options, path, mode), ("record", "mask"), ("restore_tool_state",),
             ("close_throwaway_document",))
    return ScenarioSpec(item_id, "lasso_probe", "run", True, steps)


def lasso_specs() -> list[ScenarioSpec]:
    specs = [_spec(f"lasso:high:offset={d}", "lasso_high", {}, d) for d in (0, 4, 8, 12, 16, -6)]
    specs += [_spec(f"lasso:high:width={w}:offset=8", "lasso_high", {"MgWd": w}, 8) for w in (3, 5, 20, 40)]
    specs += [_spec(f"lasso:low:contrast={c}:offset=4", "lasso_low", {"MgEd": c}, 4) for c in (1, 5, 10, 20)]
    specs += [_spec(f"lasso:noisy:offset={d}", "lasso_noisy", {}, d) for d in (0, 8)]
    # One click, then the mouse moved round the circle: the tool lays its own anchors.
    specs += [_spec(f"lasso:moves:high:offset={d}", "lasso_high", {}, d, "moves") for d in (0, 4, 8, 12, 16)]
    specs += [_spec(f"lasso:moves:high:width={w}:offset=8", "lasso_high", {"MgWd": w}, 8, "moves") for w in (5, 20)]
    specs += [_spec(f"lasso:moves:low:contrast={c}:offset=4", "lasso_low", {"MgEd": c}, 4, "moves") for c in (1, 5, 10, 40, 80)]
    specs += [_spec(f"lasso:moves:noisy:offset={d}", "lasso_noisy", {}, d, "moves") for d in (0, 8)]
    # Stopping three quarters of the way round: an outline the tool laid no anchors on closes as
    # its live segment plus Enter's straight line, instead of collapsing at the start point.
    specs += [_spec(f"lasso:moves:{img}:{key}={v}:offset={d}:arc=0.75", f"lasso_{img}", {opt: v}, d, "moves", 0.75)
              for img, key, opt, v, d in (("high", "width", "MgWd", 10, 8), ("high", "width", "MgWd", 20, 8),
                                          ("low", "contrast", "MgEd", 1, 4), ("low", "contrast", "MgEd", 10, 4),
                                          ("low", "contrast", "MgEd", 40, 4))]
    # Between a weak edge (40 levels) and a strong one (160) 12 px out: which one the outline
    # takes, as the contrast setting rises.
    specs += [_spec(f"lasso:moves:two_edge:contrast={c}:offset=6", "lasso_two_edge", {"MgEd": c}, 6, "moves") for c in (1, 10, 30, 60, 90)]
    return specs


REFINE_BASE = {"radius": 0, "smart": False, "contrast": 0, "smooth": 0, "feather": 0, "shift": 0}


def refine_specs() -> list[ScenarioSpec]:
    """Refine Edge (Select and Mask's output, by its event) on an exact hard circle over the soft
    disc, one setting changed at a time."""
    hard = ["ellipse", CENTRE[0] - RADIUS, CENTRE[1] - RADIUS, CENTRE[0] + RADIUS, CENTRE[1] + RADIUS, False, "replace"]
    variants = [("base", {})] + [(f"radius={r}", {"radius": r}) for r in (2, 5, 10, 20)] + [
        ("radius=10:smart", {"radius": 10, "smart": True}), ("radius=10:contrast=50", {"radius": 10, "contrast": 50}),
        ("smooth=20", {"smooth": 20}), ("feather=5", {"feather": 5}), ("shift=-50", {"shift": -50}), ("shift=50", {"shift": 50})]
    variants = [("refine_soft", name, change) for name, change in variants]
    variants += [(f"refine_{img}", f"{img}:{name}", change) for img, name, change in (
        ("colour", "radius=10", {"radius": 10}), ("equiluminant", "radius=10", {"radius": 10}),
        ("gradient", "radius=10", {"radius": 10}), ("gradient", "radius=20", {"radius": 20}),
        ("gradient", "radius=10:smart", {"radius": 10, "smart": True}),
        ("texture", "radius=10", {"radius": 10}), ("texture", "radius=20", {"radius": 20}))]
    specs = []
    for image_name, name, change in variants:
        o = {**REFINE_BASE, **change}
        op = ["refine_edge", o["radius"], o["smart"], o["contrast"], o["smooth"], o["feather"], o["shift"]]
        steps = (("open_test_image", image_name), ("selection_ops", [hard, op]), ("record", "mask"), ("close_throwaway_document",))
        specs.append(ScenarioSpec(f"refine:{name}", "lasso_probe", "run", False, steps))
    return specs


def edge_distance(mask: np.ndarray) -> dict[str, float]:
    """Where the selection's edge lies against the disc: its boundary pixels' distances from the
    centre, as mean and spread of (distance - RADIUS), and the selected area against the disc's."""
    selected = mask >= 128
    edge = selected & ~(np.roll(selected, 1, 0) & np.roll(selected, -1, 0) & np.roll(selected, 1, 1) & np.roll(selected, -1, 1))
    ys, xs = np.nonzero(edge)
    if len(xs) == 0:
        return {"selected": 0.0}
    d = np.hypot(xs + 0.5 - CENTRE[0], ys + 0.5 - CENTRE[1]) - RADIUS
    return {"selected": float(selected.sum()), "disc": math.pi * RADIUS ** 2, "edge_mean": round(float(d.mean()), 3),
            "edge_sd": round(float(d.std()), 3), "edge_min": round(float(d.min()), 3), "edge_max": round(float(d.max()), 3)}


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith(("lasso:", "refine:")) and row.get("status") == "ok" and "mask" in (row.get("observations") or {}):
            mask_row = row["observations"]["mask"]
            mask = np.frombuffer(base64.b64decode(mask_row["mask"]), dtype=np.uint8).reshape(mask_row["shape"])
            latest[row["item_id"]] = {"item_id": row["item_id"], **mask_row, **edge_distance(mask)}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.lasso_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--refine", action="store_true", help="refine-edge specs and rows instead")
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        rows = [r for r in rows if r["item_id"].startswith("refine:" if args.refine else "lasso:")]
        name = "refine-probe.jsonl" if args.refine else "lasso-probe.jsonl"
        with (args.dataset / name).open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} lasso probe rows written")
        return
    specs = refine_specs() if args.refine else lasso_specs()
    name = "refine-families.jsonl" if args.refine else "lasso-families.jsonl"
    with (args.dataset / name).open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} lasso probe specs")


if __name__ == "__main__":
    main()
