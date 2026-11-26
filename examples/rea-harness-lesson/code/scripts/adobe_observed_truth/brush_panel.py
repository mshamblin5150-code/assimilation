"""Finding the harness's own ramp pattern (tipmix_probe) in screen captures of Photoshop's Brush
Settings panel: the pattern picker shows it as a thumbnail and the texture page as its swatch.
A script cannot choose a brush's texture pattern, so the runner picks it there and checks it."""

from __future__ import annotations

import numpy as np

MIN_RUN = 15  # px: a ramp shorter than this is not the pattern's thumbnail


def find_ramp(image: np.ndarray) -> tuple[int, int] | None:
    """(x, y) of the middle of the lowest grey run rising from dark (< 70) to light (> 190), left
    to right, at least MIN_RUN px long; None when there is none."""
    a = np.asarray(image, int)[..., :3]
    grey = a.mean(axis=-1)
    neutral = (a.max(axis=-1) - a.min(axis=-1)) <= 12
    best = None
    for y in range(a.shape[0]):
        x = 0
        while x < a.shape[1] - 1:
            if not (neutral[y, x] and grey[y, x] < 70):
                x += 1
                continue
            end = x
            while end + 1 < a.shape[1] and neutral[y, end + 1] and grey[y, end + 1] >= grey[y, end] - 2:
                end += 1
            if end - x + 1 >= MIN_RUN and grey[y, end] > 190:
                best = ((x + end) // 2, y)
            x = end + 1
    if best is None:
        return None
    # the middle row of a ramp several rows tall
    x, y = best
    rows = [r for r in range(a.shape[0]) if neutral[r, x] and abs(grey[r, x] - grey[y, x]) <= 3]
    run = [r for r in rows if abs(r - y) <= 10]
    return x, (min(run) + max(run)) // 2 if run else y
