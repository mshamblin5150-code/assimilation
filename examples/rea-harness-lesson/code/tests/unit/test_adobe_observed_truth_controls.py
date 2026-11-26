"""Discovering a dialog's controls from pixels and input alone (dialogs Photoshop draws itself)."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.adobe_observed_truth.controls import focus_on, focus_walk, probe
from scripts.adobe_observed_truth.dialog_surface import prepare_for_ocr, to_screen
from scripts.adobe_observed_truth.input_plan import (
    Event,
    KeyDown,
    KeyUp,
    MouseDown,
    MouseMove,
    MouseUp,
)

Rect = tuple[int, int, int, int]


class FakeDialog:
    """A self-drawn dialog: grey controls, a focus ring on the focused one, Tab moves focus."""

    def __init__(self, controls: list[Rect], *, caret: bool = False, focus: int | None = 0) -> None:
        self.controls, self.focus, self.caret, self.shots = controls, focus, caret, 0

    def shot(self) -> np.ndarray:
        image = np.full((200, 300, 3), 60, dtype=np.uint8)
        for index, (x0, y0, x1, y1) in enumerate(self.controls):
            image[y0:y1, x0:x1] = 90
            if index == self.focus:  # a 2-px ring just outside the control
                ring = (slice(y0 - 3, y1 + 3), slice(x0 - 3, x1 + 3))
                image[ring] = 200
                image[y0 - 1 : y1 + 1, x0 - 1 : x1 + 1] = 60
                image[y0:y1, x0:x1] = 90
        self.shots += 1
        if self.caret and self.shots % 2:  # a text caret blinking in the first control
            x0, y0, _, y1 = self.controls[0]
            image[y0 + 2 : y1 - 2, x0 + 4] = 255
        return image

    def send(self, events: list[Event]) -> None:
        downs = [e.key for e in events if isinstance(e, KeyDown)]
        if downs == ["tab"]:
            self.focus = 0 if self.focus is None else (self.focus + 1) % len(self.controls)
        elif downs == ["shift", "tab"]:
            self.focus = 0 if self.focus is None else (self.focus - 1) % len(self.controls)


CONTROLS: list[Rect] = [(20, 20, 120, 40), (20, 60, 120, 80), (160, 20, 260, 50), (160, 120, 260, 150)]


def centre_in(rect: Rect, control: Rect) -> bool:
    x, y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    return control[0] <= x <= control[2] and control[1] <= y <= control[3]


def test_tabbing_round_a_dialog_finds_every_focusable_control_in_tab_order() -> None:
    found = focus_walk(FakeDialog(CONTROLS))

    assert len(found) == len(CONTROLS)
    assert all(centre_in(rect, control) for rect, control in zip(found, CONTROLS, strict=True))


def test_a_dotted_focus_rectangle_counts_as_one_control_not_many_specks() -> None:
    class Dotted(FakeDialog):
        def shot(self) -> np.ndarray:
            image = np.full((200, 300, 3), 60, dtype=np.uint8)
            x0, y0, x1, y1 = self.controls[self.focus]
            image[y0 - 2, x0 - 2 : x1 + 2 : 2] = 200  # every other pixel, like Windows' focus dots
            image[y1 + 1, x0 - 2 : x1 + 2 : 2] = 200
            image[y0 - 2 : y1 + 2 : 2, x0 - 2] = 200
            image[y0 - 2 : y1 + 2 : 2, x1 + 1] = 200
            return image

    found = focus_walk(Dotted(CONTROLS))

    assert all(centre_in(rect, control) for rect, control in zip(found, CONTROLS, strict=True))


def test_a_blinking_caret_is_not_mistaken_for_a_control() -> None:
    found = focus_walk(FakeDialog(CONTROLS, caret=True))

    assert len(found) == len(CONTROLS)


def test_a_default_button_that_pulses_on_every_tab_is_not_taken_for_focus() -> None:
    """Levels' OK button changed at almost every Tab (2026-11-10) and became most of the walk's
    stops. Focus changes a control on two consecutive Tabs (arriving, leaving); a thing that
    changes on three in a row is animation."""

    class Pulsing(FakeDialog):
        glow = False

        def shot(self) -> np.ndarray:
            image = super().shot()
            image[2:14, 140:290] = 230 if self.glow else 120  # near the top, like Levels' OK
            return image

        def send(self, events: list[Event]) -> None:
            super().send(events)
            self.glow = not self.glow  # its pulse happens to change between every two Tabs

    found = focus_walk(Pulsing(CONTROLS))

    assert [any(centre_in(rect, c) for rect in found) for c in CONTROLS] == [True, True, True, True]
    assert not any(centre_in(rect, (140, 2, 290, 14)) for rect in found)


def test_controls_whose_only_focus_sign_is_a_blinking_box_are_all_found() -> None:
    """Photoshop's fields show focus only by blinking their whole box (Levels, 2026-11-10):
    blinking that starts or stops is focus moving, not noise to mask for the rest of the walk."""

    class BlinkingFocus(FakeDialog):
        def shot(self) -> np.ndarray:
            image = np.full((200, 300, 3), 60, dtype=np.uint8)
            for x0, y0, x1, y1 in self.controls:
                image[y0:y1, x0:x1] = 90
            self.shots += 1
            if self.focus is not None and self.shots % 2:
                x0, y0, x1, y1 = self.controls[self.focus]
                image[y0:y1, x0:x1] = 250
            return image

    found = focus_walk(BlinkingFocus(CONTROLS))

    assert [any(centre_in(rect, c) for rect in found) for c in CONTROLS] == [True, True, True, True]


class Answering:
    """One focused control that answers keys the way its kind does; draws its state as grey."""

    def __init__(self, kind: str, text: str = "") -> None:
        self.kind, self.text, self.value, self.popup, self.pressed, self.focus_moved = kind, text, 5, False, [], False

    def shot(self) -> np.ndarray:
        image = np.full((100, 200, 3), 60, dtype=np.uint8)
        image[20:40, 20:120] = 80 + self.value * 10
        if self.focus_moved:
            image[60:80, 20:120] = 200
        return image

    def send(self, events: list[Event]) -> None:
        keys = [e.key for e in events if isinstance(e, KeyDown)]
        if self.popup:
            if keys == ["escape"]:
                self.popup = False
            return
        if keys in (["up"], ["down"]):
            step = 1 if keys == ["up"] else -1
            if self.kind in ("number_field", "slider", "dropdown"):
                self.value += step
            elif self.kind == "radio_group":
                self.focus_moved = keys == ["up"]
        elif keys == ["alt", "down"] and self.kind == "dropdown":
            self.popup = True
        elif len(keys) == 1 and keys[0].isdigit() and self.kind in ("number_field", "text_field"):
            self.value = int(keys[0])
        elif len(keys) == 1 and keys[0].isalpha() and len(keys[0]) == 1 and self.kind == "text_field":
            self.value = 9
        elif keys == ["space"]:
            self.pressed.append(self.text)
            if self.kind == "checkbox":
                self.value = 1 - self.value if self.value in (0, 1) else 0
            elif self.kind == "button":
                self.popup = True

    def popups(self) -> int:
        return int(self.popup)

    def read_text(self, rect: Rect) -> str:
        return str(self.value) if self.kind in ("number_field", "text_field") else self.text


FOCUSED: Rect = (20, 20, 120, 40)


def test_each_kind_of_control_is_told_apart_by_how_it_answers_keys() -> None:
    for kind in ("number_field", "slider", "checkbox", "dropdown", "radio_group", "text_field"):
        assert probe(Answering(kind), FOCUSED).kind == kind


def test_a_dropdown_listing_commands_is_found_by_opening_its_list_before_any_arrow_key() -> None:
    """File Info's Template Folder list runs the entry an arrow key lands on: the probe's very
    first Up opened Explorer (2026-11-11). Alt+Down opens a list without choosing from it."""

    class CommandList(Answering):
        ran: list[str] = []

        def send(self, events: list[Event]) -> None:
            keys = [e.key for e in events if isinstance(e, KeyDown)]
            if not self.popup and keys in (["up"], ["down"], ["home"], ["end"]):
                self.ran.append(keys[0])
            super().send(events)

        def popup_lines(self) -> list[str]:
            return ["Template Folder", "Import...", "Export..."] if self.popup else []

    dialog = CommandList("dropdown")

    found = probe(dialog, FOCUSED)

    assert (found.kind, found.commands, dialog.ran) == ("dropdown", True, [])


def test_arrow_keys_that_just_move_to_another_tab_stop_do_not_make_a_radio_group() -> None:
    dialog = Answering("checkbox")

    class Navigating(Answering):
        def send(self, events: list[Event]) -> None:
            keys = [e.key for e in events if isinstance(e, KeyDown)]
            if keys in (["up"], ["down"]):
                self.focus_moved = keys == ["up"]  # focus goes to a known tab stop
            else:
                super().send(events)

    dialog = Navigating("checkbox")

    assert probe(dialog, FOCUSED, known=[FOCUSED, (20, 60, 120, 80)]).kind == "checkbox"


def test_an_arrow_key_that_takes_focus_away_is_navigation_and_focus_is_brought_back() -> None:
    """WPF: Up moves focus to another control (wrapping round; Down does not bring it back).
    The focused control's own pixels change as its focus frame leaves: not a value stepping."""

    class Wrapping:
        def __init__(self) -> None:
            self.focus, self.pressed, self.typed_elsewhere = "self", [], ""

        def shot(self) -> np.ndarray:
            image = np.full((100, 200, 3), 60, dtype=np.uint8)
            image[20:40, 20:120] = 90
            image[60:80, 20:120] = 90
            frame = (20, 40) if self.focus == "self" else (60, 80)
            image[frame[0] : frame[0] + 2, 20:120] = 250
            return image

        def send(self, events: list[Event]) -> None:
            held: list[str] = []
            for event in events:
                if isinstance(event, KeyDown) and event.key in ("shift", "alt"):
                    held.append(event.key)
                elif isinstance(event, KeyDown):
                    self.press([*held, event.key])

        def press(self, keys: list[str]) -> None:
            if keys == ["up"]:
                self.focus = "other"
            elif keys in (["tab"], ["shift", "tab"]):
                self.focus = "other" if self.focus == "self" else "self"
            elif keys == ["space"] and self.focus == "self":
                self.pressed.append("Press me")
            elif len(keys) == 1 and keys[0].isdigit() and self.focus == "other":
                self.typed_elsewhere += keys[0]

        def popups(self) -> int:
            return 0

        def read_text(self, rect: Rect) -> str:
            return "Press me" if rect == FOCUSED else ""

    dialog = Wrapping()

    found = probe(dialog, FOCUSED, known=[FOCUSED, (20, 60, 120, 80)])

    assert (found.kind, dialog.pressed, dialog.typed_elsewhere) == ("button", ["Press me"], "")


def test_a_caret_moving_in_a_text_field_does_not_make_it_a_number_field() -> None:
    class Text(Answering):
        def send(self, events: list[Event]) -> None:
            keys = [e.key for e in events if isinstance(e, KeyDown)]
            if keys == ["up"]:
                self.value = 6  # the caret moved: pixels change, the text does not
            super().send(events)

        def read_text(self, rect: Rect) -> str:
            return "7" if self.value == 7 else ""

    assert probe(Text("text_field"), FOCUSED).kind == "text_field"


def test_a_button_whose_box_changes_when_a_digit_is_typed_is_not_taken_for_a_field() -> None:
    """Curves' Auto and Options... buttons (and once OK) were called text fields: a typed 7
    changed pixels in their box, though their text never showed it. The text field driver then
    typed "harness probe", whose space pressed them; Curves closed (2026-11-10)."""

    class Flickering(Answering):
        def send(self, events: list[Event]) -> None:
            keys = [e.key for e in events if isinstance(e, KeyDown)]
            if len(keys) == 1 and keys[0].isdigit():
                self.value += 1  # the box redraws; its text stays the same
            super().send(events)

    found = probe(Flickering("button", "Auto"), FOCUSED)

    assert found.kind == "button"


def test_a_button_is_pressed_to_see_what_it_opens_and_what_it_opened_is_closed() -> None:
    dialog = Answering("button", "Load...")

    found = probe(dialog, FOCUSED)

    assert (found.kind, found.opened_popup, dialog.popup) == ("button", True, False)


def test_ok_cancel_and_buttons_that_send_or_spend_are_never_pressed() -> None:
    for label in ("OK", "0K", "Cancel", "Generate", "Share", "Upload", "Submit", "Create link"):
        dialog = Answering("button", label)

        found = probe(dialog, FOCUSED)

        assert (found.kind, dialog.pressed) == ("button", []), label


def test_clicks_in_a_dialog_land_at_the_same_spot_on_screen() -> None:
    events = [MouseMove(10, 20), MouseDown(), KeyDown("shift"), MouseMove(30, 40), MouseUp()]

    moved = to_screen(events, (1000, 500))

    assert moved == [MouseMove(1010, 520), MouseDown(), KeyDown("shift"), MouseMove(1030, 540), MouseUp()]


def test_light_text_on_a_dark_dialog_is_read_dark_on_light_at_twice_the_size() -> None:
    dark = np.full((10, 20, 3), 50, dtype=np.uint8)
    dark[4:6, 5:15] = 230  # light text

    prepared = prepare_for_ocr(dark)

    # 3x: on all catalogued dialogs RapidOCR found 78.6% of label words at 3x (Windows 71.7%)
    assert prepared.shape == (30, 60)
    assert prepared[0, 0] > 128 > prepared[15, 30]


def test_a_dialog_that_opens_with_nothing_focused_is_walked_once_round() -> None:
    found = focus_walk(FakeDialog(CONTROLS, focus=None), max_steps=20)

    assert len(found) == len(CONTROLS)


def test_focus_is_brought_to_a_control_by_tabbing_until_it_lands_there() -> None:
    dialog = FakeDialog(CONTROLS)

    assert focus_on(dialog, CONTROLS[2]) and dialog.focus == 2


def test_a_dialog_still_growing_as_it_opens_is_walked_once_it_has_its_size() -> None:
    # Save As and Save a Copy grew between two back-to-back shots (317 -> 796 rows), 2026-11-23.
    class Growing(FakeDialog):
        def shot(self) -> np.ndarray:
            image = super().shot()
            return image[:110] if self.shots == 1 else image

    found = focus_walk(Growing(CONTROLS, focus=None), max_steps=20)

    assert len(found) == len(CONTROLS)


def test_a_walk_that_never_comes_back_round_stops_at_its_limit() -> None:
    class Endless(FakeDialog):
        def send(self, events: list[Event]) -> None:
            if [e.key for e in events if isinstance(e, KeyUp)] == ["tab"]:
                self.controls.append((self.controls[-1][0], self.controls[-1][1] + 1, 300, 199))
                self.focus = len(self.controls) - 1

    found = focus_walk(Endless([(20, 20, 120, 40), (20, 60, 120, 80)]), max_steps=5)

    assert len(found) <= 6


def test_a_field_whose_whole_box_blinks_is_still_told_apart_by_its_text() -> None:
    """Photoshop's focused fields blink their whole box (846 px in Levels, 2026-11-10), so the
    blink mask hides every change inside; the field's own text still shows the answer."""

    class Blinking(Answering):
        shots = 0

        def shot(self) -> np.ndarray:
            image = super().shot()
            Blinking.shots += 1
            if Blinking.shots % 2:
                image[20:40, 20:120] = 250  # the box blinks between any two shots
            return image

    assert [probe(Blinking(kind), FOCUSED).kind for kind in ("number_field", "text_field")] == ["number_field", "text_field"]


def test_a_field_at_the_top_of_its_range_is_still_a_number_field() -> None:
    """Levels' white input field shows 255: Up cannot step it, Down can (2026-11-10)."""

    class AtMax(Answering):
        def send(self, events: list[Event]) -> None:
            keys = [e.key for e in events if isinstance(e, KeyDown)]
            if keys == ["up"] and self.value >= 5:
                return  # already at its maximum
            super().send(events)

    field = AtMax("number_field")

    found = probe(field, FOCUSED)

    assert (found.kind, field.value) == ("number_field", 7)  # stepped down and back, then the typed 7


def test_another_stop_pulsing_while_a_field_is_probed_is_not_taken_for_focus_moving() -> None:
    """Levels' fields were called text fields because the pulsing OK button, a tab stop,
    changed after Up: that looked like focus moving to it. It changes with no key pressed."""

    class PulsingStop(Answering):
        ticks = 0

        def shot(self) -> np.ndarray:
            image = super().shot()
            PulsingStop.ticks += 1
            image[60:80, 20:120] = 230 if (PulsingStop.ticks // 3) % 2 else 100  # a slow pulse
            return image

    found = probe(PulsingStop("number_field"), FOCUSED, known=[FOCUSED, (20, 60, 120, 80)])

    assert (found.kind, found.answers[0]) == ("number_field", "arrow keys change it")


def test_an_alert_that_opens_while_tabbing_to_a_control_is_answered_and_the_tabbing_goes_on() -> None:
    # Place Scale Marker, 2026-11-24: a Tab committed an out-of-range value, "A value between 0
    # and 600 is required" opened, and focus_on sent its 80 Tabs into the alert, then did the same
    # for every control after it; the run sat for minutes.
    class Alerting(FakeDialog):
        alert, tabs, answered = False, 0, 0

        def send(self, events: list[Event]) -> None:
            if self.alert:
                return  # a modal alert takes every key
            if [e.key for e in events if isinstance(e, KeyDown)] == ["tab"]:
                self.tabs += 1
                if self.tabs == 1:
                    self.alert = True  # the first Tab leaves a bad value behind
                    return
            super().send(events)

        def popups(self) -> int:
            return int(self.alert)

        def close_popups(self) -> None:
            self.alert, self.answered = False, self.answered + 1

    dialog = Alerting(CONTROLS)

    assert focus_on(dialog, CONTROLS[2]) and dialog.answered == 1


@pytest.mark.parametrize("phase", range(6))
def test_a_slow_pulse_is_never_taken_for_focus_moving_whatever_its_phase(phase: int) -> None:
    # Two still-check shots missed the pulse at phases 0 and 3 of 6, so the field was called a
    # text field a third of the time (found 2026-11-24, when one fewer shot shifted the phase).
    class PulsingStop(Answering):
        ticks = phase

        def shot(self) -> np.ndarray:
            image = super().shot()
            PulsingStop.ticks += 1
            image[60:80, 20:120] = 230 if (PulsingStop.ticks // 3) % 2 else 100
            return image

    found = probe(PulsingStop("number_field"), FOCUSED, known=[FOCUSED, (20, 60, 120, 80)])

    assert found.kind == "number_field"


def test_a_checkbox_that_makes_its_dialog_grow_is_still_found_as_a_checkbox() -> None:
    # Shadows/Highlights' Show More Options doubles the dialog's height (284 to 563 rows), and
    # Apply Image's Mask grows it too: the control's mask, made at the old size, failed on a
    # shape mismatch and the whole control pass with it (2026-11-24).
    class Growing(Answering):
        def shot(self) -> np.ndarray:
            image = super().shot()
            return np.concatenate([image, image]) if self.value == 0 else image  # ticked: taller

    assert probe(Growing("checkbox"), FOCUSED).kind == "checkbox"


def test_a_dialog_that_grew_since_the_last_blink_check_still_compares_its_shots() -> None:
    # Apply Image and Calculations grow when Mask is ticked: blinking pixels noted at one size
    # met shots at the other and the walk failed on a shape mismatch (2026-11-24).
    from scripts.adobe_observed_truth.controls import _Steady

    small = np.zeros((332, 623, 3), np.uint8)
    blinked = small.copy()
    blinked[10, 10] = 255

    class Surface:
        shots = iter([small, blinked])

        def shot(self) -> np.ndarray:
            return next(self.shots)

    steady = _Steady(Surface())
    steady.shot(tries=1)  # the caret blinked at the small size
    before = np.zeros((457, 623, 3), np.uint8)
    after = before.copy()
    after[400:420, 100:200] = 255

    changed = steady.changed(before, after)

    assert changed.shape == (457, 623) and changed[410, 150]
