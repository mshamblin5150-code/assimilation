"""The pen strokes the harness sends as Windows pointer input: hover in, press, move, lift, leave."""

from __future__ import annotations

from scripts.adobe_observed_truth.pen_input import DOWN, FIRSTBUTTON, INCONTACT, INRANGE, UP, UPDATE, pen_frames


def test_a_stroke_hovers_in_presses_moves_lifts_and_leaves() -> None:
    frames = pen_frames([(10, 20), (11, 20), (12, 20)], pressures=[0.0, 0.5, 1.0])
    flags = [f.flags for f in frames]
    assert flags[0] == INRANGE | UPDATE
    assert flags[1] == INRANGE | INCONTACT | FIRSTBUTTON | DOWN
    assert flags[2:-2] == [INRANGE | INCONTACT | FIRSTBUTTON | UPDATE] * 2
    assert flags[-2] == INRANGE | UP
    assert flags[-1] == UPDATE  # out of range: the pen has left
    assert [(f.x, f.y) for f in frames[1:4]] == [(10, 20), (11, 20), (12, 20)]


def test_pressure_is_sent_in_the_pointer_range_and_only_while_touching() -> None:
    frames = pen_frames([(0, 0), (1, 0), (2, 0)], pressures=[0.0, 0.5, 1.0])
    assert [f.pressure for f in frames] == [0, 0, 512, 1024, 0, 0]


def test_tilt_and_rotation_ride_on_every_contact_frame() -> None:
    frames = pen_frames([(0, 0), (1, 0)], pressures=[1.0, 1.0], tilts=[(30, -10), (45, 0)], rotations=[0, 90])
    assert [(f.tilt_x, f.tilt_y, f.rotation) for f in frames[1:3]] == [(30, -10, 0), (45, 0, 90)]


def test_screen_points_are_sent_from_the_virtual_desktops_corner() -> None:
    from scripts.adobe_observed_truth.pen_input import to_device

    # Measured 2026-11-26: with the desktop's left edge at -1440, a hover sent at 405 landed at -1035.
    assert to_device((405, 300), virtual_origin=(-1440, 0)) == (1845, 300)
    assert to_device((10, 20), virtual_origin=(0, 0)) == (10, 20)
