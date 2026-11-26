"""Illustrator's Width tool, Pencil and automatic Simplify, from the harness's own paths and drags
(illustrator_freehand; freehand-probe.jsonl).

- Width tool: dragging d points away from a path's centre line sets the full stroke width at that
  point to d (half-width d / 2). Between a width point and the ends the half-width eases: on each
  span, from the end (t = 0) to the width point (t = 1), h = h0 + (hp - h0)(a t + (3 - 2a) t^2 +
  (a - 2) t^3) with a = 2.3: flat at the width point, steeper than linear at the ends (within
  0.14 pt on all three probes, including an off-centre width point).
- Pencil: its path ends at the second-to-last mouse sample: the last is dropped whatever the timing
  (straight lines of 11, 12 and 41 samples, with 0.4 s held before the release, ended one sample
  short). Fit to the samples it keeps (screen 1 px per pt), per Fidelity stop (PENCIL_FIDELITY):
  Accurate (0) keeps the most anchors (10 on the sine, 16 on the circle) and every sample within
  0.12 pt; stops 1 to 4 keep 5 to 10 anchors and samples within 0.33 to 0.82 pt, not in order of
  the stop (the circle is the same 6 anchors at stops 2 to 4). Three repeats of every stop gave
  the same anchors and errors within 0.02 pt, except stop 1 (5 or 6 anchors on the sine, 7 or 9
  on the circle), stop 4 on the sine (9 or 10) and one Accurate circle (21 anchors, 0.39 pt).
  The Fidelity stop is set through the Pencil options dialog: a preference set by script
  (plugin/Adobe Freehand Tool/fairness_preset) neither shows there nor reaches the tool, and
  Illustrator's getIntegerPreference returns the same value for any key, real or not.
- Simplify, automatic amount: 200 anchors became 142 and every original point stayed within
  0.14 pt (0.02 on average): the noise (sd 1 pt) is kept.
- Width tool with Alt held: only the dragged side moves, by the same half-width and easing as
  above (within 0.12 pt); the other side stays at the stroke's own edge.
Not settled: the Pencil's fitting algorithm (only its outcome per stop is kept), its smoothing
at speed (one drag speed measured), Simplify's slider.
"""

from __future__ import annotations

import numpy as np

AUTO_ANCHOR_RATIO = 142 / 200
AUTO_MAX_DEVIATION_PT = 0.15
WIDTH_EASE = 2.3
PENCIL_DEFAULT_STOP = 2
# Per Fidelity stop and probe curve: anchors, mean and worst distance (pt) of the kept samples to the path.
PENCIL_FIDELITY = {
    0: {"sine": (10, 0.045, 0.116), "circle": (16, 0.047, 0.119)},
    1: {"sine": (5, 0.256, 0.573), "circle": (9, 0.141, 0.408)},
    2: {"sine": (8, 0.105, 0.329), "circle": (6, 0.264, 0.468)},
    3: {"sine": (8, 0.143, 0.371), "circle": (6, 0.264, 0.466)},
    4: {"sine": (10, 0.285, 0.816), "circle": (6, 0.264, 0.466)},
}


def pencil_samples(points) -> np.ndarray:
    """The mouse samples the Pencil fits: all but the last."""
    return np.asarray(points, float)[:-1]


def half_width(x: np.ndarray, start: float, end: float, width_point: float, drag: float, base_half: float) -> np.ndarray:
    """Half-width along a straight path from `start` to `end` with one width point dragged `drag`."""
    x = np.asarray(x, float)
    t = np.where(x <= width_point, (x - start) / (width_point - start), (end - x) / (end - width_point))
    a = WIDTH_EASE
    ease = a * t + (3 - 2 * a) * t ** 2 + (a - 2) * t ** 3
    return base_half + (drag / 2 - base_half) * ease
