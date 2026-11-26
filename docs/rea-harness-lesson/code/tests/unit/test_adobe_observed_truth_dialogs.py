from __future__ import annotations

import json
from dataclasses import replace

import pytest

from scripts.adobe_observed_truth.photoshop import (
    Control,
    Dialog,
    accept_action,
    blocking,
    cancel_action,
    dialogs_off,
    dismiss_surveys,
)
from scripts.adobe_observed_truth.run import explain_failure, preflight


def button(text: str, hwnd: int = 0, checked: bool | None = None) -> Control:
    return Control(hwnd=hwnd, class_name="Button", text=text, checked=checked)


def label(text: str) -> Control:
    return Control(hwnd=0, class_name="Static", text=text, checked=None)


# Adobe's survey is recognised by the SHA-256 of its question, so its wording never ships: these
# tests point that hash at a made-up question.
EXAMPLE_QUESTION = "Example survey question?"


@pytest.fixture(autouse=True)
def _example_survey(monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib

    from scripts.adobe_observed_truth import photoshop

    monkeypatch.setattr(photoshop, "SURVEY_SHA256", hashlib.sha256(EXAMPLE_QUESTION.encode()).hexdigest())


# As observed live on 2026-11-09: Adobe's survey is a standard #32770 dialog, not a PSDialogBox.
SURVEY = Dialog(
    hwnd=1,
    class_name="#32770",
    controls=(
        button("Submit", hwnd=11),
        button("Cancel", hwnd=12),
        label("Example survey heading"),
        label(EXAMPLE_QUESTION),
        button("Never show again", hwnd=13, checked=False),
    ),
)
# The Generative Fill rich tooltip: a #32770 popup with no buttons, which does not block scripting.
HOVER_TOOLTIP = Dialog(hwnd=2, class_name="#32770", controls=())
PHOTOSHOP_ERROR = Dialog(
    hwnd=3,
    class_name="PSDialogBox",
    controls=(
        label("An example error message."),
        button("OK"),
    ),
)


def test_adobe_survey_and_photoshop_errors_block_but_a_hover_tooltip_does_not() -> None:
    assert blocking([SURVEY, HOVER_TOOLTIP, PHOTOSHOP_ERROR]) == [
        SURVEY,
        PHOTOSHOP_ERROR,
    ]


def drover(text: str) -> Control:
    return Control(
        hwnd=0, class_name="DroverLord - Window Class", text=text, checked=None
    )


# Image > Duplicate as captured live on 2026-11-09: Photoshop draws OK/Cancel itself.
DUPLICATE_DIALOG = Dialog(
    hwnd=4,
    class_name="#32770",
    controls=(
        drover("OS_ViewContainer"),
        drover("OS_ViewContainer"),
        drover("OS_EditTextContainer"),
        Control(hwnd=0, class_name="Edit", text="", checked=None),
    ),
)


def test_a_photoshop_drawn_dialog_blocks_even_without_windows_buttons() -> None:
    assert blocking([DUPLICATE_DIALOG, HOVER_TOOLTIP]) == [DUPLICATE_DIALOG]


# Image > Image Size as captured live on 2026-11-09: a floating container with real buttons.
IMAGE_SIZE_DIALOG = Dialog(
    hwnd=5,
    class_name="PSFloatC",
    controls=(
        Control(hwnd=51, class_name="Static", text="Image Size:", checked=None),
        Control(hwnd=52, class_name="Edit", text="400", checked=None),
        Control(hwnd=53, class_name="ComboBox", text="Pixels", checked=None),
        Control(hwnd=54, class_name="Button", text="OK", checked=None),
        Control(hwnd=55, class_name="Button", text="Cancel", checked=None),
    ),
)


def test_a_floating_photoshop_dialog_with_buttons_blocks() -> None:
    assert blocking([IMAGE_SIZE_DIALOG]) == [IMAGE_SIZE_DIALOG]


# Help > About Photoshop as captured live on 2026-11-09: a floating window with no buttons that
# holds Photoshop modal (scripting refused) until dismissed with Escape.
ABOUT_BOX = Dialog(
    hwnd=7,
    class_name="PSFloatC",
    controls=(Control(hwnd=71, class_name="PSViewC", text="", checked=None),),
)


def test_a_floating_window_with_no_buttons_still_blocks_and_is_dismissed_with_escape() -> (
    None
):
    assert blocking([ABOUT_BOX]) == [ABOUT_BOX]
    assert cancel_action(ABOUT_BOX) == ("escape", None)


# File > Export > Paths to Illustrator: Windows' own save dialog. A posted click on an inactive
# dialog can be ignored, which hung the run for 90 s; its Cancel command is not.
SAVE_DIALOG = Dialog(
    hwnd=8,
    class_name="#32770",
    controls=(
        Control(hwnd=81, class_name="Button", text="&Save", checked=None),
        Control(hwnd=82, class_name="Button", text="Cancel", checked=None),
    ),
)


def test_a_standard_windows_dialog_is_cancelled_with_its_cancel_command() -> None:
    assert cancel_action(SAVE_DIALOG) == ("cancel_command", None)


def test_cancelling_never_presses_generate_submit_or_share() -> None:
    def generative(*labels: str) -> Dialog:
        buttons = tuple(
            Control(hwnd=60 + n, class_name="Button", text=label, checked=None)
            for n, label in enumerate(labels)
        )
        return Dialog(hwnd=6, class_name="PSFloatC", controls=buttons)

    with_cancel = generative("Generate", "Share", "Cancel")
    assert cancel_action(with_cancel) == ("click", with_cancel.controls[2])
    # No Cancel: dismissed by Escape, never by pressing one of those buttons.
    assert cancel_action(generative("Generate", "Submit", "Share")) == ("escape", None)


def test_a_real_cancel_button_is_pressed_and_only_self_drawn_dialogs_are_closed() -> (
    None
):
    assert cancel_action(IMAGE_SIZE_DIALOG) == ("click", IMAGE_SIZE_DIALOG.controls[4])
    assert cancel_action(DUPLICATE_DIALOG) == ("close", None)


def test_survey_is_declined_for_good_and_never_submitted() -> None:
    clicked: list[str] = []

    result = dismiss_surveys(
        [SURVEY, HOVER_TOOLTIP], click=lambda c: clicked.append(c.text)
    )

    assert clicked == ["Never show again", "Cancel"]
    assert result.declined == [SURVEY]
    assert result.remaining == []


def test_survey_already_set_to_never_show_again_is_only_cancelled() -> None:
    ticked = tuple(
        replace(c, checked=True) if c.text == "Never show again" else c
        for c in SURVEY.controls
    )
    clicked: list[str] = []

    dismiss_surveys(
        [replace(SURVEY, controls=ticked)], click=lambda c: clicked.append(c.text)
    )

    assert clicked == ["Cancel"]


def test_other_blocking_dialogs_are_returned_untouched() -> None:
    clicked: list[str] = []

    result = dismiss_surveys([PHOTOSHOP_ERROR], click=lambda c: clicked.append(c.text))

    assert clicked == []
    assert result.remaining == [PHOTOSHOP_ERROR]


def custom_drawn(dialog: Dialog) -> Dialog:
    """The same survey if Adobe drew its controls itself instead of using standard buttons."""
    return replace(
        dialog,
        controls=tuple(
            replace(c, class_name="AdobeButton", checked=None)
            if c.class_name == "Button"
            else c
            for c in dialog.controls
        ),
    )


def test_a_survey_drawn_with_custom_controls_still_blocks_and_is_refused_unclicked() -> (
    None
):
    clicked: list[str] = []

    result = dismiss_surveys(
        [custom_drawn(SURVEY)], click=lambda c: clicked.append(c.text)
    )

    assert blocking([custom_drawn(SURVEY)]) == [custom_drawn(SURVEY)]
    assert clicked == []
    assert result.remaining == [custom_drawn(SURVEY)]


def test_survey_box_with_unreadable_state_is_not_clicked_in_case_it_is_already_ticked() -> (
    None
):
    unknown = tuple(
        replace(c, checked=None) if c.text == "Never show again" else c
        for c in SURVEY.controls
    )
    clicked: list[str] = []

    dismiss_surveys(
        [replace(SURVEY, controls=unknown)], click=lambda c: clicked.append(c.text)
    )

    assert clicked == ["Cancel"]


def screens(*answers: list[Dialog]):  # type: ignore[no-untyped-def]
    """What Photoshop shows on each look; the last answer repeats."""
    queue = list(answers)
    return lambda: queue.pop(0) if len(queue) > 1 else queue[0]


def test_preflight_waits_until_the_survey_has_closed_before_the_scenario_starts() -> (
    None
):
    clicked: list[str] = []
    slept: list[float] = []

    preflight(
        "canvas_mapping_check",
        screens([SURVEY], [SURVEY], []),
        click=lambda c: clicked.append(c.text),
        sleep=slept.append,
    )

    assert clicked.count("Cancel") == 1
    assert len(slept) == 1


def test_preflight_gives_up_on_a_survey_that_will_not_close() -> None:
    with pytest.raises(RuntimeError, match="canvas_mapping_check.*did not close"):
        preflight(
            "canvas_mapping_check",
            screens([SURVEY]),
            click=lambda c: None,
            sleep=lambda _: None,
            timeout_s=1.0,
        )


class RefusingPhotoshop:
    """Answers the first script, then refuses every later one, as Photoshop does behind a modal."""

    def __init__(self) -> None:
        self.calls = 0

    def js(self, body: str) -> str:
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError('The command "Close" is not currently available.')
        return "DialogModes.ERROR"


def test_a_failed_restore_does_not_hide_the_scenario_error() -> None:
    with (
        pytest.raises(ValueError, match="selection bounds missing"),
        dialogs_off(RefusingPhotoshop()),  # type: ignore[arg-type]
    ):
        raise ValueError("selection bounds missing")


def test_preflight_refuses_to_start_behind_another_dialog_and_names_it() -> None:
    with pytest.raises(
        RuntimeError, match='canvas_mapping_check.*An example error message'
    ):
        preflight(
            "canvas_mapping_check", screens([PHOTOSHOP_ERROR]), click=lambda c: None
        )


def failing_scenario_whose_cleanup_also_fails() -> None:
    try:
        raise ValueError("selection bounds missing")
    finally:
        raise RuntimeError('The command "Close" is not currently available.')


def test_a_scenario_failure_is_headlined_by_its_first_error_not_the_cleanup() -> None:
    try:
        failing_scenario_whose_cleanup_also_fails()
    except RuntimeError as error:
        explained = explain_failure("canvas_mapping_check", error)

    assert explained is not None
    assert str(explained).startswith(
        "canvas_mapping_check failed: ValueError('selection bounds missing')"
    )
    assert '"Close" is not currently available' in str(explained)


def test_a_failure_with_no_cleanup_error_is_left_as_it_is() -> None:
    assert (
        explain_failure("canvas_mapping_check", ValueError("selection bounds missing"))
        is None
    )


def test_context_python_suppresses_is_not_mistaken_for_an_earlier_error() -> None:
    # json.loads("") raises JSONDecodeError over a suppressed StopIteration; Photoshop.js parses
    # every DoJavaScript result this way.
    try:
        json.loads("")
    except ValueError as error:
        assert explain_failure("canvas_mapping_check", error) is None


def test_a_deliberate_translation_is_left_as_it_is() -> None:
    try:
        try:
            raise KeyError("bounds")
        except KeyError as low_level:
            raise ValueError("selection bounds missing") from low_level
    except ValueError as error:
        assert explain_failure("canvas_mapping_check", error) is None


# Filter > Adaptive Wide Angle as captured live on 2026-11-09: a full-window filter dialog of its
# own class, with real buttons. Unrecognised, it held Photoshop modal until a restart.
FILTER_DIALOG = Dialog(
    hwnd=9,
    class_name="PSFilter_WindowClass",
    controls=(
        Control(hwnd=91, class_name="Button", text="&Preview", checked=None),
        Control(hwnd=92, class_name="Button", text="OK", checked=None),
        Control(hwnd=93, class_name="Button", text="Cancel", checked=None),
    ),
)


def test_a_full_window_filter_dialog_blocks_and_its_cancel_button_is_pressed() -> None:
    assert blocking([FILTER_DIALOG]) == [FILTER_DIALOG]
    assert cancel_action(FILTER_DIALOG) == ("click", FILTER_DIALOG.controls[2])


def test_a_window_of_any_class_with_a_real_cancel_button_blocks_and_is_cancelled() -> (
    None
):
    # Filter > Blur > Radial Blur hung on 2026-11-09 behind a window class not yet seen.
    unseen = replace(FILTER_DIALOG, class_name="SomeNewPhotoshopClass")

    assert blocking([unseen]) == [unseen]
    assert cancel_action(unseen) == ("click", unseen.controls[2])


def test_a_window_of_an_unknown_class_without_a_cancel_button_does_not_block() -> None:
    assert (
        blocking([Dialog(hwnd=10, class_name="OWL.Dock", controls=(label("Layers"),))])
        == []
    )


NEVER = ("Generate", "Submit", "Share", "Upload", "Create link")


def test_to_see_a_filter_work_its_real_ok_button_is_pressed_with_the_default_settings() -> (
    None
):
    assert accept_action(FILTER_DIALOG, never_press=NEVER) == (
        "click",
        FILTER_DIALOG.controls[1],
    )


def test_a_dialog_offering_generate_is_cancelled_never_accepted() -> None:
    generative = replace(
        FILTER_DIALOG,
        controls=(
            *FILTER_DIALOG.controls,
            Control(hwnd=94, class_name="Button", text="Generate", checked=None),
        ),
    )

    assert accept_action(generative, never_press=NEVER) == (
        "click",
        FILTER_DIALOG.controls[2],
    )


def test_a_self_drawn_dialog_is_accepted_with_enter_since_its_ok_cannot_be_clicked() -> None:
    # Hue/Saturation, Levels, Curves: Photoshop draws OK itself; Enter on the dialog is OK.
    assert accept_action(DUPLICATE_DIALOG, never_press=NEVER) == ("enter", None)


def test_a_dialog_with_neither_a_real_ok_nor_self_drawn_controls_falls_back_to_cancelling() -> None:
    assert accept_action(SCRIPT_DIALOG, never_press=NEVER) == ("escape", None)


# View > Pattern Preview as captured live on 2026-11-09: a notice with no Cancel, which ignored
# WM_CLOSE and held Photoshop modal for 90 s.
PATTERN_NOTICE = Dialog(
    hwnd=11,
    class_name="PSDialogBox",
    controls=(
        label("Pattern Preview works best with smart objects."),
        Control(hwnd=111, class_name="Button", text="OK", checked=None),
        Control(hwnd=112, class_name="Button", text="More Info...", checked=None),
        Control(hwnd=113, class_name="Button", text="Don\u2019t show again", checked=None),
    ),
)


def test_a_notice_without_cancel_is_acknowledged_with_ok_not_more_info_or_dont_show() -> None:
    assert cancel_action(PATTERN_NOTICE) == ("click", PATTERN_NOTICE.controls[1])


# Place Scale Marker's range alert (2026-11-23): a Windows message box with only OK. A posted
# BM_CLICK can be ignored by a dialog that is not active (Microsoft's BM_CLICK notes); it stayed
# open across the next two controls' actions. A posted WM_COMMAND, as Save As's IDCANCEL, is not.
RANGE_ALERT = Dialog(
    hwnd=12,
    class_name="#32770",
    controls=(
        Control(hwnd=121, class_name="Static", text="", checked=None),  # the error icon
        label("Invalid numeric entry."),
        Control(hwnd=123, class_name="Button", text="OK", checked=None),
    ),
)


def test_a_windows_message_box_with_only_ok_is_answered_with_its_ok_command_not_a_click() -> None:
    assert cancel_action(RANGE_ALERT) == ("button_command", RANGE_ALERT.controls[2])


CONFIRM_REPLACE = Dialog(
    hwnd=13,
    class_name="#32770",
    controls=(
        label("The file already exists. Do you want to replace it?"),
        Control(hwnd=131, class_name="Button", text="&Yes", checked=None),
        Control(hwnd=132, class_name="Button", text="&No", checked=None),
    ),
)


def test_a_yes_no_box_is_cancelled_with_its_no_button() -> None:
    # Paths to Illustrator's Confirm Save As (2026-11-24): no Cancel and no OK, so WM_CLOSE was
    # sent, which a Yes/No box ignores; it held the command for 90 s. No leaves things as they were.
    assert cancel_action(CONFIRM_REPLACE) == ("button_command", CONFIRM_REPLACE.controls[2])


def test_a_message_box_ok_is_sent_as_its_own_buttons_command_not_idok(monkeypatch) -> None:
    """Filter Gallery's range alert (2026-11-24): its only button, OK, carries command 2, so
    IDOK (1) was ignored and the alert stayed open for 16 minutes."""
    from types import SimpleNamespace

    from scripts.adobe_observed_truth import photoshop

    posted: list[tuple[int, int, int, int]] = []

    class User32:
        def GetDlgCtrlID(self, hwnd: int) -> int:
            return {123: 2}[hwnd]

        def PostMessageW(self, *message: int) -> int:
            posted.append(message)
            return 1

    monkeypatch.setattr(photoshop.ctypes, "windll", SimpleNamespace(user32=User32()))

    photoshop.answer(RANGE_ALERT, *cancel_action(RANGE_ALERT))

    assert posted == [(12, 0x0111, 2, 0)]


def edit_field() -> Control:
    return Control(hwnd=0, class_name="Edit", text="", checked=None)


# Filter > Render > Picture Frame as captured live on 2026-11-09: a scripted-pattern dialog whose
# OK and Cancel are self-drawn; only its number fields are real controls. Escape sent to it closes it.
SCRIPT_DIALOG = Dialog(hwnd=12, class_name="CScriptPs_WindowClass", controls=(edit_field(),) * 5)


def test_a_dialog_whose_only_real_controls_are_input_fields_blocks() -> None:
    assert blocking([SCRIPT_DIALOG]) == [SCRIPT_DIALOG]


def test_a_dialog_of_its_own_class_without_real_buttons_is_dismissed_with_escape() -> None:
    assert cancel_action(SCRIPT_DIALOG) == ("escape", None)


def test_a_panel_dock_with_input_fields_is_not_a_dialog() -> None:
    dock = Dialog(hwnd=13, class_name="OWL.Dock", controls=(edit_field(),))

    assert blocking([dock]) == []


# Filter > Vanishing Point, 2026-11-09: OK stays greyed out until a plane is drawn; clicking it
# 90 times did nothing and the probe timed out.
VANISHING_POINT = Dialog(
    hwnd=14,
    class_name="PSFilter_WindowClass",
    controls=(
        Control(hwnd=141, class_name="Button", text="OK", checked=None, enabled=False),
        Control(hwnd=142, class_name="Button", text="Cancel", checked=None),
    ),
)


def test_a_greyed_out_ok_is_never_pressed_the_dialog_is_cancelled_instead() -> None:
    assert accept_action(VANISHING_POINT, never_press=NEVER) == ("click", VANISHING_POINT.controls[1])

def test_enter_or_escape_for_a_dialog_takes_the_foreground_through_focus_not_a_bare_call(monkeypatch) -> None:
    """File Info, 2026-11-24: the Claude app held the foreground and a bare SetForegroundWindow from
    the background was refused, so Enter stopped at the foreground check three times over."""
    from types import SimpleNamespace

    from scripts.adobe_observed_truth import photoshop, win_input

    order: list[str] = []

    class User32:
        def GetWindowThreadProcessId(self, hwnd, pid):
            pid._obj.value = 4924
            return 1

        def SetForegroundWindow(self, hwnd):
            order.append("bare")
            return 0

    monkeypatch.setattr(photoshop.ctypes, "windll", SimpleNamespace(user32=User32()))
    monkeypatch.setattr(win_input, "focus", lambda hwnd, pid, **k: order.append(f"focus {hwnd} {pid}"))
    monkeypatch.setattr(win_input, "perform", lambda events, pid, **k: order.append(f"keys {pid}"))

    photoshop.answer(RANGE_ALERT, "enter", None)

    assert order == ["focus 12 4924", "keys 4924"]
