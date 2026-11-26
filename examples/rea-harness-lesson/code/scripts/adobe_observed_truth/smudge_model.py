"""Photoshop's Smudge tool, rebuilt from strokes over the harness's own black band (smudge_probe;
smudge-probe.jsonl, 13 strokes: strength 10 to 100, spacing 5 to 100%, Finger Painting).

The finger moves one pixel at a time, whatever the brush's spacing (spacing 5, 10, 25, 50 and 100%
leave the same trail within 3 levels). At each step every pixel under the tip is pulled towards the
pixel one step behind it, by strength x the tip's coverage of the pixel:
C <- C + s M (C(x - 1) - C). So the finger carries what it last left, and 100% copies it on
unchanged. With a hard round tip (exact pixel coverage of the disc) and s = strength / 100, nothing
fitted, the trail turns half white within 2 px of where Photoshop's does at every strength (2 to
251 px past the band).

Not settled: the residue the trail levels off at (Photoshop's 25, 50, 75 and 90% trails settle at
254, 247 to 249, 233 and 203 where the model goes on towards white; rounding each step to 8 bits
leaves less than that at 25 and 50% and more at 75 and 90%; it varies by 2 levels between runs);
the rows just outside the tip at 100% (Photoshop darkens them to 155, the model leaves them
white); Finger Painting (switched on, with a grey foreground, a scripted stroke path leaves the
plain trail); soft tips and Sample All Layers.
"""

from __future__ import annotations

import numpy as np


def _coverage(cx: float, cy: float, radius: float, shape: tuple[int, int], samples: int = 8) -> np.ndarray:
    """Each pixel's coverage by the disc of `radius` round (cx, cy); pixel i spans [i, i + 1)."""
    offsets = (np.arange(samples) + 0.5) / samples
    ys = (np.arange(shape[0])[:, None] + offsets).ravel()
    xs = (np.arange(shape[1])[:, None] + offsets).ravel()
    inside = (xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2 <= radius * radius
    return inside.reshape(shape[0], samples, shape[1], samples).mean(axis=(1, 3))


def smudge(image: np.ndarray, start: tuple[int, int], end: tuple[int, int], strength: int, size: float) -> np.ndarray:
    """A horizontal smudge stroke (start and end on one row, through pixel centres) over a grey image."""
    if start[1] != end[1] or end[0] <= start[0]:
        raise ValueError("only left-to-right horizontal strokes are modelled")
    canvas = np.asarray(image, float).copy()
    radius, s, row = size / 2, strength / 100, start[1]
    reach = int(np.ceil(radius)) + 1
    y0, y1 = max(0, row - reach), min(canvas.shape[0], row + reach + 1)
    for x in range(start[0] + 1, end[0] + 1):
        x0, x1 = max(1, x - reach), min(canvas.shape[1], x + reach + 1)
        cover = _coverage(x + 0.5 - x0, row + 0.5 - y0, radius, (y1 - y0, x1 - x0))
        here, behind = canvas[y0:y1, x0:x1], canvas[y0:y1, x0 - 1:x1 - 1]
        canvas[y0:y1, x0:x1] = here + s * cover * (behind - here)
    return canvas
