"""Where on an app's canvas nothing else lies over it, and the view that puts a drawing there."""

from __future__ import annotations

from scripts.adobe_observed_truth.canvas_room import free_rect, view_for


def test_the_free_rectangle_is_the_largest_part_of_the_canvas_no_window_covers() -> None:
    canvas = (0, 0, 1000, 600)
    covers = [(0, 0, 400, 600), (700, 0, 1000, 300)]  # a panel down the left, one top right
    left, top, right, bottom = free_rect(canvas, covers, cell=10)
    assert (left, top, right, bottom) == (400, 0, 700, 600) or (left, top, right, bottom) == (400, 300, 1000, 600)
    assert (right - left) * (bottom - top) == 180000


def test_with_nothing_over_it_the_whole_canvas_is_free() -> None:
    assert free_rect((10, 20, 210, 120), [], cell=10) == (10, 20, 210, 120)


def test_the_view_puts_the_drawing_inside_the_free_rectangle_with_a_margin() -> None:
    canvas = (0, 0, 1000, 600)
    free = (400, 0, 700, 600)
    centre_mpt, zoom_ppm = view_for((50, 100, 250, 200), free, canvas, device_pixels_per_point=1.0, margin=0.1)
    zoom = zoom_ppm / 1_000_000

    def to_screen(x: float, y: float) -> tuple[float, float]:  # as document_to_screen does
        return 500 + (x * 1000 - centre_mpt[0]) * zoom / 1000, 300 - (y * 1000 - centre_mpt[1]) * zoom / 1000

    for x, y in ((50, 100), (250, 200), (50, 200), (250, 100)):
        sx, sy = to_screen(x, y)
        assert 400 + 30 - 0.5 <= sx <= 700 - 30 + 0.5 and 0 + 60 - 0.5 <= sy <= 600 - 60 + 0.5  # rounding


def test_points_over_another_window_are_named() -> None:
    from scripts.adobe_observed_truth.canvas_room import points_on_canvas

    owner = {(1, 1): 7, (2, 2): 9}
    assert points_on_canvas([(1, 1), (2, 2)], owner.get, canvas_window=7) == [(2, 2)]
