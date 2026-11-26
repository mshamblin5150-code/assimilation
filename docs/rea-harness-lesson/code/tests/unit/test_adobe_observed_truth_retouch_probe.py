"""The retouch probe's own image and what it reads back from a painted copy of it."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.retouch_probe import COLOUR_ROW, GREY_ROW, RAMP_LEFT, measure, ramp_image, retouch_specs


def test_the_ramp_image_holds_every_grey_and_a_red_to_white_saturation_ramp() -> None:
    image = np.asarray(ramp_image())
    assert image[GREY_ROW, RAMP_LEFT:RAMP_LEFT + 256, 0].tolist() == list(range(256))
    assert image[COLOUR_ROW, RAMP_LEFT, :].tolist() == [255, 0, 0]
    assert image[COLOUR_ROW, RAMP_LEFT + 255, :].tolist() == [255, 255, 255]


def test_an_untouched_ramp_reads_back_as_the_identity_curve() -> None:
    pixels = np.dstack([np.asarray(ramp_image()), np.full((300, 400), 255, np.uint8)])
    read = measure(pixels)
    assert read["grey"] == list(range(256)) and read["grey_channels_equal"]
    assert read["colour"][0] == [255] * 256 and read["colour"][1] == list(range(256))


def test_every_dodge_and_burn_range_exposure_and_legacy_switch_has_a_spec() -> None:
    ids = {s.item_id for s in retouch_specs()}
    assert len(ids) == 57
    assert "retouch:burn:shadows:exposure=100:legacy" in ids and "retouch:sponge:saturate:flow=25:vibrance" in ids
