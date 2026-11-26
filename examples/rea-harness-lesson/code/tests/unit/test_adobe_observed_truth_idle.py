from __future__ import annotations

import pytest

from scripts.adobe_observed_truth.idle import decide, release_plan
from scripts.adobe_observed_truth.input_plan import (
    Event,
    KeyDown,
    KeyUp,
    MouseDown,
    MouseMove,
    MouseUp,
)
from scripts.adobe_observed_truth.win_input import InputInterrupted, perform

TWENTY_MINUTES = 1200.0
TARGET = 4242
PLAN: list[Event] = [KeyDown("shift"), MouseMove(10, 10), MouseMove(20, 20), KeyUp("shift")]


def test_a_mouse_drifting_a_pixel_on_its_own_is_not_the_person_coming_back() -> None:
    """With nobody at the desk the mouse reported 1 px moves around (1450, 2501) about once
    a minute (2026-11-11); each one counted as the person, so File Info never ran. Keys,
    clicks and the wheel are always a person; a move only once it leaves where they left it."""
    from scripts.adobe_observed_truth.idle import PersonInput

    person = PersonInput()

    drift = [person.counts("move", at) for at in [(1451, 2501), (1450, 2502), (1449, 2502), (1451, 2501), (1450, 2500)]]
    moved = person.counts("move", (1462, 2503))
    typed, clicked = person.counts("key"), person.counts("click", (1462, 2503))

    assert drift == [False, False, False, False, False]
    assert (moved, typed, clicked) == (True, True, True)


def test_a_plan_stopped_part_way_lets_go_of_the_shift_it_was_holding() -> None:
    sent: list[Event] = []
    checks = iter([False, True])

    with pytest.raises(InputInterrupted):
        perform(
            PLAN,
            pid=TARGET,
            delay_s=0,
            should_stop=lambda: next(checks),
            send=sent.append,
            foreground=lambda: TARGET,
        )

    assert sent == [KeyDown("shift"), KeyUp("shift")]


def test_a_windows_error_after_a_key_went_down_still_releases_it() -> None:
    sent: list[Event] = []

    def send(event: Event) -> None:
        if isinstance(event, MouseMove):
            raise OSError("SendInput refused")
        sent.append(event)

    with pytest.raises(OSError, match="SendInput refused"):
        perform(PLAN, pid=TARGET, delay_s=0, send=send, foreground=lambda: TARGET)

    assert sent == [KeyDown("shift"), KeyUp("shift")]


def test_probes_start_only_after_the_person_has_been_away_long_enough() -> None:
    assert (
        decide(now=5000.0, last_real_input=3700.0, threshold_s=TWENTY_MINUTES, running=False)
        == "run"
    )
    assert (
        decide(now=5000.0, last_real_input=4000.0, threshold_s=TWENTY_MINUTES, running=False)
        == "wait"
    )


def test_a_running_probe_yields_the_moment_the_person_comes_back() -> None:
    assert (
        decide(now=5000.0, last_real_input=4999.5, threshold_s=TWENTY_MINUTES, running=True)
        == "stop"
    )
    assert (
        decide(now=5000.0, last_real_input=3000.0, threshold_s=TWENTY_MINUTES, running=True)
        == "run"
    )


def test_stopping_mid_drag_releases_the_button_then_the_held_keys_in_reverse() -> None:
    sent: list[Event] = [
        KeyDown("ctrl"),
        KeyDown("shift"),
        MouseMove(1, 1),
        MouseDown(),
        MouseMove(5, 5),
    ]

    assert release_plan(sent) == [MouseUp(), KeyUp("shift"), KeyUp("ctrl")]


def test_nothing_is_released_after_a_plan_that_finished_cleanly() -> None:
    sent: list[Event] = [KeyDown("shift"), MouseDown(), MouseMove(5, 5), MouseUp(), KeyUp("shift")]

    assert release_plan(sent) == []
