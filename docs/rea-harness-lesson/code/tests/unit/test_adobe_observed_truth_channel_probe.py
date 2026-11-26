"""The channel probe's specs and how a recorded selection is kept and read back."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.channel_probe import channel_specs, mask_of, measure


def test_a_recorded_mask_reads_back_with_its_counts() -> None:
    mask = np.zeros((300, 400), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    mask[10:20, 20] = 127
    row = measure(mask, 100)
    assert (mask_of(row) == mask).all()
    assert row["count_half"] == 100 and row["count_any"] == 110 and row["histogram_pixels"] == 100


def test_every_combine_mode_and_modify_operation_has_a_spec() -> None:
    ids = {s.item_id for s in channel_specs()}
    assert {"channel:combine:extend", "channel:combine:diminish", "channel:combine:intersect", "channel:round_trip"} <= ids
    assert "modify:ellipse:contract=5" in ids and "modify:rect:border=10" in ids and "count:ellipse:feather=25" in ids


def test_lab_to_srgb_inverts_the_colour_managed_conversion() -> None:
    import numpy as np

    from scripts.adobe_observed_truth.channel_model import lab_to_srgb, srgb_to_lab

    rgb = np.array([[119, 119, 119], [200, 40, 90], [10, 220, 30], [255, 255, 255], [0, 0, 0]], float)
    assert np.abs(lab_to_srgb(srgb_to_lab(rgb)) - rgb).max() < 1e-6


def test_the_colour_axes_image_holds_the_sample_and_steps_away_from_it_along_each_direction() -> None:
    import numpy as np

    from scripts.adobe_observed_truth.channel_model import srgb_to_lab
    from scripts.adobe_observed_truth.channel_probe import AXES_SAMPLE, axes_image

    image = np.array(axes_image())
    lab = srgb_to_lab(image.reshape(-1, 3).astype(float))
    distance = np.sqrt(((lab - np.array(AXES_SAMPLE)) ** 2).sum(-1))
    assert (distance < 1.0).mean() > 0.3  # the background is the sample
    assert distance.max() > 40
