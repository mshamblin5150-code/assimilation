"""Driving each kind of focused control through its values, recording what every action did."""

from __future__ import annotations

import zlib

import numpy as np

from scripts.adobe_observed_truth.control_drivers import DRIVERS, Control, timed
from scripts.adobe_observed_truth.input_plan import Event, KeyDown, KeyUp

Rect = tuple[int, int, int, int]
RECT: Rect = (20, 20, 120, 40)


class Widget:
    """One focused control of `kind`; its value is drawn as the grey of its rectangle and, for
    fields, is its text. Lists and radio groups have `options` values; numbers run 0..100."""

    def __init__(self, kind: str, value: object = 5, options: int = 4, label: str = "") -> None:
        self.kind, self.value, self.options, self.label = kind, value, options, label
        self.typed = ""
        self.selected = self.erased = False
        self.popup = False
        self.pressed: list[str] = []
        self.history: list[object] = []

    def shot(self) -> np.ndarray:
        image = np.full((100, 200, 3), 60, dtype=np.uint8)
        grey = 70 + zlib.crc32(str(self.value).encode()) % 150
        image[20:40, 20:120] = grey
        return image

    def send(self, events: list[Event]) -> None:
        """Each key press with the modifiers held at the time, in order."""
        held: list[str] = []
        for event in events:
            if isinstance(event, KeyDown) and event.key in ("ctrl", "shift", "alt"):
                held.append(event.key)
            elif isinstance(event, KeyDown):
                self.press([*held, event.key])
            elif isinstance(event, KeyUp) and event.key in held:
                held.remove(event.key)

    def press(self, keys: list[str]) -> None:
        k = self.kind
        if self.popup:
            if keys == ["escape"]:
                self.popup = False
            return
        if k in ("number_field", "text_field"):
            if keys == ["ctrl", "a"]:
                self.typed, self.selected = "", True
            elif keys in (["backspace"], ["delete"]) and self.selected:
                self.typed, self.erased = "", True
            elif keys == ["tab"]:
                if self.typed:
                    self.value = float(self.typed) if k == "number_field" else self.typed
                elif self.erased:
                    self.value = ""
                self.typed, self.selected, self.erased = "", False, False
            elif keys == ["up"] and k == "number_field":
                self.value = float(self.value) + 1
            elif keys == ["space"]:
                self.typed += " "
            elif len(keys) == 1 and len(keys[0]) == 1:
                self.typed += keys[0]
        elif k == "slider":
            moves = {"home": lambda v: 0, "end": lambda v: 100, "up": lambda v: min(100, v + 1),
                     "down": lambda v: max(0, v - 1), "pageup": lambda v: min(100, v + 10),
                     "pagedown": lambda v: max(0, v - 10)}
            if len(keys) == 1 and keys[0] in moves:
                self.value = moves[keys[0]](self.value)
        elif k in ("dropdown", "radio_group"):
            if keys == ["down"]:
                self.value = min(self.options - 1, int(self.value) + 1)
            elif keys == ["up"]:
                self.value = max(0, int(self.value) - 1)
            elif keys == ["home"]:
                self.value = 0
        elif k == "checkbox" and keys == ["space"]:
            self.value = not self.value
        elif k == "button" and keys == ["space"]:
            self.pressed.append(self.label)
            self.popup = True
        self.history.append(self.value)

    def popups(self) -> int:
        return int(self.popup)

    def read_text(self, rect: Rect) -> str:
        return str(self.value) if self.kind in ("number_field", "text_field") else self.label


def values_seen(widget: Widget) -> set[object]:
    return set(map(str, widget.history))


def test_a_number_field_is_typed_each_sweep_value_of_the_number_it_shows() -> None:
    widget = Widget("number_field", value=10)

    actions = DRIVERS["number_field"](widget, Control("number_field", RECT, "10"))

    assert {"2.5", "5.0", "20.0", "40.0"} <= values_seen(widget)
    assert all(a.changed for a in actions)


def test_a_slider_is_taken_to_both_ends_and_stepped_small_and_large() -> None:
    widget = Widget("slider", value=50)

    DRIVERS["slider"](widget, Control("slider", RECT, ""))

    assert {"0", "100", "1", "11"} <= values_seen(widget)


def test_a_checkbox_is_toggled_and_toggled_back() -> None:
    widget = Widget("checkbox", value=False)

    actions = DRIVERS["checkbox"](widget, Control("checkbox", RECT, ""))

    assert (len(actions), widget.value) == (2, False)


def test_while_timed_each_action_reports_its_control_and_when_it_ran() -> None:
    """A sampled sweep needs each control action's time window, to tell which code ran for it."""
    widget = Widget("checkbox", value=False)
    control = Control("checkbox", RECT, "Preview")
    seen: list[tuple[Control, int, int]] = []

    with timed(lambda c, t0, t1: seen.append((c, t0, t1))):
        DRIVERS["checkbox"](widget, control)
    DRIVERS["checkbox"](widget, control)  # no longer timed

    assert [c for c, _, _ in seen] == [control, control]
    assert all(0 < t0 <= t1 for _, t0, t1 in seen)
    assert seen[0][2] <= seen[1][1]  # in order, one after the other


def test_every_option_of_a_dropdown_and_a_radio_group_is_chosen_once() -> None:
    for kind in ("dropdown", "radio_group"):
        widget = Widget(kind, value=1, options=5)

        actions = DRIVERS[kind](widget, Control(kind, RECT, ""))

        assert values_seen(widget) >= {"0", "1", "2", "3", "4"}, kind
        assert sum(a.changed for a in actions) >= 4, kind


def test_options_stop_at_the_last_one_while_something_else_in_the_dialog_keeps_moving() -> None:
    """Levels' OK pulses and Image Size's preview redraws (2026-11-10): the dialog kept
    changing, so Down was pressed 300 times on a five-option list."""

    class Pulsing(Widget):
        frame = 0

        def shot(self) -> np.ndarray:
            # A default button pulsing slower than a blink: steady between two shots taken
            # back to back, moved on by the time the next key has been sent.
            image = super().shot()
            image[60:80, 150:190] = 80 + self.frame % 3 * 50
            return image

        def send(self, events: list[Event]) -> None:
            super().send(events)
            self.frame += 1

    widget = Pulsing("dropdown", value=2, options=5)

    actions = DRIVERS["dropdown"](widget, Control("dropdown", RECT, ""))

    downs = [a for a in actions if a.keys == ("down",)]
    assert len(downs) <= 5  # four moves and the one that shows the end
    assert values_seen(widget) >= {"0", "1", "2", "3", "4"}
    assert widget.value == 2  # back where it started


def test_a_text_field_is_typed_into() -> None:
    widget = Widget("text_field", value="")

    DRIVERS["text_field"](widget, Control("text_field", RECT, ""))

    assert "harness probe" in values_seen(widget)


def test_an_empty_text_field_is_emptied_again_afterwards() -> None:
    widget = Widget("text_field", value="")

    DRIVERS["text_field"](widget, Control("text_field", RECT, ""))

    assert widget.value == ""


def test_a_button_is_pressed_and_what_it_opens_is_recorded_and_closed() -> None:
    widget = Widget("button", label="Load...")

    actions = DRIVERS["button"](widget, Control("button", RECT, "Load..."))

    assert (widget.pressed, actions[0].opened_popup, widget.popup) == (["Load..."], True, False)


def test_a_button_that_ends_the_dialog_or_sends_content_is_never_pressed() -> None:
    for label in ("OK", "Cancel", "Generate", "Share"):
        widget = Widget("button", label=label)

        assert DRIVERS["button"](widget, Control("button", RECT, label)) == []
        assert widget.pressed == []


def test_a_button_whose_effect_outlives_cancel_is_never_pressed() -> None:
    labels = ("Delete", "Delete Preset", "Remove", "Rename...", "Reset All Warning Dialogs", "Save...",
              "Save Preset...", "Export...", "Clear", "Purge", "Sign In", "Install", "Update", "Buy",
              "Download", "Sync", "Send", "Print...", "Restore Defaults", "Append", "New...",
              "Add to Swatches", "Make Default", "Import...", "Replace...",
              "Open", "Place", "Done", "Select Folder")  # file dialogs; Done closes Save for Web
    for label in labels:
        widget = Widget("button", label=label)

        assert DRIVERS["button"](widget, Control("button", RECT, label)) == []
        assert widget.pressed == [], label
    load = Widget("button", label="Load...")  # opens a picker, closed again: nothing outlives Cancel
    DRIVERS["button"](load, Control("button", RECT, "Load..."))
    assert load.pressed == ["Load..."]


def test_a_button_that_opens_another_program_is_never_pressed() -> None:
    """File Info's Go to URL was clicked twice and Chrome started (2026-11-11): leaving the
    dialog for a browser or help viewer is the person's desktop, not the dialog's."""
    for label in ("Go to URL", "Learn More", "More Info...", "Help", "Visit Website"):
        widget = Widget("button", label=label)

        assert DRIVERS["button"](widget, Control("button", RECT, label)) == []
        assert widget.pressed == [], label


def test_a_driven_field_whose_box_blinks_still_shows_its_changes_through_its_text() -> None:
    class Blinking(Widget):
        shots = 0

        def shot(self) -> np.ndarray:
            image = super().shot()
            Blinking.shots += 1
            if Blinking.shots % 2:
                image[20:40, 20:120] = 250
            return image

    actions = DRIVERS["number_field"](Blinking("number_field", value=10), Control("number_field", RECT, "10"))

    assert [a.changed for a in actions] == [True, True, True, True, True]
