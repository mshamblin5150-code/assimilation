"""Photoshop's alpha channels, selection combining, pixel counting and Select > Modify, rebuilt
from the channel probe (channel-probe.jsonl, 39 selections as 8-bit coverage).

- A selection stored to an alpha channel loads back unchanged.
- Loading a channel onto a selection: add a + b - round(ab/255) (screen), subtract
  round(a(255 - b)/255), intersect round(ab/255); exact on 10,406 pairs of coverages.
- Photoshop's pixel count (the histogram's total) takes the pixels selected at least half
  (coverage >= 128 of 255).
- Expand by v is a greyscale dilation over an octagon: |dx|, |dy| <= v and |dx| + |dy| <=
  2v - floor(v/2); Contract the matching erosion with 2v - ceil(v/2); both keep an anti-aliased
  edge soft. Smooth by r is the median of the (2r + 1)^2 box. Border by w (on a hard selection)
  ramps down from 255 at the edge by round(255/w) per pixel of city-block distance, both sides.
- Grow, on greys, takes the pixels within the seed pixels' range widened by the tolerance,
  joined to the selection through the four side neighbours. Anti-aliasing lowers its edge
  pixels (204, 219, 246 at tolerances 0, 8, 32: not modelled); on colours a different rule
  (likely the wand's) applies, not measured here.

- Color Range: a raised-cosine falloff of the largest Lab channel difference, lightness reaching
  0.38 * fuzziness and a or b 0.33 * fuzziness (a soft box); fitted, close at every fuzziness
  (see color_range).

Exact against every probe except Color Range; untested: Border on soft selections, Expand and Contract at the
document edge, Grow on colours.
"""

from __future__ import annotations

from collections import deque

import numpy as np


def _half_up(v: np.ndarray) -> np.ndarray:
    return np.floor(v + 0.5)


def combine(a: np.ndarray, b: np.ndarray, mode: str) -> np.ndarray:
    """Coverage of selection `a` after loading channel `b` with add (extend), subtract
    (diminish) or intersect."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if mode == "extend":
        return (a + b - _half_up(a * b / 255)).astype(int)
    if mode == "diminish":
        return _half_up(a * (255 - b) / 255).astype(int)
    if mode == "intersect":
        return _half_up(a * b / 255).astype(int)
    raise ValueError(f"unknown mode {mode!r}")


def pixel_count(mask: np.ndarray) -> int:
    return int((np.asarray(mask) >= 128).sum())


def _octagon(v: int, cut: int) -> np.ndarray:
    d = np.arange(-v, v + 1)
    x, y = np.meshgrid(d, d)
    return np.abs(x) + np.abs(y) <= 2 * v - cut


def _morph(mask: np.ndarray, element: np.ndarray, pick) -> np.ndarray:
    mask = np.asarray(mask, int)
    r = element.shape[0] // 2
    padded = np.pad(mask, r)
    out = None
    for dy, dx in zip(*np.nonzero(element)):
        shifted = padded[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
        out = shifted if out is None else pick(out, shifted)
    return out


def expand(mask: np.ndarray, v: int) -> np.ndarray:
    return _morph(mask, _octagon(v, v // 2), np.maximum)


def contract(mask: np.ndarray, v: int) -> np.ndarray:
    return _morph(mask, _octagon(v, (v + 1) // 2), np.minimum)


def smooth(mask: np.ndarray, r: int) -> np.ndarray:
    from numpy.lib.stride_tricks import sliding_window_view

    mask = np.asarray(mask, np.int16)
    ys, xs = np.nonzero(mask)
    out = np.zeros(mask.shape, int)
    if len(ys) == 0:
        return out
    top, bottom = max(0, ys.min() - r), min(mask.shape[0], ys.max() + r + 1)
    left, right = max(0, xs.min() - r), min(mask.shape[1], xs.max() + r + 1)
    padded = np.pad(mask, r)[top:bottom + 2 * r, left:right + 2 * r]
    windows = sliding_window_view(padded, (2 * r + 1, 2 * r + 1)).reshape(bottom - top, right - left, -1)
    out[top:bottom, left:right] = _half_up(np.median(windows, axis=-1)).astype(int)
    return out


def border(mask: np.ndarray, width: int) -> np.ndarray:
    """Border of a hard selection: a ramp falling from 255 at the edge, both sides."""
    inside = np.asarray(mask) > 0
    step = _half_up(255 / width)
    distance = np.full(inside.shape, -1)
    for v in range(1, width + 1):
        diamond = _octagon(v, v)
        grown = _morph(inside.astype(int), diamond, np.maximum) > 0
        shrunk = _morph(inside.astype(int), diamond, np.minimum) > 0
        newly = (distance < 0) & ((grown & ~inside) | (~shrunk & inside))
        distance[newly] = v - 1
    return np.where(distance >= 0, np.maximum(0, 255 - step * distance), 0).astype(int)


def grow(image: np.ndarray, seed: np.ndarray, tolerance: int) -> np.ndarray:
    """Pixels Grow selects at full strength from the `seed` selection on an RGB image."""
    image = np.asarray(image, int)
    values = image[seed]
    low, high = values.min(axis=0) - tolerance, values.max(axis=0) + tolerance
    alike = ((image >= low) & (image <= high)).all(axis=-1)
    taken = np.zeros(alike.shape, dtype=bool)
    queue = deque(zip(*np.nonzero(seed)))
    for y, x in queue:
        taken[y, x] = True
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < alike.shape[0] and 0 <= nx < alike.shape[1] and alike[ny, nx] and not taken[ny, nx]:
                taken[ny, nx] = True
                queue.append((ny, nx))
    return taken


COLOUR_RANGE_REACH_L = 0.38  # lightness difference per unit of fuzziness where coverage ends
COLOUR_RANGE_REACH_AB = 0.33  # a or b difference per unit of fuzziness where coverage ends


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """8-bit sRGB to CIE Lab (D50, Bradford), as colour management converts it."""
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    to_xyz = np.array([[0.4360747, 0.3850649, 0.1430804], [0.2225045, 0.7168786, 0.0606169],
                       [0.0139322, 0.0971045, 0.7141733]])
    t = (c @ to_xyz.T) / np.array([0.96422, 1.0, 0.82521])
    f = np.where(t > 216 / 24389, np.cbrt(t), (24389 / 27 * t + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """CIE Lab (D50) back to sRGB 0..255 (unrounded, unclipped): srgb_to_lab's inverse."""
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], axis=-1)
    t = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * np.array([0.96422, 1.0, 0.82521])
    to_xyz = np.array([[0.4360747, 0.3850649, 0.1430804], [0.2225045, 0.7168786, 0.0606169],
                       [0.0139322, 0.0971045, 0.7141733]])
    c = t @ np.linalg.inv(to_xyz).T
    c = np.where(c <= 0.04045 / 12.92, c * 12.92, 1.055 * np.sign(c) * np.abs(c) ** (1 / 2.4) - 0.055)
    return c * 255.0


def color_range(lab: np.ndarray, target: list[float], fuzziness: int) -> np.ndarray:
    """Select > Color Range around one sampled Lab colour. Coverage falls off as a raised cosine of
    the largest Lab channel difference, lightness measured against COLOUR_RANGE_REACH_L * fuzziness
    and a and b against COLOUR_RANGE_REACH_AB * fuzziness: a soft box, not a sphere. Shown directly
    on the harness's own axes image (patches stepping from mid grey along L, a, b and diagonals:
    half coverage at 0.19 * fuzziness along L, 0.165 along a or b, and sqrt 2 times that along the
    a-b diagonal); within 1.1 levels on average there at fuzziness 20 to 200, and on the 751-colour
    selection image within 1 up to fuzziness 40, 2.5 at 100 and 7 at 200 (Delta E 76, 94 and 2000,
    L1, p-norms and per-channel products all fit worse). The two reaches are fitted, not read."""
    d = np.abs(np.asarray(lab, float) - np.asarray(target, float))
    if fuzziness == 0:
        return np.where(d.max(axis=-1) < 1e-3, 255, 0)
    x = np.maximum(d[..., 0] / (COLOUR_RANGE_REACH_L * fuzziness),
                   np.maximum(d[..., 1], d[..., 2]) / (COLOUR_RANGE_REACH_AB * fuzziness))
    return _half_up(255 * np.where(x < 1, 0.5 + 0.5 * np.cos(np.pi * np.minimum(x, 1)), 0)).astype(int)