"""The Illustrator runner: its dialogs are standard dialog windows (#32770) whose controls Illustrator
draws itself, so they are found by class and answered by closing them, which cancels."""

from __future__ import annotations

from scripts.adobe_observed_truth.runner_illustrator import (
    declined,
    dialog_windows,
    documents_to_close,
    dont_send_button,
    while_command_runs,
)


def test_the_crash_reporter_is_answered_with_dont_send_never_generate_report() -> None:
    # Error Report for "Illustrator" sat open mid-sweep until it was answered by hand (2026-11-25).
    buttons = [(11, "Button", "Generate report"), (12, "Button", "Adobe may contact me for fixes and workarounds"),
               (13, "Button", "Automatically send future error reports"), (14, "Button", "Don't send"),
               (15, "Static", "Don't send")]

    assert dont_send_button(buttons) == 14
    assert dont_send_button([(11, "Button", "Generate report")]) is None


def test_illustrator_declining_a_command_is_a_refusal_not_a_failure() -> None:
    # 81 commands (live effects, window commands) answered at once with error 'BKey', no dialog
    # shown: Illustrator declining them here, as Photoshop's "not currently available" (2026-11-25).
    error = ("com_error: (-2147352567, 'Exception occurred.', (0, 'Adobe Illustrator', 'Error 54: Uncaught JavaScript "
             "exception: an Illustrator error occurred: 1112237433 (\\'BKey\\').\\rLine: 1'")

    assert declined(error) == "Illustrator declined the command (error BKey)"
    assert declined("TimeoutError: did not return") is None


def test_the_harness_closes_its_own_documents_and_any_a_command_made_never_another() -> None:
    # File > New made "Untitled-27"; left open, the next spec refused to start beside it (2026-11-25).
    before = ["observed-truth-sweep"]
    now = ["observed-truth-sweep", "Untitled-27"]

    assert documents_to_close(before, now) == ["observed-truth-sweep", "Untitled-27"]
    assert documents_to_close(["Brochure.ai", "observed-truth-sweep"], ["Brochure.ai", "observed-truth-sweep"]) == [
        "observed-truth-sweep"]


def test_only_visible_dialog_windows_count_never_the_main_window_or_a_floating_panel() -> None:
    windows = [
        (1, "illustrator", "observed-truth-sweep @ 100%", True),  # the main window
        (2, "OWL.Dock", "", True),  # a floating panel: closing it would close the person's panel
        (3, "#32770", "Rotate", True),
        (4, "#32770", "", False),  # hidden
    ]

    assert dialog_windows(windows, main_hwnd=1) == [3]


def test_a_dialog_awaited_by_a_handler_goes_to_it_never_to_the_closer() -> None:
    # Offset Path opened between the handler's look and the closer's, so the closer cancelled it
    # and the handler got the next box (the first live dropdown probe, 2026-11-25).
    assert while_command_runs(handler_waiting=True, dialogs=[]) == "crash_reports_only"
    assert while_command_runs(handler_waiting=True, dialogs=[7, 8]) == "hand_over"
    assert while_command_runs(handler_waiting=False, dialogs=[7]) == "close_dialogs"
    assert while_command_runs(handler_waiting=False, dialogs=[]) == "close_dialogs"


def test_a_box_of_another_class_counts_too_as_the_about_box_does() -> None:
    # The About box is a splash window, not a dialog window: left open, it held the next command
    # (the first live check, 2026-11-25).
    windows = [(1, "illustrator", "doc", True), (5, "com.adobe.AdobeSplashKit.TextWindowClass", "", True),
               (6, "com.adobe.AdobeSplashKit.GraphicWindowClass", "", True), (7, "OWL.Palette", "", True)]

    assert dialog_windows(windows, main_hwnd=1) == [5, 6]
