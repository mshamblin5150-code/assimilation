"""Photoshop's tonal adjustments, rebuilt from transfer curves on the harness's own ramp
(adjust_probe; adjust-probe.jsonl, 37 adjustments run by their events).

- Curves: the natural cubic spline through the points (flat beyond the end points); exact.
- Levels: out = lo + (hi - lo) * clip((in - black) / (white - black)) ^ (1 / gamma), half up;
  exact for gamma <= 1, and above 1 exact from TOE_END levels past the black point up. Nearer
  black, gammas above 1 bend the curve below the power law by an amount that rises and falls
  with gamma (inputs it differs to: none at 1.1, 1 at 1.2, 22 at 1.5, 29 at 2, 22 at 3, 6 at 5,
  none at 9.99, where input 1 gives the power law's 146): not a slope cap, offset power or table
  chord (each tried): not settled. With the black or white point moved as well, a gamma other
  than 1 is within 1 level throughout (rounding in the input's rescaling).
- Threshold: 255 when in >= level. Posterize n: floor(in * n / 256) * 255 / (n - 1), rounded.
- Hue/Saturation lightness L: L > 0 moves toward white, floor(in + (255 - in) L/100); L < 0
  toward black, in (1 + L/100) half up.
- Exposure: in gamma-2.2 linear light, out = (x^2.2 * 2^exposure + offset) ^ (1 / (2.2 gamma)).
- Legacy Brightness/Contrast: brightness adds; contrast scales about the image's mean luma
  (Rec. 601), not 128, within 1 level.
- Brightness/Contrast (not legacy) and saturation-type changes are kept as measured curves only.
"""

from __future__ import annotations

import numpy as np

LEVELS = np.arange(256, dtype=float)
TOE_END = 30  # input levels past the black point from which Levels is the power law exactly


def _half_up(v: np.ndarray) -> np.ndarray:
    return np.floor(v + 0.5)


def curves(points: list[tuple[float, float]]) -> np.ndarray:
    x = np.array([p[0] for p in points], float)
    y = np.array([p[1] for p in points], float)
    n, h = len(x), np.diff(x)
    a = np.zeros((n, n))
    b = np.zeros(n)
    a[0, 0] = a[-1, -1] = 1
    for i in range(1, n - 1):
        a[i, i - 1], a[i, i], a[i, i + 1] = h[i - 1], 2 * (h[i - 1] + h[i]), h[i]
        b[i] = 3 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
    c = np.linalg.solve(a, b)
    out = np.where(LEVELS < x[0], y[0], y[-1]).astype(float)
    for k in range(n - 1):
        m = (LEVELS >= x[k]) & (LEVELS <= x[k + 1])
        t = LEVELS[m] - x[k]
        bk = (y[k + 1] - y[k]) / h[k] - h[k] * (2 * c[k] + c[k + 1]) / 3
        out[m] = y[k] + bk * t + c[k] * t ** 2 + (c[k + 1] - c[k]) / (3 * h[k]) * t ** 3
    return np.clip(_half_up(out), 0, 255).astype(int)


def levels(black: float, white: float, gamma: float, out_black: float = 0, out_white: float = 255) -> np.ndarray:
    t = np.clip((LEVELS - black) / (white - black), 0, 1) ** (1 / gamma)
    return _half_up(out_black + (out_white - out_black) * t).astype(int)


def threshold(level: int) -> np.ndarray:
    return np.where(LEVELS >= level, 255, 0)


def posterize(n: int) -> np.ndarray:
    return _half_up(np.floor(LEVELS * n / 256) * 255 / (n - 1)).astype(int)


def lightness(amount: int) -> np.ndarray:
    if amount >= 0:
        return np.floor(LEVELS + (255 - LEVELS) * amount / 100).astype(int)
    return _half_up(LEVELS * (1 + amount / 100)).astype(int)


def exposure(exposure: float, offset: float, gamma: float) -> np.ndarray:
    linear = (LEVELS / 255) ** 2.2 * 2 ** exposure + offset
    return np.clip(_half_up(255 * np.clip(linear, 0, None) ** (1 / (2.2 * gamma))), 0, 255).astype(int)


def legacy_brightness_contrast(brightness: int, contrast: int, mean_luma: float) -> np.ndarray:
    out = LEVELS + brightness
    if contrast:
        slope = (100 + contrast) / 100 if contrast < 0 else 100 / (100 - contrast)
        out = mean_luma + (out - mean_luma) * slope
    return np.clip(_half_up(out), 0, 255).astype(int)
