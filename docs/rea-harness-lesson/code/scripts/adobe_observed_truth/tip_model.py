"""Photoshop's sampled brush tips, rebuilt from the masks it hands its tip kernel.

Sampled tips (a brush defined from image pixels) paint through the same per-dab kernel as the
round tip (MaxBrushTip, or AirbrushTip under 100% flow): Photoshop.exe scales, turns and
squashes the tip first and the kernel only lays the finished mask into the stroke. Measured on
the harness's own tips (brush_probe.OWN_TIPS; brush-tip-probe.jsonl, 22 probes):

- the tip is the art's non-white content; its alpha is the ink a pixel's grey has in the grey
  working space (factory Dot Gain 20%): black 255, white 0, sRGB grey 128 -> 149.5 (dithered
  149/150). Only that one grey was measured, so ink_of_grey knows black, white and 128;
- at its own size the mask is the art pixel for pixel, with an empty column right and two rows
  below for sub-pixel placement;
- scaled up, output pixel j samples the art bilinearly at j / scale plus the dab's sub-pixel
  phase (within 0.1 level at 2x, 0.43 at 1.27x);
- scaled down, an area (triangle) filter widened by 1 / scale comes within 1 to 4.5 levels on
  average: Photoshop also sharpens slightly (overshoot at edges), which is not fitted.

- roundness keeps whole rows of the (scaled) tip, unfiltered: mask row j is art row
  floor(j / roundness) (within the grey's dither at roundness 50 and 25%, squash_tip);
- an angle turns the tip counter-clockwise (rows down, columns right) by exactly the angle and
  samples it bilinearly (rotate_tip): within 0.35 levels inside the art at 30 and -45 degrees
  (a mask of single-pixel impulses shows each spread over the 2 x 2 bilinear footprint, centroids
  within 0.22 px of the turned grid); a quarter turn is exact. The art's outer border is not:
  pixels within a pixel of it differ by up to 177 levels, and a quarter turn loses one edge row.

Not settled: the downscale's exact filter, the turned tip's outer border, texture, dual tips. Tried for the downscale (2026-11-26): Keys cubics
(a = -0.5, -0.75, -1), Mitchell and Catmull-Rom widened by 1 / scale, and a 2 x 2 box mipmap
then bilinear, all fit worse than the triangle. The triangle's best width is 1 / scale at
scales 0.5 and 0.25, but at 0.625 and 0.75 the error still falls past 1 / scale (to 3.3 levels
at 2.0 for 0.625), so the width is not simply 1 / scale there.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def ink_of_grey(grey: int) -> float:
    """A tip pixel's alpha from its sRGB grey: the measured points only."""
    known = {0: 255.0, 128: 149.5, 255: 0.0}
    if grey not in known:
        raise ValueError(f"grey {grey} was not measured; only {sorted(known)}")
    return known[grey]


def tip_alpha(boxes: Sequence[tuple[int, int, int, int, int]], canvas: tuple[int, int]) -> np.ndarray:
    """The alpha of tip art drawn as grey boxes on a white canvas, cropped to its non-white content."""
    width, height = canvas
    grey = np.full((height, width), 255, dtype=int)
    for left, top, right, bottom, value in boxes:
        grey[top:bottom, left:right] = value
    ys, xs = np.nonzero(grey < 255)
    grey = grey[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.vectorize(ink_of_grey)(grey)


def _axis(art: np.ndarray, out_n: int, scale: float, phase: float, axis: int) -> np.ndarray:
    n = art.shape[axis]
    widen = max(1.0, 1.0 / scale)
    rows = []
    for j in range(out_n):
        centre = j / scale + phase
        taps = np.arange(int(np.floor(centre - widen)) - 1, int(np.ceil(centre + widen)) + 2)
        weights = np.clip(1.0 - np.abs(taps - centre) / widen, 0.0, None)
        inside = (taps >= 0) & (taps < n)
        values = np.take(art, np.clip(taps, 0, n - 1), axis=axis)
        values = values * (inside[:, None] if axis == 0 else inside[None, :])
        total = weights.sum()
        rows.append(np.tensordot(weights / total if total else weights, values, axes=([0], [axis])))
    out = np.array(rows)
    return out if axis == 0 else out.T


def resample_tip(art: np.ndarray, scale: float, phase: tuple[float, float], shape: tuple[int, int]) -> np.ndarray:
    """The tip mask Photoshop hands the kernel for `art` drawn at `scale`, with sub-pixel phase
    (rows, columns) and the mask's shape (the art scaled plus room for the phase)."""
    if scale == 1.0 and phase == (0.0, 0.0):
        out = np.zeros(shape)
        out[:art.shape[0], :art.shape[1]] = art
        return out
    tall = _axis(art, shape[0], scale, phase[0], 0)
    return _axis(tall, shape[1], scale, phase[1], 1)


def squash_tip(art: np.ndarray, roundness: float, shape: tuple[int, int]) -> np.ndarray:
    """The mask of `art` at `roundness` (0..1): whole rows kept, row j from art row floor(j / roundness)."""
    out = np.zeros(shape)
    rows = np.floor(np.arange(shape[0]) / roundness).astype(int)
    keep = rows < art.shape[0]
    width = min(shape[1], art.shape[1])
    out[np.nonzero(keep)[0], :width] = art[rows[keep], :width]
    return out


def _bilinear(art: np.ndarray, y: np.ndarray, x: np.ndarray) -> np.ndarray:
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = y - y0, x - x0

    def at(yy: np.ndarray, xx: np.ndarray) -> np.ndarray:
        inside = (yy >= 0) & (yy < art.shape[0]) & (xx >= 0) & (xx < art.shape[1])
        return np.where(inside, art[np.clip(yy, 0, art.shape[0] - 1), np.clip(xx, 0, art.shape[1] - 1)], 0.0)

    return (at(y0, x0) * (1 - fy) * (1 - fx) + at(y0, x0 + 1) * (1 - fy) * fx
            + at(y0 + 1, x0) * fy * (1 - fx) + at(y0 + 1, x0 + 1) * fy * fx)


def rotate_tip(art: np.ndarray, degrees: float, offset: tuple[float, float], shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """The mask of `art` turned counter-clockwise by `degrees`, sampled bilinearly, and which of its
    pixels map inside the art away from its outer border (where the model is not settled).
    `offset` (rows, columns) places the turned art past the top-left corner of its turned box."""
    t = np.radians(degrees)
    turn = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    h, w = art.shape
    corner = -(turn @ np.array([[0, 0, h, h], [0, w, 0, w]], float)).min(axis=1)
    qy, qx = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    y, x = np.linalg.inv(turn) @ np.stack([qy.ravel() - corner[0] - offset[0], qx.ravel() - corner[1] - offset[1]])
    inner = ((y > 1) & (y < h - 2) & (x > 1) & (x < w - 2)).reshape(shape)
    return _bilinear(np.asarray(art, float), y, x).reshape(shape), inner
