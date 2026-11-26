"""Photoshop's Dual Brush, rebuilt from strokes with a second tip (tipmix_probe; tipmix-probe.jsonl).

The second tip is laid along the stroke at its own spacing (from the stroke's start, one dab per
step, no scatter); its dabs join as their union (the larger coverage wins), and the union masks
the main stroke through the blend mode: multiply p d / 255, darken min(p, d), subtract
max(0, p - d). Colour burn and hard mix change a full-ink stroke little (4.4 and 2.8 levels on
average, the middle of its centre row not at all; not modelled). Two things differ from the main tip: the second tip's dabs centre on a pixel corner, half a pixel further along and lower
than the main tip's (which centre on pixel centres), and a hard second tip comes out slightly soft
(a hard disc blurred by a Gaussian of DUAL_SOFTNESS px). Within 1.2 to 1.6 levels on average on
9 and 21 px second tips at 100% spacing, 1.7 at 25%; the worst pixels (55 to 70 levels) lie on its
soft edge.

Not settled: the softening itself (a fitted blur), scatter and count, the second tip's own
roundness and angle, colour burn and hard mix.

Texture (tipmix-probe.jsonl, texture specs): a script cannot choose the pattern (the tool options
carry no pattern key, ticked in the panel or not), so the runner picks the harness's ramp pattern in
the Brush Settings panel's picker (pick_texture_pattern) and sets the rest by script. With Texture
Each Tip off, the texture tiles from the document's corner and sets each pixel's ink from the
pattern grey g under it, whatever the flow (texture_alpha): multiply and darken g (on full ink),
subtract 255 - g, depth d mixing towards full ink, 255 (1 - d (1 - g/255)); invert uses 255 - g.
With Texture Each Tip on, every dab lays flow x that share and the overlapping dabs build up:
255 (1 - (1 - flow share)^N), N the dabs covering a pixel (EACH_TIP_DABS, 20 for a 41 px tip at
5% spacing). Within 1.5 levels on every full-ink row. Height, linear height and colour burn leave
full ink as it is but threshold partial ink against the pattern: on a soft tip's edge,
clamp(11.5 ink + 8.6 - 0.97 g) (height_texture, fitted at depth 100: 0.84 levels on average).

Not settled: height at other depths (at 50% the hard edge's 72 became 434 - g), linear height and
colour burn on partial ink, contrast, brightness, scale.
"""

from __future__ import annotations

import numpy as np

DUAL_SOFTNESS = 0.6  # px, the Gaussian a hard second tip comes out blurred by
DUAL_OFFSET = (0.5, 0.5)  # (along, down) px from where the main tip would centre


def _coverage(cx: float, cy: float, radius: float, shape: tuple[int, int], samples: int = 8) -> np.ndarray:
    offsets = (np.arange(samples) + 0.5) / samples
    ys = (np.arange(shape[0])[:, None] + offsets).ravel()
    xs = (np.arange(shape[1])[:, None] + offsets).ravel()
    inside = (xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2 <= radius * radius
    return inside.reshape(shape[0], samples, shape[1], samples).mean(axis=(1, 3))


def _blur(mask: np.ndarray, sigma: float) -> np.ndarray:
    reach = int(np.ceil(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-reach, reach + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    mask = np.apply_along_axis(lambda v: np.convolve(v, kernel, "same"), 0, mask)
    return np.apply_along_axis(lambda v: np.convolve(v, kernel, "same"), 1, mask)


def dual_dabs(shape: tuple[int, int], start: tuple[int, int], length: float, size: float, spacing: float) -> np.ndarray:
    """The second tip's union (0..255) along a horizontal stroke from pixel `start`, `length` px."""
    step = max(1.0, size * spacing / 100)
    union = np.zeros(shape)
    x = 0.0
    while x <= length + 1e-9:
        cx, cy = start[0] + x + 0.5 + DUAL_OFFSET[0], start[1] + 0.5 + DUAL_OFFSET[1]
        union = np.maximum(union, _blur(_coverage(cx, cy, size / 2, shape), DUAL_SOFTNESS))
        x += step
    return union * 255


def combine(stroke: np.ndarray, dual: np.ndarray, mode: str) -> np.ndarray:
    """The main stroke's alpha masked by the second tip's union through `mode`."""
    if mode == "multiply":
        return stroke * dual / 255
    if mode == "darken":
        return np.minimum(stroke, dual)
    if mode == "subtract":
        return np.maximum(0.0, stroke - dual)
    raise ValueError(f"mode {mode!r} is not modelled")


EACH_TIP_DABS = 20  # dabs covering a pixel of the probe's stroke: a 41 px tip at 5% spacing (2.05 px)


def texture_alpha(grey: float, mode: str, depth: float = 100, dabs: int | None = None, flow: float = 100) -> float:
    """A full-ink stroke's alpha over pattern grey `grey` (0..255) with a texture in `mode` at
    `depth` %; with `dabs`, Texture Each Tip: that many dabs over the pixel, each at `flow` %."""
    g, d = grey / 255, depth / 100
    if mode in ("multiply", "darken"):
        share = 1 - d * (1 - g)
    elif mode == "subtract":
        share = 1 - d * g
    elif mode in ("height", "linearHeight", "colorBurn"):
        share = 1.0
    else:
        raise ValueError(f"texture mode {mode!r} is not modelled")
    if dabs:
        return 255 * (1 - (1 - flow / 100 * share) ** dabs) if share < 1 else 255.0
    return 255 * share


HEIGHT_GAIN, HEIGHT_OFFSET, HEIGHT_GREY = 11.5, 8.6, 0.97  # fitted on a soft tip's edge at depth 100


def height_texture(ink: np.ndarray, grey: np.ndarray) -> np.ndarray:
    """Height texture at depth 100 over partial ink `ink` (the stroke's alpha without texture) and
    pattern grey `grey`: a steep threshold of the ink against the pattern, full ink kept."""
    return np.clip(HEIGHT_GAIN * np.asarray(ink, float) + HEIGHT_OFFSET - HEIGHT_GREY * np.asarray(grey, float), 0, 255)
