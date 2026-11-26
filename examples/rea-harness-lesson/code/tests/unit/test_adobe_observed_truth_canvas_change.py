"""What a command did to the pixels, measured from before and after images."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.ps_pixels import canvas_change, pixels_sha256


def blank(height: int = 4, width: int = 4) -> np.ndarray:
    image = np.zeros((height, width, 4), dtype=np.uint8)
    image[..., 3] = 255
    return image


def test_identical_results_share_a_hash_and_one_changed_pixel_or_size_does_not() -> None:
    changed = blank()
    changed[1, 2, 0] = 1

    assert pixels_sha256(blank()) == pixels_sha256(blank())
    assert len({pixels_sha256(blank()), pixels_sha256(changed), pixels_sha256(blank(4, 8))}) == 3


def test_an_untouched_canvas_reports_no_change() -> None:
    change = canvas_change(blank(), blank())

    assert (change["changed_fraction"], change["changed_box"]) == (0.0, None)


def test_one_changed_pixel_is_located_and_measured_per_channel() -> None:
    after = blank()
    after[1, 2, 0] = 200  # red at x=2, y=1

    change = canvas_change(blank(), after)

    assert change["changed_fraction"] == 0.0625  # 1 of 16 pixels
    assert change["changed_box"] == [2, 1, 2, 1]  # x0, y0, x1, y1
    assert change["mean_delta"] == {"r": 12.5, "g": 0.0, "b": 0.0, "a": 0.0}


def test_a_resized_canvas_reports_both_sizes_instead_of_a_pixel_comparison() -> None:
    change = canvas_change(blank(4, 4), blank(2, 6))

    assert change == {"size_before": [4, 4], "size_after": [6, 2]}


def test_change_is_reported_for_each_named_region_of_the_image() -> None:
    after = blank()
    after[:, :2, 1] = 90  # the whole left half

    change = canvas_change(blank(), after, regions={"left": (0, 4, 0, 2), "right": (0, 4, 2, 4)})

    assert change["regions"] == {"left": 1.0, "right": 0.0}
