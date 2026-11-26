"""Photoshop's Image Size resampling, rebuilt from impulse responses (resample_probe;
resample-probe.jsonl: six methods, five sizes, from a 64 px image of single white pixels).

Every method is separable, centre-aligned (output pixel j samples the source at
(j + 0.5) / scale - 0.5), clamps at the image edge, widens its kernel by 1 / scale when reducing
and normalises the weights; results round half up.

- Nearest Neighbor: a box; exact (an exact tie takes the pixel after).
- Bilinear: a triangle; exact enlarging and at 1/2 (a 2 x 2 average); an area average when
  reducing by other factors (within 0.7 level on average at 0.375).
- Bicubic: the cubic with a = -0.75; within 3 levels at most, 0.03 on average.
- Bicubic Smoother: a Mitchell-Netravali cubic with B = 0.4 and C = 0.7 enlarging (0.9 reducing),
  not the standard B = C = 1/3; within 0.12 on average.
- Bicubic Sharper: B = 0.2, C = 1.0 enlarging; reducing, the a = -1.5 cubic comes within 0.31 on
  average: Photoshop likely sharpens after (not settled).
- Bicubic Automatic: Smoother when enlarging, Sharper when reducing (measured: identical images).
Preserve Details and the deep-learning upscale were not probed.
"""

from __future__ import annotations

import numpy as np


def _cubic(a: float):
    def kernel(x: np.ndarray) -> np.ndarray:
        x = np.abs(x)
        return np.where(x < 1, (a + 2) * x ** 3 - (a + 3) * x ** 2 + 1,
                        np.where(x < 2, a * x ** 3 - 5 * a * x ** 2 + 8 * a * x - 4 * a, 0.0))
    return kernel, 2.0


def _bc(b: float, c: float):
    def kernel(x: np.ndarray) -> np.ndarray:
        x = np.abs(x)
        return np.where(x < 1, ((12 - 9 * b - 6 * c) * x ** 3 + (-18 + 12 * b + 6 * c) * x ** 2 + (6 - 2 * b)) / 6,
                        np.where(x < 2, ((-b - 6 * c) * x ** 3 + (6 * b + 30 * c) * x ** 2 + (-12 * b - 48 * c) * x
                                         + (8 * b + 24 * c)) / 6, 0.0))
    return kernel, 2.0


def _box(x: np.ndarray) -> np.ndarray:
    return ((x > -0.5) & (x <= 0.5)).astype(float)


def _triangle(x: np.ndarray) -> np.ndarray:
    return np.clip(1 - np.abs(x), 0, None)


def kernel_for(method: str, enlarging: bool):
    """(kernel, support, widen when reducing) for an Image Size method."""
    if method == "nearestneighbor":
        return _box, 0.5, False
    if method == "bilinear":
        return (_triangle, 1.0, False) if enlarging else (_box, 0.5, True)
    if method == "bicubic":
        return (*_cubic(-0.75), True)
    if method == "bicubicsmoother" or (method == "bicubicautomatic" and enlarging):
        return (*_bc(0.4, 0.7 if enlarging else 0.9), True)
    if method in ("bicubicsharper", "bicubicautomatic"):
        return (*(_bc(0.2, 1.0) if enlarging else _cubic(-1.5)), True)
    raise ValueError(method)


def _axis(a: np.ndarray, n_out: int, kernel, support: float, widen: bool, axis: int) -> np.ndarray:
    n = a.shape[axis]
    scale = n_out / n
    width = max(1.0, 1.0 / scale) if widen else 1.0
    rows = []
    for j in range(n_out):
        centre = (j + 0.5) / scale - 0.5
        taps = np.arange(int(np.floor(centre - support * width)) - 1, int(np.ceil(centre + support * width)) + 2)
        weights = kernel((taps - centre) / width)
        if weights.sum():
            weights = weights / weights.sum()
        rows.append(np.tensordot(weights, np.take(a, np.clip(taps, 0, n - 1), axis=axis), axes=([0], [axis])))
    out = np.array(rows)
    return out if axis == 0 else out.T


def resize(grey: np.ndarray, size: int, method: str) -> np.ndarray:
    """A square 8-bit grey image resized to `size` px by an Image Size method."""
    kernel, support, widen = kernel_for(method, size > grey.shape[0])
    tall = _axis(np.asarray(grey, float), size, kernel, support, widen, 0)
    return np.clip(np.floor(_axis(tall, size, kernel, support, widen, 1) + 0.5), 0, 255).astype(int)
