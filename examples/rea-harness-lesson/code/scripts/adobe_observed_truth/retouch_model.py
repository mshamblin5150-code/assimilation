"""Photoshop's Dodge, Burn and Sponge rebuilt as transfer curves from the retouch probe.

retouch-probe.jsonl holds 48 curves: one hard dab of size 400 over the harness's own grey and saturation
ramps (retouch_probe), so each row is the tool's output for every input level. The tools paint
their dab mask with the airbrush tip kernel (kernel hooks: AirbrushTip, the exposure or flow as
its flow byte) and the tonal change is Photoshop.exe's; it is rebuilt here from the curves.

Legacy (protect tones off), with s = 0.196 * exposure (50/255 per unit) and x in 0..1:
dodge shadows x + s(1 - x); burn highlights x(1 - s); dodge highlights x / (1 - s'); burn
shadows (x - s') / (1 - s') with s' = 0.191 * exposure; midtones are gammas, dodge x^(1/(1 + m)),
burn x^(1 + m) with m about 0.29 * exposure (within 3 and 4 levels). Others within 1 level.

Protect tones (the default): out = in + exposure * D(in), one full-strength delta curve D per
tool and range (measured; the 25% curve predicts 50% and 100% within 2 levels once its
extrapolation is clipped). D's closed form is not known.

Sponge, legacy desaturate: each channel moves toward the luma Y = 0.30R + 0.59G + 0.11B by
0.196 * flow. Greys never change. Legacy saturate (on a muted hue ramp with room to rise): each
channel moves away from the luma by 0.392 * flow, twice desaturate's step; within 1 level.
Not settled: the vibrance variants (kept as measured curves). Fitted the same way, vibrance
saturate scales the colour by about 1 + 0.315 * flow and lifts the luma (+7 levels at 100%),
vibrance desaturate by about 1 - 0.231 * flow and lowers it (-3 at 100%), 4 to 14 levels off:
not a luma-relative gain.
"""

from __future__ import annotations

import numpy as np

STRENGTH = 50 / 255  # per unit of exposure or flow
LEGACY_TOLERANCE = {("dodge", "shadows"): 1, ("dodge", "highlights"): 1, ("dodge", "midtones"): 3,
                    ("burn", "shadows"): 1, ("burn", "highlights"): 1, ("burn", "midtones"): 4}
_DIVIDING = 0.1912  # dodge highlights and burn shadows, per unit of exposure
_GAMMA = {"dodge": 0.2931, "burn": 0.2825}


def legacy(tool: str, band: str, levels: np.ndarray, exposure: float) -> np.ndarray:
    """Legacy Dodge or Burn on 8-bit levels at `exposure` per cent, fully covered."""
    x = levels / 255.0
    e = exposure / 100.0
    s, d, m = STRENGTH * e, _DIVIDING * e, _GAMMA[tool] * e
    if (tool, band) == ("dodge", "shadows"):
        y = x + s * (1 - x)
    elif (tool, band) == ("burn", "highlights"):
        y = x * (1 - s)
    elif (tool, band) == ("dodge", "highlights"):
        y = x / (1 - d)
    elif (tool, band) == ("burn", "shadows"):
        y = (x - d) / (1 - d)
    elif (tool, band) == ("dodge", "midtones"):
        y = x ** (1 / (1 + m))
    else:
        y = x ** (1 + m)
    return np.clip(np.round(np.clip(y, 0, 1) * 255), 0, 255).astype(int)


def full_strength_delta(levels: np.ndarray, measured: np.ndarray, exposure: float) -> np.ndarray:
    """The full-strength delta curve read from one measured curve at `exposure` per cent."""
    return (np.asarray(measured, float) - levels) * 100.0 / exposure


def protect_tones(levels: np.ndarray, delta: np.ndarray, exposure: float) -> np.ndarray:
    """Dodge or Burn with protect tones at `exposure` per cent, from its full-strength delta."""
    return np.clip(np.round(levels + delta * exposure / 100.0), 0, 255).astype(int)


def legacy_saturate(rgb: np.ndarray, flow: float) -> np.ndarray:
    """Legacy Sponge saturate on 8-bit RGB rows at `flow` per cent, fully covered: each channel
    moves away from the luma by twice desaturate's step."""
    rgb = np.asarray(rgb, float)
    luma = rgb @ np.array([0.30, 0.59, 0.11])
    out = rgb + 2 * STRENGTH * flow / 100.0 * (rgb - luma[:, None])
    return np.clip(np.floor(out + 0.5), 0, 255).astype(int)


def legacy_desaturate(rgb: np.ndarray, flow: float) -> np.ndarray:
    """Legacy Sponge desaturate on 8-bit RGB rows at `flow` per cent, fully covered."""
    rgb = np.asarray(rgb, float)
    luma = rgb @ np.array([0.30, 0.59, 0.11])
    out = rgb + STRENGTH * flow / 100.0 * (luma[:, None] - rgb)
    return np.clip(np.round(out), 0, 255).astype(int)
