from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth import ps_pixels


def test_radial_profile_averages_the_four_axis_samples_at_each_radius() -> None:
    alpha = np.zeros((7, 7), dtype=np.uint8)
    alpha[3, 3] = 200
    # Radius 1: right, left, down, up.
    alpha[3, 4], alpha[3, 2], alpha[4, 3], alpha[2, 3] = 100, 60, 40, 0
    # Radius 3 sits on the border; radius 4 falls outside the array.
    alpha[3, 6] = 80

    assert ps_pixels.radial_profile(alpha, centre=(3, 3), radii=[0, 1, 2, 3, 4]) == [
        200,
        50,
        0,
        20,
        0,
    ]


def test_zero_radius_is_the_first_whole_radius_beyond_every_covered_pixel() -> None:
    alpha = np.zeros((9, 9), dtype=np.uint8)
    alpha[4, 4] = 255
    alpha[6, 6] = 1  # distance sqrt(8), about 2.83
    assert ps_pixels.zero_radius(alpha, centre=(4, 4)) == 3

    alpha[4, 7] = 9  # distance exactly 3 is still covered
    assert ps_pixels.zero_radius(alpha, centre=(4, 4)) == 4

    assert ps_pixels.zero_radius(np.zeros((9, 9), dtype=np.uint8), centre=(4, 4)) == 0


def test_nonzero_bounds_are_left_top_right_bottom_with_exclusive_right_and_bottom() -> None:
    mask = np.zeros((6, 8), dtype=np.uint8)
    mask[1, 2] = 255
    mask[4, 5] = 3

    assert ps_pixels.nonzero_bounds(mask) == [2, 1, 6, 5]
    assert ps_pixels.nonzero_bounds(np.zeros((6, 8), dtype=np.uint8)) is None


def test_mask_difference_counts_differing_pixels_and_the_largest_difference() -> None:
    before = np.array([[0, 255, 128], [10, 0, 0]], dtype=np.uint8)
    after = np.array([[0, 250, 255], [10, 0, 3]], dtype=np.uint8)

    assert ps_pixels.mask_difference(before, after) == {"differing_pixels": 3, "max_abs_difference": 127}
    assert ps_pixels.mask_difference(before, before) == {"differing_pixels": 0, "max_abs_difference": 0}


def test_changed_mask_marks_pixels_where_any_channel_differs() -> None:
    before = np.full((2, 3, 4), 255, dtype=np.uint8)
    after = before.copy()
    after[0, 0, 0] = 0  # red only
    after[1, 2, 3] = 254  # alpha only

    assert ps_pixels.changed_mask(before, after).tolist() == [
        [True, False, False],
        [False, False, True],
    ]


def test_edges_touched_names_each_canvas_edge_a_mask_reaches() -> None:
    mask = np.zeros((5, 6), dtype=bool)
    mask[2, 2] = True
    assert ps_pixels.edges_touched(mask) == []

    mask[4, 3] = True  # bottom row
    mask[1, 5] = True  # right column
    assert ps_pixels.edges_touched(mask) == ["right", "bottom"]

    mask[0, 0] = True
    assert ps_pixels.edges_touched(mask) == ["left", "top", "right", "bottom"]


def test_region_stats_summarise_a_left_top_right_bottom_box() -> None:
    alpha = np.full((4, 4), 255, dtype=np.uint8)
    alpha[1, 1], alpha[1, 2], alpha[2, 1], alpha[2, 2] = 10, 20, 30, 41

    assert ps_pixels.region_stats(alpha, [1, 1, 3, 3]) == {"pixels": 4, "min": 10, "max": 41, "mean": 25}


def test_dab_shape_tells_square_aliased_round_and_soft_dabs_apart() -> None:
    square = np.zeros((9, 9), dtype=np.uint8)
    square[2:6, 3:7] = 255
    assert ps_pixels.dab_shape(square) == "square"

    aliased_round = np.zeros((9, 9), dtype=np.uint8)
    aliased_round[3:6, 3:6] = 255
    aliased_round[2, 4] = aliased_round[6, 4] = aliased_round[4, 2] = aliased_round[4, 6] = 255
    assert ps_pixels.dab_shape(aliased_round) == "aliased-round"

    soft = aliased_round.copy()
    soft[2, 4] = 90
    assert ps_pixels.dab_shape(soft) == "soft"

    assert ps_pixels.dab_shape(np.zeros((9, 9), dtype=np.uint8)) == "empty"
