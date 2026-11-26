from __future__ import annotations

from fractions import Fraction

from scripts.adobe_observed_truth.illustrator import (
    device_pixels_per_point,
    document_to_screen,
    selected_anchor_indices,
)


# Canvas (100, 200)-(900, 800) on screen: its centre is (500, 500).
CANVAS = (100, 200, 900, 800)


def test_view_centre_lands_on_canvas_centre_and_y_up_maps_to_screen_up() -> None:
    # View centred on (200, -150) pt at 200%: a point 50 pt right of and 50 pt above
    # the centre is 100 px right of and 100 px above the canvas centre.
    point = document_to_screen(
        (250_000, -100_000), center_mpt=(200_000, -150_000), zoom_ppm=2_000_000, canvas=CANVAS
    )

    assert point == (600, 400)


def test_device_pixels_per_point_scales_offsets_on_a_high_dpi_display() -> None:
    # 100% zoom on a display drawing 1.5 device pixels per point: 10 pt right and
    # 8 pt below the centre is 15 px right and 12 px below the canvas centre.
    point = document_to_screen(
        (10_000, -8_000),
        center_mpt=(0, 0),
        zoom_ppm=1_000_000,
        canvas=CANVAS,
        device_pixels_per_point=Fraction(3, 2),
    )

    assert point == (515, 512)


def test_device_pixels_per_point_is_calibrated_from_visible_bounds_and_canvas_width() -> None:
    # At 200% the 800 px canvas shows 200 pt of document: 800 / (200 * 2) = 2 px per point.
    scale = device_pixels_per_point(
        view_bounds_mpt=(100_000, 50_000, 300_000, -100_000), zoom_ppm=2_000_000, canvas=CANVAS
    )

    assert scale == 2


def test_selected_anchors_exclude_neighbours_that_only_show_a_selected_handle() -> None:
    # Observed in Illustrator 30.8.2: selecting anchor 1 alone makes anchor 0 report
    # its right handle and anchor 2 its left handle as selected.
    points = [
        {"selected": "PathPointSelection.RIGHTDIRECTION"},
        {"selected": "PathPointSelection.ANCHORPOINT"},
        {"selected": "PathPointSelection.LEFTDIRECTION"},
        {"selected": "PathPointSelection.NOSELECTION"},
    ]

    assert selected_anchor_indices(points) == [1]
