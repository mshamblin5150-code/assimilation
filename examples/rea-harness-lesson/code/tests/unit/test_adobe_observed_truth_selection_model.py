"""Magic Wand, Paint Bucket and Feather rebuilt from the selection probe's measurements."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.selection_model import feather, matches, wand


def test_a_pixel_matches_when_the_spread_of_zero_and_its_channel_differences_is_within_tolerance() -> None:
    seed = np.array([128, 128, 128])
    pixels = np.array([[[160, 160, 160], [161, 128, 128], [144, 144, 128], [144, 112, 128]]], dtype=np.uint8)

    # grey 32 away: spread 32; red 33 away: 33; red and green 16 the same way: 16; opposite ways: 32
    assert matches(pixels, seed, tolerance=32).tolist() == [[True, False, True, True]]
    assert matches(pixels, seed, tolerance=20).tolist() == [[False, False, True, False]]


def test_contiguous_means_joined_through_the_four_side_neighbours() -> None:
    image = np.full((5, 5, 3), 200, dtype=np.uint8)
    image[1, 1] = image[2, 2] = image[1, 3] = 100  # (2, 2) touches (1, 1) only at a corner

    joined = wand(image, (1, 1), tolerance=0, contiguous=True, anti_alias=False)
    anywhere = wand(image, (1, 1), tolerance=0, contiguous=False, anti_alias=False)

    assert joined.sum() == 255 and joined[1, 1] == 255
    assert anywhere.sum() == 3 * 255


def test_anti_alias_adds_one_partly_selected_pixel_around_the_selection() -> None:
    ramp = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2).repeat(3, axis=0)

    hard = wand(ramp, (128, 1), tolerance=10, contiguous=True, anti_alias=False)[1]
    soft = wand(ramp, (128, 1), tolerance=10, contiguous=True, anti_alias=True)[1]

    assert np.nonzero(hard)[0].tolist() == list(range(118, 139))
    assert 0 < soft[117] < 255 and 0 < soft[139] < 255 and soft[116] == 0


def test_feather_is_a_gaussian_blur_as_wide_as_its_radius() -> None:
    box = np.zeros((200, 200), dtype=np.uint8)
    box[50:150, 50:150] = 255

    soft = feather(box, 5)

    assert soft[100, 50] in range(134, 141)  # the first pixel in, its centre half a pixel past the edge
    assert soft[100, 45] in range(44, 52)  # 4.5 px out: 255 * Phi(-4.5 / 5.1)
    assert soft[100, 100] == 255
