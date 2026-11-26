"""Document <-> screen mapping on hand-built views.

A view maps view units (screen pixels from the view's top-left, divided by the
monitor scale) to document pixels: doc = (a*u + c*v + tx, b*u + d*v + ty).
Expected values below are worked by hand from that definition.
"""

from __future__ import annotations

from scripts.adobe_observed_truth.canvas import View, document_to_screen, screen_to_document


def view(*, bounds, matrix, dpi_scale, zoom=1.0, size=(400, 300)) -> View:
    return View(
        zoom=zoom,
        document_size=size,
        view_bounds=bounds,
        view_to_document=matrix,
        dpi_scale=dpi_scale,
        rulers_visible=False,
    )


def test_at_100_percent_on_an_unscaled_monitor_a_document_pixel_is_one_screen_pixel() -> None:
    # doc = u - 20, so u = doc + 20; screen x = 100 + u. Likewise y = 50 + (doc + 10).
    at_100 = view(bounds=(100, 50, 900, 650), matrix=(1.0, 0.0, 0.0, 1.0, -20.0, -10.0), dpi_scale=1.0)

    assert document_to_screen(at_100, 0, 0) == (120, 60)
    assert document_to_screen(at_100, 30, 40) == (150, 100)


def test_at_50_percent_on_a_125_percent_monitor_100_document_pixels_span_50_screen_pixels() -> None:
    # Photoshop's scale is monitor scale / zoom = 1.25 / 0.5 = 2.5 document pixels per view unit.
    # doc 100: u = (100 + 100) / 2.5 = 80, screen x = 200 + 80 * 1.25 = 300.
    # doc 50:  v = (50 + 50) / 2.5 = 40,   screen y = 100 + 40 * 1.25 = 150.
    # doc 0:   u = 100 / 2.5 = 40,          screen x = 200 + 50 = 250.
    at_50 = view(
        bounds=(200, 100, 1000, 700), matrix=(2.5, 0.0, 0.0, 2.5, -100.0, -50.0), dpi_scale=1.25, zoom=0.5
    )

    assert document_to_screen(at_50, 100, 50) == (300, 150)
    assert document_to_screen(at_50, 0, 50) == (250, 150)


def test_at_200_percent_on_a_125_percent_monitor_one_document_pixel_spans_two_screen_pixels() -> None:
    # Scale 1.25 / 2 = 0.625. doc 60: u = (60 - 10) / 0.625 = 80, x = 0 + 80 * 1.25 = 100.
    # doc 45: v = (45 - 20) / 0.625 = 40, y = 40 * 1.25 = 50. doc 61 lands 2 pixels right: 102.
    at_200 = view(bounds=(0, 0, 800, 600), matrix=(0.625, 0.0, 0.0, 0.625, 10.0, 20.0), dpi_scale=1.25, zoom=2.0)

    assert document_to_screen(at_200, 60, 45) == (100, 50)
    assert document_to_screen(at_200, 61, 45) == (102, 50)


def test_a_scrolled_view_offsets_by_the_document_point_at_the_view_origin() -> None:
    # A 3000x2000 document at 100% scrolled so doc (600, 450) sits at the view's top-left (u = v = 0).
    # doc 1000: u = (1000 - 600) / 1.25 = 320, x = 133 + 320 * 1.25 = 533.
    # doc 900:  v = (900 - 450) / 1.25 = 360,  y = 164 + 360 * 1.25 = 614.
    scrolled = view(
        bounds=(133, 164, 1965, 1278),
        matrix=(1.25, 0.0, 0.0, 1.25, 600.0, 450.0),
        dpi_scale=1.25,
        size=(3000, 2000),
    )

    assert document_to_screen(scrolled, 600, 450) == (133, 164)
    assert document_to_screen(scrolled, 1000, 900) == (533, 614)


def test_points_outside_the_canvas_and_the_view_still_map() -> None:
    # Same 200% view as above. doc -10: u = (-10 - 10) / 0.625 = -32, x = -40.
    # doc -20: v = (-20 - 20) / 0.625 = -64, y = -80. Beyond a 400x300 canvas: doc 410 -> u = 640, x = 800.
    at_200 = view(bounds=(0, 0, 800, 600), matrix=(0.625, 0.0, 0.0, 0.625, 10.0, 20.0), dpi_scale=1.25, zoom=2.0)

    assert document_to_screen(at_200, -10, -20) == (-40, -80)
    assert document_to_screen(at_200, 410, 20) == (800, 0)


def test_a_screen_pixel_maps_to_the_document_point_under_its_top_left_corner() -> None:
    # Same 50% view. Screen (300, 150): u = 100 / 1.25 = 80, doc x = 2.5 * 80 - 100 = 100;
    # v = 50 / 1.25 = 40, doc y = 2.5 * 40 - 50 = 50.
    # Screen (201, 100): u = 1 / 1.25 = 0.8, doc x = 2 - 100 = -98; v = 0, doc y = -50.
    at_50 = view(
        bounds=(200, 100, 1000, 700), matrix=(2.5, 0.0, 0.0, 2.5, -100.0, -50.0), dpi_scale=1.25, zoom=0.5
    )

    assert screen_to_document(at_50, 300, 150) == (100.0, 50.0)
    assert screen_to_document(at_50, 201, 100) == (-98.0, -50.0)


def test_axes_scale_independently_as_photoshop_reports_at_non_integer_zooms() -> None:
    # Photoshop reported 1.8727 x 1.8657 at 66.67%. Here 2 and 4: doc (8, 8) -> u = 4, v = 2,
    # so screen (10 + 4, 20 + 2).
    anisotropic = view(bounds=(10, 20, 810, 620), matrix=(2.0, 0.0, 0.0, 4.0, 0.0, 0.0), dpi_scale=1.0)

    assert document_to_screen(anisotropic, 8, 8) == (14, 22)


def test_every_screen_pixel_survives_a_round_trip_even_through_a_rotated_view() -> None:
    # 30-degree rotation at 75% on a 150% monitor, panned; whatever Photoshop's matrix order is,
    # both directions must agree pixel for pixel.
    rotated = view(
        bounds=(-1920, 40, 0, 1080),
        matrix=(1.7320508, 1.0, -1.0, 1.7320508, 250.5, -75.25),
        dpi_scale=1.5,
        zoom=0.75,
    )
    pixels = [(sx, sy) for sx in range(-1920, 0, 97) for sy in range(40, 1080, 89)]

    assert [document_to_screen(rotated, *screen_to_document(rotated, *p)) for p in pixels] == pixels
