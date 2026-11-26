"""Driving every control of one open dialog: keyboard controls found by Tab and told apart by
how they answer; mouse-only and shown controls placed through the catalogue's labels."""

from __future__ import annotations

import zlib

import numpy as np

from scripts.adobe_observed_truth.control_pass import (
    catalogued,
    controls_summary,
    drive_dialog,
    known_labels,
    place,
    publishable,
)
from scripts.adobe_observed_truth.controls import DialogClosed
from scripts.adobe_observed_truth.input_plan import (
    Event,
    KeyDown,
    KeyUp,
    MouseDown,
    MouseMove,
)

Rect = tuple[int, int, int, int]
SIZE = (200, 300)  # height, width


def test_a_shown_control_is_found_by_its_label_text() -> None:
    lines = [("Undefined Areas", (10, 100, 110, 112)), ("Radius:", (10, 20, 50, 32))]

    placed = place([{"type": "group_box", "label": "Undefined Areas"}], lines, [], SIZE)

    assert [(c.kind, c.rect) for _, c in placed] == [("group_box", (10, 100, 110, 112))]


def test_a_mouse_control_is_the_nearest_drawn_thing_of_its_shape_beside_its_label() -> None:
    lines = [("Angle:", (10, 50, 50, 62))]
    wide_track = (60, 52, 160, 58)
    dial = (170, 40, 200, 70)
    far_square = (20, 160, 50, 190)

    placed = place([{"type": "angle_dial", "label": "Angle"}], lines, [wide_track, far_square, dial], SIZE)

    assert placed[0][1].rect == dial


def test_a_resize_grip_is_the_bottom_right_corner_and_the_preview_the_largest_picture() -> None:
    small, preview = (200, 20, 230, 40), (10, 10, 150, 150)

    placed = place(
        [{"type": "resize_grip", "label": "Window resize grip"}, {"type": "canvas_preview", "label": "Preview"}],
        [],
        [small, preview],
        SIZE,
    )

    assert [c.rect for _, c in placed] == [(284, 184, 300, 200), preview]


def test_a_control_whose_label_is_not_on_screen_is_reported_unplaced() -> None:
    placed = place([{"type": "curve_graph", "label": "Curve"}], [("Radius:", (10, 20, 50, 32))], [], SIZE)

    assert placed == [({"type": "curve_graph", "label": "Curve"}, None)]


def test_two_controls_never_claim_the_same_drawn_thing() -> None:
    lines = [("Glow Color", (10, 50, 80, 62)), ("Vine Color", (10, 80, 80, 92))]
    swatch = (90, 48, 110, 64)

    placed = place(
        [{"type": "color_swatch", "label": "Glow Color"}, {"type": "color_swatch", "label": "Vine Color"}],
        lines,
        [swatch],
        SIZE,
    )

    assert [c.rect if c else None for _, c in placed] == [swatch, None]


class Dialog:
    """A dialog of tab-stop controls (drawn in the grey of their value, the focused one framed)
    plus mouse-only controls that change when pressed, and text lines OCR reads."""

    def __init__(self) -> None:
        self.controls = [
            {"kind": "number_field", "rect": (100, 20, 160, 36), "value": 10.0, "label": "", "tab": True},
            {"kind": "slider", "rect": (100, 50, 200, 58), "value": 50, "label": "", "tab": True},
            {"kind": "checkbox", "rect": (20, 80, 32, 92), "value": False, "label": "", "tab": True},
            {"kind": "button", "rect": (230, 20, 290, 40), "value": 0, "label": "OK", "tab": True},
            {"kind": "angle_dial", "rect": (170, 110, 200, 140), "value": 0, "label": "", "tab": False},
        ]
        self.lines = [("Radius:", (20, 22, 80, 34)), ("Angle:", (110, 118, 160, 130)), ("Options", (20, 150, 90, 162))]
        self.focus, self.typed, self.pointer, self.pressed = 0, "", (0, 0), []

    def tab_stops(self) -> list[dict]:
        return [c for c in self.controls if c["tab"]]

    def shot(self) -> np.ndarray:
        image = np.full((*SIZE, 3), 60, dtype=np.uint8)
        for c in self.controls:
            x0, y0, x1, y1 = c["rect"]
            typed = self.typed if c is self.tab_stops()[self.focus] else ""
            image[y0:y1, x0:x1] = 70 + zlib.crc32(f"{c['value']}{typed}".encode()) % 150
        x0, y0, x1, y1 = self.tab_stops()[self.focus]["rect"]
        image[y0 - 2 : y1 + 2, x0 - 2 : x0] = image[y0 - 2 : y1 + 2, x1 : x1 + 2] = 250
        image[y0 - 2 : y0, x0 - 2 : x1 + 2] = image[y1 : y1 + 2, x0 - 2 : x1 + 2] = 250
        return image

    def send(self, events: list[Event]) -> None:
        held: list[str] = []
        for event in events:
            if isinstance(event, KeyDown) and event.key in ("ctrl", "shift", "alt"):
                held.append(event.key)
            elif isinstance(event, KeyDown):
                self.press([*held, event.key])
            elif isinstance(event, KeyUp) and event.key in held:
                held.remove(event.key)
            elif isinstance(event, MouseMove):
                self.pointer = (event.x, event.y)
            elif isinstance(event, MouseDown):
                for c in self.controls:
                    x0, y0, x1, y1 = c["rect"]
                    if not c["tab"] and x0 <= self.pointer[0] < x1 and y0 <= self.pointer[1] < y1:
                        c["value"] += 1

    def press(self, keys: list[str]) -> None:
        stops = self.tab_stops()
        if keys in (["tab"], ["shift", "tab"]):
            c = stops[self.focus]
            if keys == ["tab"] and self.typed and c["kind"] == "number_field":
                c["value"] = float(self.typed)
            self.typed = ""
            self.focus = (self.focus + (1 if keys == ["tab"] else -1)) % len(stops)
            return
        c = stops[self.focus]
        if c["kind"] == "number_field":
            if keys == ["ctrl", "a"]:
                self.typed = ""
            elif keys in (["up"], ["down"]):
                c["value"] += 1 if keys == ["up"] else -1
            elif len(keys) == 1 and len(keys[0]) == 1:
                self.typed += keys[0]
        elif c["kind"] == "slider":
            moves = {"home": 0, "end": 100, "up": c["value"] + 1, "down": c["value"] - 1,
                     "pageup": c["value"] + 10, "pagedown": c["value"] - 10}
            if len(keys) == 1 and keys[0] in moves:
                c["value"] = max(0, min(100, moves[keys[0]]))
        elif c["kind"] == "checkbox" and keys == ["space"]:
            c["value"] = not c["value"]
        elif c["kind"] == "button" and keys == ["space"]:
            self.pressed.append(c["label"])
            c["value"] += 1  # drawn changed: the press shows

    def popups(self) -> int:
        return 0

    def read_text(self, rect: Rect) -> str:
        for text, r in self.lines:
            if r == rect:
                return text
        for c in self.controls:
            x0, y0, x1, y1 = c["rect"]
            if x0 - 3 <= rect[0] and rect[2] <= x1 + 3 and y0 - 3 <= rect[1] and rect[3] <= y1 + 3:
                if c["kind"] != "number_field":
                    return c["label"]
                being_typed = self.typed and c is self.tab_stops()[self.focus]
                return self.typed if being_typed else str(c["value"])  # a field shows what is typed
        return ""

    def words(self) -> list[dict]:
        return [
            {"text": text, "x": r[0], "y": r[1], "w": r[2] - r[0], "h": r[3] - r[1], "line": n}
            for n, (text, r) in enumerate(self.lines)
        ]


def test_every_control_of_a_dialog_is_driven_or_read_and_each_row_says_what_happened() -> None:
    dialog = Dialog()
    expected = [
        {"type": "angle_dial", "label": "Angle"},
        {"type": "group_box", "label": "Options"},
        {"type": "curve_graph", "label": "Curve"},
        {"type": "number_field", "label": "Radius"},  # found by Tab, not by label
    ]

    rows = drive_dialog(dialog, expected, "Filter > Test")

    driven = {r["kind"] for r in rows if any(a["changed"] for a in r.get("actions", []))}
    assert driven == {"number_field", "slider", "checkbox", "angle_dial"}
    assert [r["read"] for r in rows if r["kind"] == "group_box"] == ["Options"]
    assert [r["placed"] for r in rows if r["kind"] == "curve_graph"] == [False]
    assert dialog.pressed == []  # OK is identified, never pressed
    assert all(r["dialog"] == "Filter > Test" for r in rows)


def test_a_catalogued_dialog_is_found_by_its_menu_path_however_its_ampersand_was_written() -> None:
    dial = [{"type": "angle_dial", "label": "Angle"}]
    rows = [
        {"command": "Image > Adjustments > Black  White", "controls": [{"type": "slider", "label": "Reds"}]},
        {"command": "Image > Adjustments > Black  White", "controls": [*dial, {"type": "slider", "label": "Reds"}]},
        {"command": "Keyboard Shortcuts > Motion Blur...", "controls": dial},
    ]

    found = catalogued(rows)

    assert found("Image > Adjustments > Black & White") == [*dial, {"type": "slider", "label": "Reds"}]
    assert found("Filter > Blur > Motion Blur") == []  # shortcut captures name no menu path


def test_what_is_published_carries_no_text_read_off_the_dialog_only_short_labels() -> None:
    row = {
        "kind": "static_text",
        "label": "Radius:",
        "read": "The command is not currently available.",
        "actions": [{"changed": True, "text_after": "anything"}],
    }
    long_label = {"kind": "button", "label": "A label far too long to be a label, more like a sentence", "actions": []}

    assert [publishable(row), publishable(long_label)] == [
        {
            "kind": "static_text",
            "label": "Radius:",
            "read": {"chars": 39, "sha256": "599aa9522ed093c1c3557ebf864d79b6d0dea9a22e3aa2fdbcb8925968a1ae03"},
            "actions": [{"changed": True}],
        },
        {
            "kind": "button",
            "label": {"chars": 56, "sha256": "b663e977123b841c6674ba61cc6023a59eb5584b4d198e5caa4c7a81079ac79d"},
            "actions": [],
        },
    ]

def test_a_dialogs_summary_names_what_was_driven_with_an_effect_read_and_not_placed() -> None:
    rows = [
        {"kind": "slider", "actions": [{"changed": False}, {"changed": True}]},
        {"kind": "button", "actions": []},
        {"kind": "checkbox", "actions": [{"changed": False}]},
        {"kind": "group_box", "read": "Options"},
        {"kind": "curve_graph", "placed": False},
    ]

    assert controls_summary(rows) == {
        "rows": 5,
        "driven": ["slider"],
        "no_effect": ["button", "checkbox"],
        "read": ["group_box"],
        "unplaced": ["curve_graph"],
    }


def test_a_survey_names_each_keyboard_control_and_drives_none() -> None:
    # Driving every control took about 4 minutes a dialog (11 hours for Illustrator's 167); a
    # survey says what each dialog holds, and the ones worth it are driven later (2026-11-25).
    dialog = Dialog()

    rows = drive_dialog(dialog, [], "Filter > Test", drive=False)

    keyboard = [r for r in rows if r.get("source") == "keyboard"]
    assert [r["kind"] for r in keyboard] == ["number_field", "slider", "checkbox", "button"]
    assert all("actions" not in r for r in keyboard)


def test_a_button_the_probe_pressed_is_recorded_from_that_press_not_pressed_again() -> None:
    dialog = Dialog()
    dialog.controls.insert(3, {"kind": "button", "rect": (230, 50, 290, 70), "value": 0, "label": "Load...", "tab": True})

    rows = drive_dialog(dialog, [], "Filter > Test")

    load = next(r for r in rows if r.get("label") == "Load...")
    assert (dialog.pressed, load["kind"], [a["changed"] for a in load["actions"]]) == (["Load..."], "button", [True])


def test_controls_are_placed_by_their_labels_as_the_dialog_opened_not_as_driving_left_them() -> None:
    class Relabelling(Dialog):
        def press(self, keys: list[str]) -> None:
            super().press(keys)
            if self.tab_stops()[self.focus]["kind"] == "checkbox" and keys == ["space"]:
                self.lines[2] = ("Changed", self.lines[2][1])  # e.g. "Press me" -> "Pressed"

    rows = drive_dialog(Relabelling(), [{"type": "group_box", "label": "Options"}], "Filter > Test")

    assert [r["placed"] for r in rows if r["kind"] == "group_box"] == [True]


def test_a_catalogued_control_the_tab_walk_misses_is_placed_by_its_label_and_driven_by_mouse() -> None:
    dialog = Dialog()
    dialog.controls.append({"kind": "checkbox", "rect": (130, 170, 142, 182), "value": 0, "label": "", "tab": False})
    dialog.lines.append(("Invert", (150, 170, 200, 182)))

    rows = drive_dialog(dialog, [{"type": "checkbox", "label": "Invert"}], "Filter > Test")

    invert = [r for r in rows if r.get("label") == "Invert"]
    assert [(r["kind"], r["rect"], [a["changed"] for a in r["actions"]]) for r in invert] == [
        ("checkbox", [130, 170, 142, 182], [True, True])
    ]


def test_a_walked_control_is_named_by_its_catalogued_label_else_by_the_text_beside_it() -> None:
    dialog = Dialog()
    dialog.lines.append(("Amount", (20, 48, 80, 60)))  # beside the slider, which nothing catalogues

    rows = drive_dialog(dialog, [{"type": "number_field", "label": "Radius"}], "Filter > Test")

    names = {r["kind"]: r.get("name") for r in rows if r["source"] == "keyboard"}
    assert (names["number_field"], names["slider"], names["checkbox"]) == ("Radius", "Amount", None)


def test_a_drawn_thing_nothing_catalogues_is_recorded_but_never_clicked() -> None:
    dialog = Dialog()  # its angle dial is not in the catalogue entries given

    rows = drive_dialog(dialog, [], "Filter > Test")

    drawn = [(r["kind"], r["rect"], r["clicked"]) for r in rows if r["source"] == "drawn"]
    assert (drawn, dialog.controls[4]["value"]) == ([("unknown", [170, 110, 200, 140], False)], 0)


def test_a_dialog_that_closes_while_driven_keeps_the_rows_so_far_and_names_what_closed_it() -> None:
    class Closing(Dialog):
        closed = False

        def send(self, events: list[Event]) -> None:
            if self.closed:
                raise DialogClosed("the dialog is gone")
            super().send(events)

        def press(self, keys: list[str]) -> None:
            super().press(keys)
            if self.tab_stops()[self.focus]["kind"] == "checkbox" and keys == ["space"]:
                self.closed = True  # this checkbox's answer closed the dialog

    rows = drive_dialog(Closing(), [], "Filter > Test")

    assert [(r["kind"], r.get("closed_dialog", False)) for r in rows] == [
        ("number_field", False),
        ("slider", False),
        ("unknown", True),
    ]


def test_a_walked_controls_name_read_off_the_dialog_is_published_only_if_short() -> None:
    long_name = {"kind": "checkbox", "name": "A label far too long to be a label, more like a sentence"}
    short_name = {"kind": "slider", "name": "Amount"}

    assert [publishable(long_name)["name"], publishable(short_name)["name"]] == [
        {"chars": 56, "sha256": "b663e977123b841c6674ba61cc6023a59eb5584b4d198e5caa4c7a81079ac79d"},
        "Amount",
    ]


def test_a_placed_control_that_closes_the_dialog_is_named_by_its_kind() -> None:
    class Closing(Dialog):
        closed = False

        def send(self, events: list[Event]) -> None:
            if self.closed:
                raise DialogClosed("the dialog is gone")
            super().send(events)
            if any(isinstance(e, MouseDown) for e in events):
                self.closed = True  # the dial's first drag closed the dialog

    rows = drive_dialog(Closing(), [{"type": "angle_dial", "label": "Angle"}], "Filter > Test")

    assert [(r["kind"], r.get("label")) for r in rows if r.get("closed_dialog")] == [("angle_dial", "Angle")]


def test_input_stopped_mid_dialog_still_stops_the_run_and_keeps_the_rows_so_far() -> None:
    """Liquify lost the foreground to Explorer three times at the same spot (2026-11-10); no
    row survived to say which control was being driven. The stop still stops everything."""
    from scripts.adobe_observed_truth.idle import Interrupted

    class LosingFocus(Dialog):
        def send(self, events: list[Event]) -> None:
            if any(isinstance(e, MouseDown) for e in events):
                raise Interrupted("Foreground left the target process (to process 63500).")
            super().send(events)

    try:
        drive_dialog(LosingFocus(), [{"type": "angle_dial", "label": "Angle"}], "Filter > Test")
    except Interrupted as stopped:
        rows = stopped.rows
    else:
        raise AssertionError("the interruption was swallowed")

    assert [r["kind"] for r in rows[:-1]] == ["number_field", "slider", "checkbox", "button"]
    assert (rows[-1]["kind"], rows[-1]["label"], rows[-1]["interrupted"]) == (
        "angle_dial", "Angle", "Foreground left the target process (to process 63500).",
    )


def test_a_window_the_dialog_opened_that_will_not_close_stops_the_drive_and_says_so() -> None:
    """Liquify's Face tool opened a notice that ignores Escape (2026-11-10): every key after
    it went to the notice (Windows' error sound for each, and Tab plus Space can tick its
    "Don't show again") for sixteen minutes. Nothing more is sent once such a window stays."""

    class StuckNotice(Dialog):
        opened = False
        after: list[list[str]] = []

        def press(self, keys: list[str]) -> None:
            if self.opened:
                self.after.append(keys)
                return
            if keys == ["space"] and self.tab_stops()[self.focus]["kind"] == "checkbox":
                self.opened = True
                return
            super().press(keys)

        def popups(self) -> int:
            return int(self.opened)

        def popup_classes(self) -> list[str]:
            return ["PSFilter_WindowClass"] if self.opened else []

    dialog = StuckNotice()

    rows = drive_dialog(dialog, [{"type": "angle_dial", "label": "Angle"}], "Filter > Test")

    assert [r["kind"] for r in rows] == ["number_field", "slider", "unknown"]
    assert rows[-1]["rect"] == [17, 77, 35, 95] and rows[-1]["window_left_open"] is True  # the checkbox, framed
    # Which window stayed (Image Size left one open now and then, 2026-11-11): its class, not its text.
    assert rows[-1]["left_open"] == ["PSFilter_WindowClass"]
    assert dialog.after == [["escape"]]  # the one attempt to close it, nothing after


def test_a_control_hidden_until_a_later_button_shows_it_is_driven_then_and_the_panel_put_back() -> None:
    """Filter Gallery opened with its thumbnails hidden (2026-11-10): the grid, catalogued
    first, answered nothing; "Collapse/expand filter thumbnails", seven rows later, showed
    them, and Photoshop kept them shown after Cancel. A control that answered nothing is
    tried again once a button changes the dialog; a button that showed it is pressed back."""

    class HiddenPanel(Dialog):
        def __init__(self) -> None:
            super().__init__()
            self.controls.append({"kind": "button", "rect": (240, 150, 280, 170), "value": 0, "label": "", "tab": False})
            self.dial, self.panel = self.controls[4], self.controls[5]

        @property
        def dial_shown(self) -> bool:
            return self.panel["value"] % 2 == 1

        def shot(self) -> np.ndarray:
            image = super().shot()
            if not self.dial_shown:
                x0, y0, x1, y1 = self.dial["rect"]
                image[y0:y1, x0:x1] = 60  # the dialog's background
            return image

        def send(self, events: list[Event]) -> None:
            shown, value = self.dial_shown, self.dial["value"]
            super().send(events)
            if not shown:
                self.dial["value"] = value  # a hidden dial takes no clicks

    dialog = HiddenPanel()
    expected = [
        {"type": "angle_dial", "label": "Angle", "box": [170 / 300, 110 / 200, 200 / 300, 140 / 200]},
        {"type": "button", "label": "Show panel", "box": [240 / 300, 150 / 200, 280 / 300, 170 / 200]},
    ]

    rows = drive_dialog(dialog, expected, "Filter > Test")

    catalogue = [r for r in rows if r["source"] == "catalogue label"]
    assert [
        (r["kind"], r.get("retried_after"), r.get("put_back"), any(a["changed"] for a in r["actions"])) for r in catalogue
    ] == [
        ("angle_dial", None, None, False),
        ("button", None, None, True),
        ("angle_dial", "Show panel", None, True),
        ("button", None, True, True),
    ]
    assert not dialog.dial_shown  # left as the person had it


def test_a_dropdown_listing_commands_is_opened_and_read_but_nothing_is_ever_chosen_from_it() -> None:
    """File Info's Template Folder list holds commands (Import..., Export..., showing the
    folder), not values: Home chose the first and Explorer opened (2026-11-11)."""

    class CommandList(Dialog):
        def __init__(self) -> None:
            super().__init__()
            self.controls.insert(3, {"kind": "dropdown", "rect": (100, 150, 200, 166), "value": 0, "label": "", "tab": True})
            self.listed, self.ran = False, []

        def press(self, keys: list[str]) -> None:
            c = self.tab_stops()[self.focus]
            if c["kind"] != "dropdown" or keys in (["tab"], ["shift", "tab"]):
                return super().press(keys)
            if keys == ["alt", "down"]:
                self.listed = True
            elif keys == ["escape"]:
                self.listed = False
            elif keys in (["home"], ["end"], ["enter"]):
                self.ran.append(keys[0])  # choosing an entry runs that command
            elif keys in (["up"], ["down"]):
                c["value"] += 1 if keys == ["down"] else -1

        def popups(self) -> int:
            return int(self.listed)

        def popup_lines(self) -> list[str]:
            return ["Template Folder", "Import_", "Epot-", "No Templates Found"] if self.listed else []

    dialog = CommandList()

    rows = drive_dialog(dialog, [], "File > Test")

    listed = next(r for r in rows if r.get("kind") == "dropdown")
    assert dialog.ran == []
    assert (listed["actions"], listed["skipped"]) == ([], "lists commands: opened and read, never chosen")


def test_a_catalogued_command_menu_is_never_keyed_probed_or_clicked() -> None:
    """File Info's Template Folder dropdown runs an entry on any key: Home opened Explorer,
    Alt+Down opened Import's file dialog on the person's own folders (2026-11-11)."""

    class AnyKeyRuns(Dialog):
        def __init__(self) -> None:
            super().__init__()
            self.controls.insert(3, {"kind": "dropdown", "rect": (100, 150, 200, 166), "value": 0, "label": "", "tab": True})
            self.ran: list[list[str]] = []

        def press(self, keys: list[str]) -> None:
            if self.tab_stops()[self.focus]["kind"] == "dropdown" and keys not in (["tab"], ["shift", "tab"]):
                self.ran.append(keys)
                return
            super().press(keys)

        def send(self, events: list[Event]) -> None:
            super().send(events)
            menu = (100, 150, 200, 166)
            if any(isinstance(e, MouseDown) for e in events) and menu[0] <= self.pointer[0] < menu[2] and menu[1] <= self.pointer[1] < menu[3]:
                self.ran.append(["click"])

    dialog = AnyKeyRuns()
    entry = {"type": "dropdown", "label": "Template Folder", "box": [100 / 300, 150 / 200, 200 / 300, 166 / 200]}

    rows = drive_dialog(dialog, [entry], "File > File Info")

    assert dialog.ran == []
    assert [r["skipped"] for r in rows if r.get("skipped", "").startswith("a menu of commands")] != []


def test_a_run_of_like_controls_no_label_names_is_placed_in_order_on_a_run_of_like_icons() -> None:
    """Levels: three eyedroppers catalogued as "Set Black/Gray/White Point eyedropper" (no such
    text on screen) and three 20 px icons in a row (2026-11-10)."""
    gear, histogram = (352, 59, 365, 72), (14, 113, 368, 460)
    icons = [(442, 256, 462, 276), (404, 256, 424, 276), (479, 256, 499, 276)]
    entries = [{"type": "eyedropper", "label": f"Set {tone} Point eyedropper"} for tone in ("Black", "Gray", "White")]

    placed = place(entries, [("Preview", (420, 302, 470, 318))], [gear, *icons, histogram], (474, 521))

    assert [c.rect for _, c in placed] == [(404, 256, 424, 276), (442, 256, 462, 276), (479, 256, 499, 276)]


def test_a_run_is_not_guessed_when_the_counts_do_not_match() -> None:
    icons = [(404, 256, 424, 276), (442, 256, 462, 276), (479, 256, 499, 276)]
    entries = [{"type": "eyedropper", "label": "Set Black Point eyedropper"}, {"type": "eyedropper", "label": "Set White Point eyedropper"}]

    placed = place(entries, [], icons, (474, 521))

    assert [c for _, c in placed] == [None, None]
    assert place(entries[:1], [], icons[:1], (474, 521))[0][1].rect == icons[0]  # one fits one


def test_a_descriptive_label_is_found_by_its_distinctive_words_along_its_row() -> None:
    """Levels catalogues its gear menu as "Preset options": "Preset:" is on screen, the gear at
    the end of that row, past the dropdown (2026-11-10)."""
    gear, histogram, icon = (352, 59, 365, 72), (14, 113, 368, 460), (404, 256, 424, 276)

    placed = place([{"type": "flyout_menu", "label": "Preset options"}], [("Preset:", (14, 58, 61, 71))], [histogram, icon, gear], (474, 521))

    assert placed[0][1].rect == gear


def test_a_one_of_a_kind_shape_no_label_names_is_placed_by_its_size() -> None:
    graph, icon = (20, 120, 300, 400), (404, 256, 424, 276)

    placed = place([{"type": "curve_graph", "label": "curve"}], [("Channel:", (14, 100, 80, 112))], [icon, graph], (474, 521))

    assert placed[0][1].rect == graph


def test_text_read_in_a_dialog_is_published_only_if_it_is_a_known_photoshop_label() -> None:
    """A file dialog lists the person's own files: a name read there must never reach the
    published dataset. Given Photoshop's labels, only text among them is kept."""
    row = {"kind": "list_box", "label": "thesis-final.docx", "name": "Radius:", "actions": []}

    out = publishable(row, known={"radius"})

    assert (out["label"], out["name"]) == (
        {"chars": 17, "sha256": "b2ba284cdad25a3b8982f67e46cbecba2e5aef8e05d9f7080eb6eeb9e40ca2c9"},
        "Radius:",
    )


def test_known_labels_are_the_catalogues_and_photoshops_own_strings_as_drawn() -> None:
    catalogue = [{"controls": [{"type": "slider", "label": "Radius"}, {"type": "button", "label": None}]}]

    assert known_labels(catalogue, ["&Amount:", "Pre^view", "OK"]) == {"radius", "amount", "preview", "ok"}


def test_a_control_in_an_off_limits_area_is_recorded_but_never_touched() -> None:
    """A file dialog's folder pane lists the person's own folders, and arrowing through it
    opens each one (Place Linked, 2026-11-10): it is off limits."""
    dialog = Dialog()
    slider = dialog.controls[1]

    rows = drive_dialog(dialog, [], "File > Place Linked", off_limits=[(95, 45, 205, 63)])

    fenced = [r for r in rows if r.get("skipped") == "off limits"]
    assert ([r["rect"] for r in fenced], slider["value"]) == ([[97, 47, 203, 61]], 50)  # its focus frame; untouched


def test_a_placed_control_that_shows_ok_is_never_clicked_whatever_the_catalogue_calls_it() -> None:
    """Hue/Saturation's self-drawn OK is no tab stop: the catalogued Preset dropdown was placed on
    it and clicking it accepted the dialog (2026-11-10). What is drawn where a click lands
    decides, not the catalogue's label."""
    dialog = Dialog()
    ok = {"kind": "angle_dial", "rect": (230, 150, 290, 172), "value": 0, "label": "", "tab": False}
    dialog.controls.append(ok)
    dialog.lines += [("Preset", (150, 152, 200, 164)), ("OK", (250, 155, 270, 167))]

    rows = drive_dialog(dialog, [{"type": "dropdown", "label": "Preset"}], "Image > Adjustments > Hue/Saturation")

    preset = [r for r in rows if r.get("label") == "Preset"]
    assert (ok["value"], [r.get("skipped") for r in preset]) == (0, ["shows OK: never pressed"])


def test_slider_handles_hanging_under_their_track_belong_to_it() -> None:
    """Levels (2026-11-10, positions from its capture): the input histogram was placed on the
    graph alone, so its triangles stayed loose (and made the eyedroppers' run ambiguous), and
    the output bar went onto a 1 px separator line."""
    graph, separator, gear = (31, 164, 353, 291), (26, 353, 359, 354), (352, 59, 365, 72)
    out_bar = [(31, 383, 97, 399), (124, 383, 354, 399)]  # drawn in two pieces
    in_handles = [(26, 293, 41, 307), (169, 293, 184, 307), (343, 293, 357, 307)]
    out_handles = [(26, 401, 41, 415), (343, 401, 357, 415)]
    droppers = [(404, 256, 424, 276), (442, 256, 462, 276), (479, 256, 499, 276)]
    lines = [("Input Levels:", (28, 145, 118, 160)), ("Output Levels:", (28, 362, 125, 377)), ("Preset:", (14, 58, 61, 71))]
    entries = [
        {"type": "histogram_sliders", "label": "Input Levels"},
        {"type": "gradient_bar", "label": "Output Levels"},
        *({"type": "eyedropper", "label": f"Set {t} Point eyedropper"} for t in ("Black", "Gray", "White")),
    ]

    placed = place(entries, lines, [gear, graph, *in_handles, separator, *out_bar, *out_handles, *droppers], (474, 521))

    assert [c.rect for _, c in placed] == [(26, 164, 357, 307), (26, 383, 357, 415), *droppers]


def test_a_catalogued_box_places_a_control_whatever_its_label_says() -> None:
    """With positions in the catalogue, "Set Black Point eyedropper" (no such text on screen) is
    the drawn thing at its box, the box scaled to the dialog as it is now."""
    dropper, other = (404, 256, 424, 276), (442, 256, 462, 276)
    entry = {"type": "eyedropper", "label": "Set Black Point eyedropper", "box": [0.7754, 0.5401, 0.8138, 0.5823]}

    placed = place([entry], [], [other, dropper], (474, 521))

    assert placed[0][1].rect == dropper


def test_a_box_with_nothing_drawn_under_it_is_used_as_it_is() -> None:
    entry = {"type": "resize_grip", "label": "grip", "box": [0.5, 0.5, 0.6, 0.6]}

    placed = place([{**entry, "type": "color_swatch"}], [], [], (200, 400))

    assert placed[0][1].rect == (200, 100, 240, 120)


def test_a_walked_control_is_matched_to_its_catalogue_entry_by_box_and_named_by_it() -> None:
    entry = {"type": "number_field", "label": "Input black", "box": [0.3333, 0.1, 0.5333, 0.18]}  # no such text

    rows = drive_dialog(Dialog(), [entry], "Image > Adjustments > Levels")

    assert [(r["source"], r.get("name")) for r in rows if r["kind"] == "number_field"] == [("keyboard", "Input black")]


def test_a_walked_control_the_catalogue_calls_another_kind_is_driven_as_that_kind_too() -> None:
    """Colored Pencil's filter thumbnails were reached by Tab and probed as a slider; the
    catalogue's kind was never driven, so thumbnail grids stayed unproven (2026-11-10)."""
    entry = {"type": "thumbnail_grid", "label": "Filters", "box": [0.3333, 0.25, 0.6667, 0.29]}  # the slider

    rows = drive_dialog(Dialog(), [entry], "Filter > Test")

    def on_slider(rect: list[int]) -> bool:
        return 100 <= (rect[0] + rect[2]) / 2 <= 200 and 50 <= (rect[1] + rect[3]) / 2 <= 58

    at_box = [(r["source"], r["kind"], r.get("catalogued_as")) for r in rows if r.get("rect") and on_slider(r["rect"])]
    assert at_box == [("keyboard", "slider", "thumbnail_grid"), ("catalogue label", "thumbnail_grid", None)]
