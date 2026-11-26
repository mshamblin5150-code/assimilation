"""Photoshop's brush dynamics and pen mapping, rebuilt from the dynamics probes and the pen code.

Every dab's tip parameters were read straight from the tip kernels' buffers while Photoshop drew
(kernel_hooks.capture_script; brush-dynamics-probe.jsonl, 61 probes, 14,043 dabs), with pen
values fed through the brush pose so a scripted stroke carries them.

Pen input (Photoshop.exe's Windows Ink converter, the factory path): pressure is the pen's raw
value / 1000 when it reports pressure, else 1; tilt X and Y are raw degrees / 90, clamped to
+-1, Y negated; rotation is raw degrees. No curve is applied there. The brush pose's tilt is
+-100 for the same +-1. Pen.from_device and Pen.from_pose make the two.

Checked end to end with a real Windows pen input (pen_probe, pen-probe.jsonl: a synthetic pen
device, 66 strokes, each pen value held through a stroke): opacity is round(255 * raw / 1000)
exactly; pressure is not clamped, so the pointer's top raw values (1001-1024) paint up to 2.4%
over the set size; tilt is |degrees| / 90 on its magnitude (both axes, either sign); rotation
turns the tip counter-clockwise by the reported degrees. Two things the brush pose could not
show: when size follows tilt, the pen's pressure still scales the whole dab (tilt_size), and
with Smoothing on (26% measured) the dabs trail the pen by about 5 px at 2 px per 8 ms and, with
catch-up at the end off, the stroke stops about 6.5 px short of the pen's last point.

A variation (size, angle, roundness, opacity, flow, scatter, count...) has a control, fade steps,
a jitter and a minimum, all per cent:

- control off: 1; fade: 1 - (1 - minimum) * min(dab / steps, 1), so a fade with minimum 0 ends
  the stroke after `steps` dabs; pen pressure: minimum + (1 - minimum) * pressure;
- jitter J: the factor times (1 - J * u), u uniform on [0, 1), drawn per dab; the minimum does
  not bound plain jitter. Opacity and flow bytes are round(255 * value * factor).
- Pen tilt on size stretches the tip along its length to size * (1 + tilt scale * |tilt|), its
  width staying at size; on roundness, roundness * (1 - (1 - minimum roundness) * |tilt|); on
  angle, the tip turns to 90 degrees plus the tilt's direction. Rotation sets the angle to the
  pen's rotation. Angle jitter J turns the tip by J * 360 * (u - 0.5) degrees; roundness jitter
  draws it uniformly between the minimum roundness and 1 at J = 100.
- Scatter S (one axis) moves each dab across the stroke uniformly within +-S * diameter / 2;
  on both axes it moves it a uniform distance up to S * diameter / 2 in a uniform direction
  (scatter_both_axes: the across-stroke offsets of 153 dabs fit this, KS 0.077 against a 1%
  bound of 0.132; a uniform disc fits worse, 0.106, and a square is rejected, 0.153). Count N
  draws N dabs at each place.

Not settled (not claimed here): count jitter (100% barely changed the dab count), control and jitter
combined, stylus wheel and the direction sources (they read 0 under a pose), how Photoshop's
generator draws u (only the distributions are matched; a random stroke never repeats).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

OFF, FADE, PEN_PRESSURE, PEN_TILT, STYLUS_WHEEL = 0, 1, 2, 3, 4
ROTATION = 8  # the angle control that follows the pen's barrel rotation


@dataclass(frozen=True)
class Pen:
    """Pen state as the brush engine sees it: pressure 0..1, tilt -1..1 per axis, rotation degrees."""

    pressure: float = 1.0
    tilt_x: float = 0.0
    tilt_y: float = 0.0
    rotation: float = 0.0

    @classmethod
    def from_device(cls, pressure: int | None, tilt_x: int = 0, tilt_y: int = 0, rotation: int = 0) -> Pen:
        """From Windows Ink's pen info: pressure 0..1024 (None when the pen reports none), tilt degrees."""
        clamp = lambda v: max(-1.0, min(1.0, v / 90.0))
        return cls(1.0 if pressure is None else pressure * 0.001, clamp(tilt_x), -clamp(tilt_y), float(rotation))

    @classmethod
    def from_pose(cls, pressure: int = 100, tilt_x: int = 0, tilt_y: int = 0, angle: int = 0) -> Pen:
        """From a brush pose: pressure per cent, tilt -100..100, angle degrees."""
        return cls(pressure / 100.0, tilt_x / 100.0, tilt_y / 100.0, float(angle))

    @property
    def tilt(self) -> float:
        return min(1.0, math.hypot(self.tilt_x, self.tilt_y))


@dataclass(frozen=True)
class Variation:
    control: int = OFF
    jitter: float = 0.0  # per cent
    minimum: float = 0.0  # per cent
    steps: int = 25


def _control(variation: Variation, pen: Pen, dab: int) -> float:
    minimum = variation.minimum / 100.0
    if variation.control == FADE:
        return 1.0 - (1.0 - minimum) * min(dab / variation.steps, 1.0)
    if variation.control == PEN_PRESSURE:
        return minimum + (1.0 - minimum) * pen.pressure
    return 1.0


def _jittered(factor: float, variation: Variation, u: float) -> float:
    return factor * (1.0 - variation.jitter / 100.0 * u)


def size_factor(variation: Variation, pen: Pen, dab: int = 0, u: float = 0.0) -> float:
    """The dab's diameter as a fraction of the brush size (0: no dab)."""
    return _jittered(_control(variation, pen, dab), variation, u)


def dab_byte(value_percent: float, variation: Variation, pen: Pen, dab: int = 0, u: float = 0.0) -> int:
    """A dab's opacity or flow byte, as the tip kernel receives it."""
    return round(255 * value_percent / 100.0 * _jittered(_control(variation, pen, dab), variation, u))


def scatter_both_axes(scatter_percent: float, diameter: float, u_radius: float, u_angle: float) -> tuple[float, float]:
    """A dab's offset (along, across the stroke) under scatter on both axes, from two uniform draws."""
    radius = u_radius * scatter_percent / 100.0 * diameter / 2
    angle = 2 * math.pi * u_angle
    return radius * math.cos(angle), radius * math.sin(angle)


def tilt_size(size: float, tilt_scale: float, pen: Pen) -> tuple[float, float]:
    """Length and width of a tip whose size follows pen tilt: the pen's pressure still scales the
    whole dab, and pressure over 1 (the pointer's top values) lengthens the stretch by itself again
    (fitted to the one such pressure there is, 1.024)."""
    stretch = 1.0 + tilt_scale / 100.0 * pen.tilt * max(1.0, pen.pressure)
    return size * pen.pressure * stretch, size * pen.pressure


def roundness_factor(variation: Variation, pen: Pen, minimum_roundness: float, u: float = 0.0) -> float:
    """The dab's roundness as a fraction of the tip's own."""
    floor = minimum_roundness / 100.0
    factor = 1.0 - (1.0 - floor) * pen.tilt if variation.control == PEN_TILT else 1.0
    return factor * (1.0 - (1.0 - floor) * variation.jitter / 100.0 * u)


def tip_angle(base: float, variation: Variation, pen: Pen, u: float = 0.5) -> float:
    """The dab's tip angle in degrees, counter-clockwise."""
    if variation.control == PEN_TILT:
        angle = 90.0 + math.degrees(math.atan2(pen.tilt_y, pen.tilt_x))
    elif variation.control == ROTATION:
        angle = pen.rotation
    else:
        angle = base
    return angle + variation.jitter / 100.0 * 360.0 * (u - 0.5)


def scatter_reach(diameter: float, scatter: float) -> float:
    """How far (pixels) one-axis scatter can move a dab across the stroke, either side."""
    return scatter / 100.0 * diameter / 2.0
