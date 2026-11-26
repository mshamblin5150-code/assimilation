"""Clicking inside a full-window workspace (Vanishing Point, Liquify): find the known test image
in a screenshot of the workspace, then turn image points into screen points."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.input_plan import MouseDown, MouseMove, MouseUp
from scripts.adobe_observed_truth.test_images import chart
from scripts.adobe_observed_truth.workspace import (
    Placement,
    likeness,
    locate,
    plane_clicks,
    to_screen,
    trim_frame,
)

GREY = (79, 79, 79)  # Vanishing Point's background, from the 2026-11-09 capture


def workspace_with_chart(left: int, top: int, scale: float = 1.0) -> np.ndarray:
    shot = np.zeros((900, 1400, 3), dtype=np.uint8)
    shot[...] = GREY
    image = chart().convert("RGB")
    if scale != 1.0:
        image = image.resize((round(600 * scale), round(400 * scale)))
    shot[top : top + image.height, left : left + image.width] = np.asarray(image)
    return shot


def test_the_image_is_found_where_the_workspace_shows_it() -> None:
    assert locate(workspace_with_chart(300, 150), search=(0, 0, 1400, 900)) == Placement(300, 150, 600, 400)


def test_the_image_is_found_at_any_zoom() -> None:
    assert locate(workspace_with_chart(500, 200, 0.5), search=(0, 0, 1400, 900)) == Placement(500, 200, 300, 200)


def test_toolbars_outside_the_search_area_are_ignored() -> None:
    shot = workspace_with_chart(300, 150)
    shot[0:40, :] = (200, 200, 200)  # a toolbar strip along the top

    assert locate(shot, search=(0, 50, 1400, 900)) == Placement(300, 150, 600, 400)


def test_the_found_area_looks_like_the_known_image() -> None:
    shot = workspace_with_chart(300, 150)

    assert likeness(shot, Placement(300, 150, 600, 400), chart()) > 0.95


def test_something_else_in_the_workspace_does_not_look_like_the_image() -> None:
    shot = workspace_with_chart(300, 150)
    shot[150:550, 300:900] = np.random.default_rng(1).integers(0, 256, (400, 600, 3))

    assert likeness(shot, Placement(300, 150, 600, 400), chart()) < 0.6


def test_an_image_point_becomes_a_screen_point_through_the_placement_and_window_origin() -> None:
    placement = Placement(300, 150, 300, 200)  # the 600 x 400 image shown at 50%

    assert to_screen((100, 100), placement, image_size=(600, 400), window_origin=(10, 20)) == (360, 220)


def test_a_thin_dark_frame_drawn_around_the_image_is_trimmed_off() -> None:
    # Vanishing Point draws a 1-2 px frame round the image (found 569 x 603 for a 566 x 600 icon).
    shot = workspace_with_chart(300, 150)
    shot[148:552, 298:902][[0, 1, -2, -1], :] = (20, 20, 20)
    shot[148:552, 298:902][:, [0, 1, -2, -1]] = (20, 20, 20)

    assert trim_frame(shot, Placement(298, 148, 604, 404)) == Placement(300, 150, 600, 400)


def test_a_light_uniform_image_edge_such_as_a_white_background_is_kept() -> None:
    shot = np.full((400, 400, 3), 79, dtype=np.uint8)
    shot[100:300, 100:300] = 255  # a white-backed image's edge

    assert trim_frame(shot, Placement(100, 100, 200, 200)) == Placement(100, 100, 200, 200)


def test_a_perspective_plane_is_four_clicks_on_an_inset_rectangle_of_the_image() -> None:
    # Vanishing Point: "Click the four corners of a perspective plane..."; an inset rectangle
    # is always a valid plane. The 600 x 400 chart shown at 100% at (300, 150).
    events = plane_clicks(Placement(300, 150, 600, 400), image_size=(600, 400), window_origin=(0, 0))

    moves = [(e.x, e.y) for e in events if isinstance(e, MouseMove)]
    assert moves == [(451, 251), (751, 251), (751, 451), (451, 451)]
    assert [type(e) for e in events[:3]] == [MouseMove, MouseDown, MouseUp]