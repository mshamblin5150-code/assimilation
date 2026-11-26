"""Photoshop's round brush (computed tip, dynamics off) rebuilt from the brush probe's measurements.

A dab of size D (radius R = D/2) and hardness h is solid out to a core radius c, then falls off
as a Gaussian: alpha(r) = 1 for r <= c, else exp(-((r - c) / s)^2), with c = a*R - j and
s = b*R + k. a, b, j and k were fitted per hardness across sizes 9, 21 and 99 (FALLOFF) and are
interpolated between: a grows from 0 to about 1 with hardness, b shrinks from 0.66 to 0, and j
and k (about one pixel at full hardness) are the anti-aliased edge. Dabs land every
D * spacing pixels along the stroke from its first point, never closer than one pixel. Each dab
adds paint at the flow: a pixel ends at 1 - prod(1 - flow * dab_i); the stroke is then capped at
the opacity. Pen pressure (the options bar's switches, driven by Photoshop's simulated pressure,
a 0 -> 1 -> 0 taper along the path) is linear: a dab's diameter is size * pressure, its opacity
ceiling is pressure, and spacing follows the current diameter. Against the 56 probes: dabs within
2 alpha levels of 255 up to hardness 50 and 12 on the hardest edges; every stroke's level within
1, its centre line within 2 on average; pressure strokes' widths within 0.3 px on average.
Not matched: the last few pixels of a size taper, where dabs are under 2 px. Untested: other
tips, angle and roundness, dynamics, real pen input, sizes under 9.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

# hardness: (a, b, j, k), fitted 2026-11-25 on brush-probe.jsonl.
FALLOFF: dict[int, tuple[float, float, float, float]] = {
    0: (0.0002, 0.6597, 0.0011, 0.0279),
    10: (0.1596, 0.5705, 0.2444, 0.1516),
    25: (0.3732, 0.4475, 0.5451, 0.3399),
    50: (0.6623, 0.2652, 0.8542, 0.6699),
    75: (0.8640, 0.1154, 0.9261, 0.8904),
    90: (0.9534, 0.0432, 0.9303, 0.9427),
    100: (0.9952, -0.0009, 0.9638, 1.0043),
}
MIN_GAP_PX = 1.0  # spacing 1% of a 21-pixel tip still put dabs 1 pixel apart


def _falloff(hardness: float) -> tuple[float, ...]:
    keys = sorted(FALLOFF)
    lo = max(k for k in keys if k <= hardness)
    hi = min(k for k in keys if k >= hardness)
    t = 0.0 if hi == lo else (hardness - lo) / (hi - lo)
    return tuple(FALLOFF[lo][i] + t * (FALLOFF[hi][i] - FALLOFF[lo][i]) for i in range(4))


def dab(size: float, hardness: float, centre: tuple[float, float], shape: tuple[int, int]) -> np.ndarray:
    """One dab's coverage (0..1) on a pixel grid, centred at `centre` in pixel coordinates
    (a pixel's centre is at +0.5)."""
    a, b, j, k = _falloff(hardness)
    radius = size / 2
    ys, xs = np.mgrid[: shape[0], : shape[1]]
    r = np.hypot(xs + 0.5 - centre[0], ys + 0.5 - centre[1])
    core, width = a * radius - j, max(b * radius + k, 1e-3)
    return np.exp(-((np.maximum(r - core, 0) / width) ** 2))


def dab_centres(start: tuple[float, float], end: tuple[float, float], *, size: float,
                spacing: float) -> list[tuple[float, float]]:
    """Where dabs land on a straight segment: from its start, every size * spacing% pixels
    (never under MIN_GAP_PX), up to its end."""
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length == 0:
        return [start]
    gap = max(size * spacing / 100, MIN_GAP_PX)
    count = int(math.floor(length / gap + 1e-9))
    return [(start[0] + (end[0] - start[0]) * i * gap / length, start[1] + (end[1] - start[1]) * i * gap / length)
            for i in range(count + 1)]


def _pressed_dabs(start: tuple[float, float], end: tuple[float, float], size: float, spacing: float,
                  controls: str) -> list[tuple[tuple[float, float], float, float]]:
    """(centre, diameter, ceiling) of each dab of a stroke with simulated pen pressure: Photoshop
    tapers pressure 0 -> 1 -> 0 along the path; pressure sets the dab's diameter, its opacity
    ceiling or both, and the next dab lands its current diameter * spacing on (at least 1 px)."""
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    dabs, travelled = [], 0.0
    while travelled <= length + 1e-9:
        pressure = 1 - abs(travelled / length - 0.5) * 2
        diameter = size * pressure if controls in ("size", "both") else size
        ceiling = pressure if controls in ("opacity", "both") else 1.0
        t = travelled / length
        dabs.append(((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t), diameter, ceiling))
        travelled += max(diameter * spacing / 100, MIN_GAP_PX)
    return dabs


def stroke(points: Sequence[Sequence[int]], options: dict[str, Any], *, shape: tuple[int, int]) -> np.ndarray:
    """The alpha (0..255) a stroke through pixel centres paints, as Photoshop's round brush
    does: one point is a single dab; two are a straight stroke between them. With "pressure"
    (size, opacity or both) Photoshop's simulated pen pressure tapers the stroke.

    Each dab builds paint toward its own opacity ceiling: paint += (ceiling - paint) * flow * dab,
    never lowering it, so at a fixed ceiling a pixel ends at 1 - prod(1 - flow * dab_i). The
    stroke is then capped at the opacity. A dab under 2 px paints in proportion to its area."""
    size, hardness = options["size_px"], options["hardness"]
    flow, opacity, controls = options["flow"] / 100, options["opacity"] / 100, options.get("pressure")
    anchors = [(p[0] + 0.5, p[1] + 0.5) for p in points]
    if len(anchors) == 1:
        dabs = [(anchors[0], size, 1.0)]
    elif controls:
        dabs = _pressed_dabs(anchors[0], anchors[-1], size, options["spacing"], controls)
    else:
        dabs = [(c, size, 1.0) for c in dab_centres(anchors[0], anchors[-1], size=size, spacing=options["spacing"])]
    paint = np.zeros(shape)
    for centre, diameter, ceiling in dabs:
        if diameter <= 0:
            continue
        cover = dab(diameter, hardness, centre, shape) * min(1.0, diameter / 2) ** 2
        paint += np.maximum(ceiling - paint, 0) * flow * cover
    return np.round(255 * opacity * paint)
