from __future__ import annotations

from scripts.adobe_observed_truth.input_plan import (
    KeyDown,
    KeyUp,
    MouseDown,
    MouseMove,
    MouseUp,
    chord,
    click,
    drag,
)


def test_modifier_held_before_press_brackets_the_whole_drag() -> None:
    plan = drag((100, 100), (300, 200), steps=2, hold=("shift",), hold_from="before_press")

    assert plan == [
        KeyDown("shift"),
        MouseMove(100, 100),
        MouseDown(),
        MouseMove(200, 150),
        MouseMove(300, 200),
        MouseUp(),
        KeyUp("shift"),
    ]


def test_modifier_held_after_drag_starts_goes_down_mid_drag_and_holds_through_release() -> None:
    plan = drag((100, 100), (300, 200), steps=2, hold=("shift",), hold_from="mid_drag")

    assert plan == [
        MouseMove(100, 100),
        MouseDown(),
        MouseMove(200, 150),
        KeyDown("shift"),
        MouseMove(300, 200),
        MouseUp(),
        KeyUp("shift"),
    ]


def test_a_chord_ending_in_the_plus_key_keeps_the_plus() -> None:
    assert chord("ctrl++") == [KeyDown("ctrl"), KeyDown("+"), KeyUp("+"), KeyUp("ctrl")]


def test_chord_presses_modifiers_in_order_taps_the_key_and_releases_in_reverse() -> None:
    assert chord("shift+ctrl+z") == [
        KeyDown("shift"),
        KeyDown("ctrl"),
        KeyDown("z"),
        KeyUp("z"),
        KeyUp("ctrl"),
        KeyUp("shift"),
    ]


def test_click_with_held_modifier_brackets_press_and_release() -> None:
    assert click((40, 60), hold=("shift",)) == [
        KeyDown("shift"),
        MouseMove(40, 60),
        MouseDown(),
        MouseUp(),
        KeyUp("shift"),
    ]
