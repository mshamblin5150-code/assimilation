"""Mouse-driven controls: what is clicked or dragged, and that nothing lands outside the control."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.adobe_observed_truth.control_drivers import (
    DRIVERS,
    READERS,
    Control,
    items_in,
    mouse_candidates,
)
from scripts.adobe_observed_truth.input_plan import Event, MouseDown, MouseMove, MouseUp

Rect = tuple[int, int, int, int]
RECT: Rect = (100, 100, 300, 200)


class Board:
    """A dialog that records every press and release position and changes a pixel each time;
    clicking inside `opens` opens a window."""

    def __init__(self, image: np.ndarray | None = None, opens: Rect | None = None) -> None:
        self.image = image if image is not None else np.full((400, 500, 3), 60, dtype=np.uint8)
        self.opens, self.popup = opens, False
        self.presses: list[tuple[int, int]] = []
        self.releases: list[tuple[int, int]] = []
        self.where = (0, 0)
        self.count = 0

    def shot(self) -> np.ndarray:
        image = self.image.copy()
        image[0, 0] = self.count % 256
        return image

    def send(self, events: list[Event]) -> None:
        for event in events:
            if isinstance(event, MouseMove):
                self.where = (event.x, event.y)
            elif isinstance(event, MouseDown):
                self.presses.append(self.where)
                if self.opens and _inside(self.where, self.opens):
                    self.popup = True
            elif isinstance(event, MouseUp):
                self.releases.append(self.where)
                self.count += 1
            elif getattr(event, "key", None) == "escape":
                self.popup = False

    def popups(self) -> int:
        return int(self.popup)

    def read_text(self, rect: Rect) -> str:
        return "label"


def _inside(point: tuple[int, int], rect: Rect) -> bool:
    return rect[0] <= point[0] < rect[2] and rect[1] <= point[1] < rect[3]


def strip_with_icons(count: int, rect: Rect = RECT) -> np.ndarray:
    image = np.full((400, 500, 3), 60, dtype=np.uint8)
    x0, y0, x1, y1 = rect
    width = (x1 - x0) // count
    for i in range(count):
        image[y0 + 20 : y1 - 20, x0 + i * width + 8 : x0 + (i + 1) * width - 8] = 180
    return image


# Every mouse-driven type except the resize grip, whose drag necessarily ends outside it (the
# window grows) and which has its own test below.
MOUSE_KINDS = [
    "tool_palette", "thumbnail_grid", "tab", "star_rating", "mode_toggle", "column_headers",
    "zoom_control", "scroll_arrows", "anchor_grid", "collapsible_section", "color_swatch",
    "flyout_menu", "address_bar", "canvas_preview", "angle_dial", "point_picker", "curve_graph",
    "histogram_sliders", "gradient_bar", "scrollbar_thumb", "eyedropper", "on_image_adjust_tool",
]


@pytest.mark.parametrize("kind", MOUSE_KINDS)
def test_a_mouse_driver_acts_and_never_presses_or_releases_outside_its_control(kind: str) -> None:
    board = Board(strip_with_icons(4))

    actions = DRIVERS[kind](board, Control(kind, RECT, ""))

    assert actions and board.presses, kind
    assert all(_inside(p, RECT) for p in board.presses + board.releases), kind


def test_icons_in_a_strip_are_found_one_by_one() -> None:
    crop = strip_with_icons(4)[100:200, 100:300]

    assert len(items_in(crop)) == 4


def test_each_tool_in_a_palette_is_clicked_once_at_its_icon() -> None:
    board = Board(strip_with_icons(4))

    DRIVERS["tool_palette"](board, Control("tool_palette", RECT, ""))

    width = (RECT[2] - RECT[0]) // 4
    assert sorted((x - RECT[0]) // width for x, _ in board.presses) == [0, 1, 2, 3]


def test_every_cell_of_an_anchor_grid_is_clicked() -> None:
    board = Board()

    DRIVERS["anchor_grid"](board, Control("anchor_grid", RECT, ""))

    cells = {((x - RECT[0]) * 3 // 200, (y - RECT[1]) * 3 // 100) for x, y in board.presses}
    assert len(cells) == 9


def test_a_colour_swatch_opens_the_colour_picker_which_is_recorded_and_closed() -> None:
    board = Board(opens=RECT)

    actions = DRIVERS["color_swatch"](board, Control("color_swatch", RECT, ""))

    assert (actions[0].opened_popup, board.popup) == (True, False)


def test_an_angle_dial_is_dragged_round_from_its_centre_to_four_directions() -> None:
    board = Board()

    DRIVERS["angle_dial"](board, Control("angle_dial", RECT, ""))

    cx, cy = (RECT[0] + RECT[2]) // 2, (RECT[1] + RECT[3]) // 2
    directions = {(np.sign(x - cx), np.sign(y - cy)) for x, y in board.releases}
    assert len(directions) >= 4


def test_a_section_header_is_opened_and_closed_again() -> None:
    board = Board()

    DRIVERS["collapsible_section"](board, Control("collapsible_section", RECT, ""))

    assert len(board.presses) == 2 and board.presses[0] == board.presses[1]


def test_a_resize_grip_is_dragged_out_and_back_to_its_start() -> None:
    board = Board()

    DRIVERS["resize_grip"](board, Control("resize_grip", RECT, ""))

    assert board.releases[-1] == board.presses[0]


def test_an_eyedropper_is_picked_then_used_on_the_dialogs_preview() -> None:
    board = Board()
    preview: Rect = (320, 220, 480, 380)

    DRIVERS["eyedropper"](board, Control("eyedropper", RECT, "", target=preview))

    assert _inside(board.presses[0], RECT) and any(_inside(p, preview) for p in board.presses[1:])


def test_things_drawn_in_a_dialog_that_are_neither_text_nor_known_tab_stops_are_candidates() -> None:
    image = np.full((300, 400, 3), 60, dtype=np.uint8)
    image[20:40, 20:120] = 150  # a tab stop already found by the keyboard walk
    image[60:70, 20:90] = 220  # a text label
    image[100:116, 200:216] = 180  # an icon nobody can Tab to
    image[150:160, 300:390] = 120  # a slider track

    found = mouse_candidates(image, known=[(20, 20, 120, 40)], text=[(20, 60, 90, 70)])

    assert sorted(found) == [(200, 100, 216, 116), (300, 150, 390, 160)]


def test_a_help_link_is_only_read_never_clicked() -> None:
    board = Board()

    text = READERS["help_link"](board, Control("help_link", RECT, ""))

    assert (text, board.presses) == ("label", [])
