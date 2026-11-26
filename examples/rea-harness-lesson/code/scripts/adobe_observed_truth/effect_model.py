"""Photoshop's layer Stroke, Outer Glow and Drop Shadow, rebuilt from profiles across the edge of
the harness's own square (effect_probe; effect-probe.jsonl, 23 effects in solid red).

d is a pixel's distance from the shape's edge, counted in whole pixels outward from 0 (the first
pixel outside); coverage is 0..255.

- Stroke: covers exactly `size` pixels outside, inside, or split at the edge (center; an odd size
  puts a half-covered pixel either side). Corners are round at 10 px (Euclidean distance) and
  nearly square at 3 px (not settled).
- Outer Glow, precise: floor(255 (size - d) / (size + 1)) (within 2 levels). With spread 50% about
  the first half of the size is solid and the ramp still ends at the size; its exact steps differ
  between sizes 5 and 20 (not settled).
- Drop Shadow: the shape blurred by a Gaussian of sigma 0.41 x size (within 2% of full coverage),
  moved by its distance at its angle.
- Outer Glow, softer: the same blur doubled and capped, min(1, 2 x blur) (within 2.8%).
Not settled: spread for the softer glow and shadow, contours, noise, the inner effects.
"""

from __future__ import annotations

from math import erf, sqrt

import numpy as np

BLUR_SIGMA_PER_SIZE = 0.41


def stroke(d_outside: np.ndarray, size: int, position: str) -> np.ndarray:
    """Stroke coverage at signed whole-pixel distances (0 = first pixel outside, -1 = first inside)."""
    d = np.asarray(d_outside, float)
    if position == "outside":
        return np.where((d >= 0) & (d < size), 255, 0)
    if position == "inside":
        return np.where((d < 0) & (d >= -size), 255, 0)
    half = size / 2
    inner = np.where((d >= 0) & (d < np.floor(half)), 255, np.where((d < 0) & (d >= -np.floor(half)), 255, 0))
    if size % 2:
        inner = np.where((d == np.floor(half)) | (d == -np.floor(half) - 1), 128, inner)
    return inner


def precise_glow(d: np.ndarray, size: int) -> np.ndarray:
    """A precise outer glow with no spread."""
    return np.clip(np.floor(255 * (size - np.asarray(d, float)) / (size + 1)), 0, 255).astype(int)


def _edge_blur(d: np.ndarray, size: float) -> np.ndarray:
    sigma = BLUR_SIGMA_PER_SIZE * size
    return 0.5 * (1 - np.vectorize(erf)((np.asarray(d, float) + 0.5) / (sigma * sqrt(2))))


def shadow(d: np.ndarray, size: float) -> np.ndarray:
    return 255 * _edge_blur(d, size)


def softer_glow(d: np.ndarray, size: float) -> np.ndarray:
    return 255 * np.minimum(1.0, 2 * _edge_blur(d, size))
