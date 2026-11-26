"""Synthesized keyboard input: keys by virtual-key code, other characters as themselves."""

from __future__ import annotations

from scripts.adobe_observed_truth import win_input
from scripts.adobe_observed_truth.input_plan import KeyDown, KeyUp

KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x0002, 0x0004


def keyboard(event: KeyDown | KeyUp) -> tuple[int, int, int]:
    ki = win_input._to_input(event).u.ki
    return ki.wVk, ki.wScan, ki.dwFlags


def test_a_capital_or_a_symbol_is_typed_as_that_character_not_its_bare_key() -> None:
    """Restoring Save for Web's "100%" failed on '%', and a typed "Default" came back as
    "default": the bare D key types d (2026-11-10)."""
    assert [keyboard(KeyDown("%")), keyboard(KeyUp("%")), keyboard(KeyDown("D"))] == [
        (0, ord("%"), KEYEVENTF_UNICODE),
        (0, ord("%"), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
        (0, ord("D"), KEYEVENTF_UNICODE),
    ]


def test_lowercase_letters_digits_and_named_keys_keep_their_key_codes_for_shortcuts() -> None:
    assert [keyboard(KeyDown(k))[0] for k in ("a", "7", "tab", "ctrl")] == [ord("A"), ord("7"), 0x09, 0x11]


def test_the_foreground_is_never_taken_from_the_person_once_they_are_back() -> None:
    """The dialog surface took the foreground before its guard was asked, pulling the window
    away from the person typing in another app (2026-11-11). Nothing is touched: hwnd 0 and
    pid 0 would fail any window call made."""
    import pytest

    with pytest.raises(win_input.InputInterrupted, match="person"):
        win_input.focus(0, 0, settle_s=0, should_stop=lambda: True)


def test_input_with_no_guard_of_its_own_still_stops_for_the_person_once_a_session_guard_is_set() -> None:
    """The scenario suite called focus and perform with no guard at all (2026-11-11): the
    person's own typing never stopped it. A session sets one guard that every call obeys."""
    import pytest

    sent: list[object] = []
    win_input.set_session_guard(lambda: True)
    try:
        with pytest.raises(win_input.InputInterrupted):
            win_input.perform([KeyDown("a"), KeyUp("a")], pid=1, send=sent.append, foreground=lambda: 1, delay_s=0)
        with pytest.raises(win_input.InputInterrupted, match="person"):
            win_input.focus(0, 0, settle_s=0)
    finally:
        win_input.set_session_guard(None)

    assert sent == []


def test_an_interruption_names_the_process_that_took_the_foreground() -> None:
    import pytest

    sent: list[object] = []

    with pytest.raises(win_input.InputInterrupted, match="process 4242"):
        win_input.perform([KeyDown("a"), KeyUp("a")], pid=28028, send=sent.append, foreground=lambda: 4242, delay_s=0)


def test_no_foreground_window_for_a_moment_is_not_the_person_coming_back() -> None:
    """Dragging Liquify's resize grip, Windows briefly reported no foreground window
    (process 0) and the run stopped as if interrupted (2026-11-10). A missing foreground gets a
    moment to return; another process still stops input."""
    import pytest

    readings = iter([0, 0, 28028, 28028])
    sent: list[object] = []

    win_input.perform([KeyDown("a"), KeyUp("a")], pid=28028, send=sent.append, foreground=lambda: next(readings), delay_s=0)

    assert len(sent) == 2
    with pytest.raises(win_input.InputInterrupted, match="process 4242"):
        others = iter([0, 4242])
        win_input.perform([KeyDown("a")], pid=28028, send=sent.append, foreground=lambda: next(others), delay_s=0)


def test_a_window_that_took_the_foreground_while_nobody_is_here_is_taken_back_and_input_goes_on() -> None:
    """The Claude app raised itself mid-command with no one at the PC (no input for 5 min),
    and every key after it stopped: dialog after dialog was interrupted (2026-11-24). With
    the person away the window the plan began in is brought back; the person still stops it."""
    holder = {"pid": 28028}
    taken_back: list[int] = []
    sent: list[object] = []

    def take_back() -> bool:
        taken_back.append(1)
        holder["pid"] = 28028
        return True

    def foreground() -> int:
        pid = holder["pid"]
        if len(sent) == 1 and not taken_back:
            holder["pid"] = pid = 29536  # the Claude app comes forward after the first key
        return pid

    win_input.perform([KeyDown("a"), KeyUp("a")], pid=28028, send=sent.append, foreground=foreground,
                      take_back=take_back, should_stop=lambda: False, delay_s=0)

    assert (len(sent), len(taken_back)) == (2, 1)
