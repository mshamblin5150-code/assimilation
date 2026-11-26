"""Photoshop's 8-bit layer blend modes, rebuilt from full truth tables (layer_probe).

blend-probe.jsonl holds, per mode, the composite of a top layer over a base for every pair of
grey levels (256 x 256) and for 64 x 64 pseudo-random colour pairs. Every separable mode below
is exact on all 65,536 grey pairs and per channel in colour. Rounding is half up throughout
(floor(v + 0.5)), which is what separates several modes from textbook formulas. a is the base
level, b the top's, both 0..255:

- multiply round(ab/255) (the kernel's own add-128 path), screen 255 - round((255-a)(255-b)/255),
  overlay: a < 128 round(2ab/255), else 255 - round(2(255-a)(255-b)/255); hard light: b < 128
  multiply(a, 2b), else
  screen(a, 2b - 256); exclusion a + b - 2 round(ab/255); linear light a + 2b - 256 (clipped);
- colour dodge round(255a / (255 - b)) (a = 0 gives 0, b = 255 gives 255), colour burn
  255 - round(255(255 - a) / b) (a = 255 gives 255, b = 0 gives 0), divide round(255a / b)
  (b = 0 gives 0 for a = 0, else 255);
- pin light and vivid light split the top as round(b * 255/128) under 128 and
  round((b - 128) * 255/127) above; vivid light's burn of 0 is 0 and dodge by 255 is 255
  whatever the base; hard mix is 255 when a + b > 255, or a + b = 255 with b < 128;
- soft light: the W3C formula (dark bases use ((16a - 12)a + 4)a) is right within 1 level, off
  by 1 on 15% of pairs.

Opacity mixes by its stored byte: 50% is 128, out = a + round((blend - a) * 128/255).
Hue, saturation, colour and luminosity are the W3C non-separable formulas with Rec. 601 weights
(0.30, 0.59, 0.11), within 3 to 6 levels; darker and lighter colour pick by the same luma, all
but near ties.
"""

from __future__ import annotations

import numpy as np

SEPARABLE = ("normal", "darken", "multiply", "colorBurn", "linearBurn", "lighten", "screen", "colorDodge",
             "linearDodge", "overlay", "softLight", "hardLight", "vividLight", "linearLight", "pinLight", "hardMix",
             "difference", "exclusion", "blendSubtraction", "blendDivide")
SEPARABLE = tuple(m for m in SEPARABLE if m != "softLight")  # soft light is within 1 level, not exact
LUMA = np.array([0.30, 0.59, 0.11])


def _half_up(v: np.ndarray) -> np.ndarray:
    return np.floor(v + 0.5)


def _dodge(a: np.ndarray, s: np.ndarray, full_first: bool = False) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        q = np.minimum(255, _half_up(255 * a / (255 - s)))
    if full_first:
        return np.where(s >= 255, 255, np.where(a == 0, 0, q))
    return np.where(a == 0, 0, np.where(s >= 255, 255, q))


def _burn(a: np.ndarray, s: np.ndarray, zero_first: bool = False) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        q = 255 - np.minimum(255, _half_up(255 * (255 - a) / s))
    if zero_first:
        return np.where(s <= 0, 0, np.where(a >= 255, 255, q))
    return np.where(a >= 255, 255, np.where(s <= 0, 0, q))


def _separable(mode: str, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    multiply = lambda x, y: _half_up(x * y / 255)
    screen = lambda x, y: 255 - _half_up((255 - x) * (255 - y) / 255)
    lower, upper = _half_up(b * 255 / 128), _half_up((b - 128) * 255 / 127)
    if mode == "normal":
        return b
    if mode == "darken":
        return np.minimum(a, b)
    if mode == "lighten":
        return np.maximum(a, b)
    if mode == "multiply":
        return multiply(a, b)
    if mode == "screen":
        return screen(a, b)
    if mode == "hardLight":
        return np.where(b < 128, multiply(a, 2 * b), screen(a, 2 * b - 256))
    if mode == "overlay":
        return np.where(a < 128, _half_up(2 * a * b / 255), 255 - _half_up(2 * (255 - a) * (255 - b) / 255))
    if mode == "colorDodge":
        return _dodge(a, b)
    if mode == "colorBurn":
        return _burn(a, b)
    if mode == "linearBurn":
        return a + b - 255
    if mode == "linearDodge":
        return a + b
    if mode == "linearLight":
        return a + 2 * b - 256
    if mode == "vividLight":
        return np.where(b < 128, _burn(a, lower, zero_first=True), _dodge(a, upper, full_first=True))
    if mode == "pinLight":
        return np.where(b < 128, np.minimum(a, lower), np.maximum(a, upper))
    if mode == "hardMix":
        return np.where((a + b > 255) | ((a + b == 255) & (b < 128)), 255, 0)
    if mode == "difference":
        return np.abs(a - b)
    if mode == "exclusion":
        return a + b - 2 * multiply(a, b)
    if mode == "blendSubtraction":
        return a - b
    if mode == "blendDivide":
        with np.errstate(divide="ignore", invalid="ignore"):
            q = np.minimum(255, _half_up(255 * a / b))
        return np.where(b <= 0, np.where(a == 0, 0, 255), q)
    if mode == "softLight":
        x, y = a / 255, b / 255
        d = np.where(x <= 0.25, ((16 * x - 12) * x + 4) * x, np.sqrt(x))
        return _half_up(255 * np.where(y <= 0.5, x - (1 - 2 * y) * x * (1 - x), x + (2 * y - 1) * (d - x)))
    raise ValueError(f"not a separable mode: {mode}")


def _lum(c: np.ndarray) -> np.ndarray:
    return c @ LUMA


def _clip_colour(c: np.ndarray) -> np.ndarray:
    l = _lum(c)[..., None]
    n, x = c.min(-1, keepdims=True), c.max(-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(n < 0, l + (c - l) * l / (l - n), c)
        c = np.where(x > 1, l + (c - l) * (1 - l) / (x - l), c)
    return c


def _set_lum(c: np.ndarray, l: np.ndarray) -> np.ndarray:
    return _clip_colour(c + (l - _lum(c))[..., None])


def _set_sat(c: np.ndarray, s: np.ndarray) -> np.ndarray:
    high, low = c.max(-1, keepdims=True), c.min(-1, keepdims=True)
    spread = high - low
    return np.where(spread > 0, (c - low) * s[..., None] / np.where(spread > 0, spread, 1), 0)


def _mixing(mode: str, base: np.ndarray, top: np.ndarray) -> np.ndarray:
    cb, cs = base / 255.0, top / 255.0
    sat = lambda c: c.max(-1) - c.min(-1)
    if mode == "hue":
        out = _set_lum(_set_sat(cs, sat(cb)), _lum(cb))
    elif mode == "saturation":
        out = _set_lum(_set_sat(cb, sat(cs)), _lum(cb))
    elif mode == "color":
        out = _set_lum(cs, _lum(cb))
    elif mode == "luminosity":
        out = _set_lum(cb, _lum(cs))
    elif mode == "darkerColor":
        out = np.where((_lum(cs) < _lum(cb))[..., None], cs, cb)
    elif mode == "lighterColor":
        out = np.where((_lum(cs) > _lum(cb))[..., None], cs, cb)
    else:
        raise ValueError(f"not a blend mode: {mode}")
    return _half_up(np.clip(out, 0, 1) * 255)


def blend(mode: str, base: np.ndarray, top: np.ndarray) -> np.ndarray:
    """The blended levels of `top` over `base` (8-bit arrays; colour ones end in 3 channels)."""
    a, b = np.asarray(base, float), np.asarray(top, float)
    if mode in ("hue", "saturation", "color", "luminosity", "darkerColor", "lighterColor"):
        return _mixing(mode, a, b).astype(np.uint8)
    return np.clip(_separable(mode, a, b), 0, 255).astype(np.uint8)


def composite(mode: str, base: np.ndarray, top: np.ndarray, opacity: float) -> np.ndarray:
    """The layer composited at `opacity` per cent, stored as a byte."""
    a = np.asarray(base, float)
    byte = _half_up(np.asarray(opacity) * 255 / 100)
    return np.clip(a + _half_up((blend(mode, base, top) - a) * byte / 255), 0, 255).astype(np.uint8)
