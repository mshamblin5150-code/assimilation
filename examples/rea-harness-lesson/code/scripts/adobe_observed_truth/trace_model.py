"""Illustrator's Image Trace as behaviour to match, measured on the harness's own rasters
(illustrator_trace; trace-probe.jsonl, 100 traces).

Image Trace is not rebuilt step by step here: what a tracer must do to match it is, with the
tolerances Illustrator itself showed (black and white, white ignored, other options default):

- outlines within 0.10 pt (circle), 0.05 pt (square turned 30 degrees) and 0.34 pt (five-point
  star) of the true shape, areas within 0.2%;
- economical paths: a circle in 5 anchors, a square in 4 sharp corners, the star in 12. Path
  fidelity 100 follows the pixel steps instead (53, 112 and 96 anchors); corner fidelity 0
  rounds corners into extra anchors;
- noise n drops every region of fewer than n pixels (1 keeps all, default 50);
- threshold t blackens a grey ramp out to grey level about t + 2 (within 3 px on a ramp
  rising 1.28 levels per px);
- with white ignored and the default stacked (overlapping) method, a hole that is white is not
  cut out: a black ring traces as a disc;
- traced colours come back within 1 level.

- abutting cuts white holes out (a black ring traces as an outer and an inner disc) and traces
  each colour's visible region (within 0.3% of its pixels, three overlapping discs); overlapping
  keeps the lowest region as it is and enlarges the others where they meet (by 2.5% and 4%);
- stroke tracing makes a bar a stroke when it is at most half the largest stroke weight wide
  (traced_as_stroke), along its centre line 1 pt low with its ends drawn in by half its width;
  every traced stroke reads 2 pt whatever the bar's width. With fills on too every bar also
  gets a fill.

Not settled: the fitting algorithm itself, the traced stroke's weight (2 pt for bars of 2 to 8
px), the tie rule for a reduced colour (the darker of two members equally near: three cases).

Colour count: tracingColors is applied only when tracingColorTypeValue is full colour (the DOM's
"limited" type, whatever its name says, ignores it: 2 to 8 there, and colorFidelity 0 to 75 in
either type, kept all eight flat colours). The count includes white, which is then dropped when
white is ignored (colours_kept), and the colours kept are the image's own (within 1 level), not
averages; Illustrator's 3, 6 and 16 Colors presets set exactly that. Which merge: the best weighted
k-means clustering in RGB (pixel counts as weights), each cluster shown by its member nearest its
centre, ties to the lower luma (reduce_colours); exact at 3 and 6 colours on the palette (Lab clusters differently).
"""

from __future__ import annotations

import numpy as np

from . import illustrator_trace as it

DEFAULT_MAX_DEVIATION_PT = {"circle": 0.11, "square": 0.05, "star": 0.35}
DEFAULT_ANCHORS = {"circle": 5, "square": 4, "star": 12}
NOISE_DEFAULT = 50
THRESHOLD_OFFSET = 2.0  # grey levels


def outline(path: dict, height: float, samples: int = 24) -> np.ndarray:
    """Points along a traced path (image coordinates, y down)."""
    points = np.asarray(path["points"], float)
    count = len(points)
    out = []
    for i in range(count if path["closed"] else count - 1):
        a, b = points[i], points[(i + 1) % count]
        p0, p1, p2, p3 = a[0:2], a[4:6], b[2:4], b[0:2]
        t = np.linspace(0, 1, samples, endpoint=False)[:, None]
        out.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    pts = np.vstack(out)
    pts[:, 1] = height - pts[:, 1]
    return pts


def _square() -> np.ndarray:
    cx, cy, half, turn = it.SQUARE
    a = np.radians(turn)
    c, s = np.cos(a), np.sin(a)
    return np.array([[cx + u * c - v * s, cy + u * s + v * c] for u, v in ((-half, -half), (half, -half), (half, half), (-half, half))])


def _polygon_distance(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    best = np.full(len(points), np.inf)
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        ab = b - a
        t = np.clip(((points - a) @ ab) / (ab @ ab), 0, 1)
        best = np.minimum(best, np.linalg.norm(points - (a + t[:, None] * ab), axis=1))
    return best


def deviation(points: np.ndarray, shape: str) -> np.ndarray:
    """Each point's distance from the true outline of a probe shape."""
    if shape == "circle":
        cx, cy, r = it.CIRCLE
        return np.abs(np.hypot(points[:, 0] - cx, points[:, 1] - cy) - r)
    return _polygon_distance(points, _square() if shape == "square" else it._star_polygon())


def true_area(shape: str) -> float:
    if shape == "circle":
        return float(np.pi * it.CIRCLE[2] ** 2)
    polygon = _square() if shape == "square" else it._star_polygon()
    x, y = polygon[:, 0], polygon[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def kept_regions(areas_px: list[int], noise: int) -> list[int]:
    return [a for a in areas_px if a >= noise]


def black_width_on_ramp(threshold: int, size: int) -> float:
    """How far (px) black reaches on the probe ramp (grey floor(256 x / size) at column x)."""
    return float(np.clip((threshold + THRESHOLD_OFFSET) * size / 256, 0, size))


ABUTTING_AREA_TOLERANCE = 0.003  # a colour's traced area against its visible pixels
STROKE_DROP_PT = 1.0  # a traced stroke lies this far below its bar's centre line
TRACED_STROKE_WEIGHT = 2  # pt, what every traced stroke reads


def traced_as_stroke(width_px: float, max_stroke_weight: float) -> bool:
    """Whether a bar `width_px` wide becomes a stroke (at 1 px per pt)."""
    return width_px <= max_stroke_weight / 2


def colours_kept(tracing_colors: int, image_colours: int, ignore_white: bool) -> int:
    """How many fill colours a full-colour trace keeps: the count includes white, which is
    dropped when white is ignored."""
    return min(tracing_colors, image_colours) - (1 if ignore_white else 0)


def reduce_colours(colours: np.ndarray, weights: np.ndarray, count: int) -> np.ndarray:
    """The colour each of an image's `colours` (RGB, with pixel counts `weights`) is traced as when
    reduced to `count`: the best weighted k-means clustering in RGB (every choice of starting
    centres tried, the lowest cost kept), each cluster shown by its member nearest its centre,
    ties to the darker. Matched Illustrator at 3 and 6 colours on the eight-colour palette."""
    from itertools import combinations

    x, w = np.asarray(colours, float), np.asarray(weights, float)
    if count >= len(x):
        return x.copy()
    best = None
    for seeds in combinations(range(len(x)), count):
        centres = x[list(seeds)].copy()
        for _ in range(100):
            label = ((x[:, None] - centres[None]) ** 2).sum(-1).argmin(1)
            moved = np.array([(x[label == j] * w[label == j, None]).sum(0) / w[label == j].sum() if (label == j).any() else centres[j]
                              for j in range(count)])
            if np.allclose(moved, centres):
                break
            centres = moved
        cost = float((w * ((x - centres[label]) ** 2).sum(-1)).sum())
        if best is None or cost < best[0] - 1e-9:
            best = (cost, label, centres)
    _, label, centres = best
    shown = np.empty_like(x)
    for j in range(count):
        members = np.nonzero(label == j)[0]
        if len(members) == 0:
            continue
        distance = ((x[members] - centres[j]) ** 2).sum(-1)
        darkness = x[members] @ np.array([0.299, 0.587, 0.114])  # luma: the darker of equally near members
        pick = members[np.lexsort((darkness, np.round(distance, 6)))[0]]
        shown[members] = x[pick]
    return shown
