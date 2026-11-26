"""A rebuild of Photoshop's round brush from the brush probe's measurements: dab falloff, dab
placement, flow build-up and the opacity cap."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.brush_model import dab_centres, stroke


def test_dabs_land_every_size_times_spacing_from_the_start_and_never_closer_than_a_pixel() -> None:
    assert dab_centres((40.5, 150.5), (103.5, 150.5), size=21, spacing=150) == [(40.5, 150.5), (72.0, 150.5), (103.5, 150.5)]
    dense = dab_centres((40.5, 150.5), (50.5, 150.5), size=21, spacing=1)  # 0.21 px asked: 1 px kept
    assert [x for x, _ in dense] == [40.5 + i for i in range(11)]


def test_a_hard_dab_is_solid_to_its_radius_and_a_soft_one_reaches_well_beyond_it() -> None:
    options = {"size_px": 99, "hardness": 100, "opacity": 100, "flow": 100, "spacing": 25}
    hard = stroke([(200, 150)], options, shape=(300, 400))
    soft = stroke([(200, 150)], {**options, "hardness": 0}, shape=(300, 400))

    assert hard[150, 200 + 47] == 255 and hard[150, 200 + 51] == 0
    assert soft[150, 200 + 70] > 0  # 1.4 x the radius


def test_flow_builds_up_per_dab_and_opacity_caps_the_stroke() -> None:
    base = {"size_px": 21, "hardness": 100, "opacity": 100, "flow": 25, "spacing": 25}
    line = [(40, 150), (360, 150)]

    flowed = stroke(line, base, shape=(300, 400))
    capped = stroke(line, {**base, "flow": 100, "opacity": 50}, shape=(300, 400))
    both = stroke(line, {**base, "opacity": 50}, shape=(300, 400))

    assert flowed[150, 200] == round(255 * (1 - 0.75 ** 4))  # four dabs cover each pixel at 25% spacing
    assert capped[150, 200] == 128 and np.all(capped <= 128)
    assert both[150, 200] == round(0.5 * 255 * (1 - 0.75 ** 4))


def test_simulated_pressure_tapers_size_or_opacity_from_nothing_to_full_at_the_middle() -> None:
    base = {"size_px": 21, "hardness": 100, "opacity": 100, "flow": 100, "spacing": 25}
    line = [(40, 150), (360, 150)]

    sized = stroke(line, {**base, "pressure": "size"}, shape=(300, 400))
    faded = stroke(line, {**base, "pressure": "opacity"}, shape=(300, 400))

    widths = (sized > 127).sum(axis=0)
    assert widths[42] == 0 and 9 <= widths[120] <= 12 and widths[200] >= 19  # a quarter, then all, of 21
    assert faded[150, 42] < 40 and 120 <= faded[150, 120] <= 160 and faded[150, 200] >= 240
