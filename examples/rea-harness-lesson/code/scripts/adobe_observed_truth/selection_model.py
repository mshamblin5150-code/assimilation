"""Magic Wand, Paint Bucket and Feather rebuilt from the selection probe's measurements.

A pixel matches the clicked one when its largest channel difference is within the tolerance and
the spread between its channel differences, rounded up to an even number, is too. On greys (all
channels moving together) that is |difference| <= tolerance, inclusive; on colours it also limits
how far the channels move apart (a grid of red and green steps selected a hexagon, not a square),
and a difference in one channel is held to the tolerance rounded down to even (tolerance 1 took
only the exact colour, 5 took 4 either side). Contiguous selection joins matching pixels through the four side neighbours only (two
squares touching at a corner were not joined); without it every matching pixel is taken. Anti-
aliasing adds a one-pixel ring of partial selection outside the edge; its level was 243-250 of
255 here (170 when the click landed half a pixel off), so AA_LEVEL is an approximation. The Paint
Bucket fills exactly the pixels the wand selects with the same settings. Feather is a Gaussian
blur of the selection with sigma 1.02 times the radius. Against all 36 probes: hard wand
selections and contiguity exactly, anti-aliased edges within 10 levels, feathers within 4.
Untested: other colour modes and bit depths, Sample Merged, the wand's sample size option.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

AA_LEVEL = 246
FEATHER_SIGMA_PER_RADIUS = 1.02


def matches(image: np.ndarray, seed_rgb: np.ndarray, *, tolerance: int) -> np.ndarray:
    """Which pixels of an RGB image the wand counts as like `seed_rgb`."""
    delta = image[..., :3].astype(int) - np.asarray(seed_rgb, dtype=int)
    largest = np.abs(delta).max(axis=-1)
    spread = delta.max(axis=-1) - delta.min(axis=-1)
    return (largest <= tolerance) & (2 * ((spread + 1) // 2) <= tolerance)


def _flood(like: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    region = np.zeros_like(like)
    x, y = seed
    if not like[y, x]:
        return region
    region[y, x] = True
    queue = deque([(x, y)])
    height, width = like.shape
    while queue:
        cx, cy = queue.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < width and 0 <= ny < height and like[ny, nx] and not region[ny, nx]:
                region[ny, nx] = True
                queue.append((nx, ny))
    return region


def wand(image: np.ndarray, seed: tuple[int, int], *, tolerance: int, contiguous: bool, anti_alias: bool) -> np.ndarray:
    """The selection (0..255) a Magic Wand click at pixel `seed` (x, y) makes; the Paint Bucket
    fills the same pixels."""
    like = matches(image, image[seed[1], seed[0], :3], tolerance=tolerance)
    region = _flood(like, seed) if contiguous else like
    mask = np.where(region, 255, 0).astype(np.uint8)
    if anti_alias:
        grown = region.copy()
        grown[1:] |= region[:-1]
        grown[:-1] |= region[1:]
        grown[:, 1:] |= region[:, :-1]
        grown[:, :-1] |= region[:, 1:]
        mask[grown & ~region] = AA_LEVEL
    return mask


def _kernel(sigma: float) -> np.ndarray:
    reach = int(math.ceil(4 * sigma))
    edges = [0.5 * (1 + math.erf((i + 0.5) / (sigma * math.sqrt(2)))) for i in range(-reach - 1, reach + 1)]
    return np.diff(edges)


def feather(mask: np.ndarray, radius: float) -> np.ndarray:
    """A selection (0..255) feathered by `radius` pixels: a Gaussian blur, nothing outside the canvas."""
    kernel = _kernel(FEATHER_SIGMA_PER_RADIUS * radius)
    soft = mask.astype(float)
    soft = np.apply_along_axis(lambda line: np.convolve(line, kernel, mode="same"), 1, soft)
    soft = np.apply_along_axis(lambda line: np.convolve(line, kernel, mode="same"), 0, soft)
    return np.clip(np.round(soft), 0, 255).astype(np.uint8)
