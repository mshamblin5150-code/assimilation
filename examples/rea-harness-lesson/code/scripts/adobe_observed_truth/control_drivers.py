"""Drive each kind of dialog control through its values and record what every action did.

A driver gets the dialog surface with focus already on the control (controls.focus_on) and
returns one Action per step: the keys or clicks sent, whether and where the dialog changed,
whether a window opened (it is captured by the caller and closed here with Escape), and the
control's text afterwards. Drivers put a control back to its starting value where they can
read it; the runner resets every dialog afterwards by replaying its recorded defaults.

DRIVERS and READERS must cover every control type in dialog-controls.jsonl
(test_adobe_observed_truth_control_coverage).
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np

from .controls import ProbedSurface, Rect, _Steady, close_popups, never_press, regions
from .input_plan import Event, chord
from .sweeps import sweep_values


@dataclass(frozen=True)
class Control:
    kind: str
    rect: Rect
    label: str = ""
    target: Rect | None = None  # where a tool acts (the dialog's preview), for eyedroppers


@dataclass(frozen=True)
class Action:
    keys: tuple[str, ...]
    changed: bool
    change: Rect | None = None  # bounding box of everything that changed in the dialog
    opened_popup: bool = False
    text_after: str = ""


Driver = Callable[[ProbedSurface, Control], list[Action]]
DRIVERS: dict[str, Driver] = {}
READERS: dict[str, Callable[[ProbedSurface, Control], str]] = {}


def _events(keys: tuple[str, ...]) -> list[Event]:
    return [event for key in keys for event in chord(key)]


def act(surface: ProbedSurface, control: Control, *keys: str) -> Action:
    """Send `keys` in order and record what changed; a window that opened is closed again."""
    return act_events(surface, control, _events(keys), keys)


Listener = Callable[[Control, int, int], None]  # (control, start ms, end ms)
_listeners: list[Listener] = []


@contextmanager
def timed(listener: Listener) -> Iterator[None]:
    """While inside, every action tells `listener` its control and the epoch milliseconds it
    started (input sent) and ended (the dialog settled): a sampled sweep's time windows."""
    _listeners.append(listener)
    try:
        yield
    finally:
        _listeners.remove(listener)


def act_events(
    surface: ProbedSurface, control: Control, events: list[Event], name: tuple[str, ...]
) -> Action:
    """Send `events` (keys, clicks, drags) and record what changed, as `act`. The control's
    own text counts too: a focused Photoshop field blinks its whole box, which the blink mask
    hides."""
    steady = _Steady(surface)
    before = steady.shot()
    text_before = surface.read_text(control.rect)
    started = int(time.time() * 1000)
    surface.send(events)
    after = steady.shot()
    for listener in _listeners:
        listener(control, started, int(time.time() * 1000))
    changed = steady.changed(before, after)
    boxes = regions(changed, min_area=1)
    box = None
    if boxes:
        box = (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )
    opened = surface.popups() > 0
    if opened:
        close_popups(surface)  # closes what opened, not the dialog
    text_after = surface.read_text(control.rect)
    return Action(tuple(name), bool(changed.any()) or text_after != text_before, box, opened, text_after)


def _typing(text: str) -> tuple[str, ...]:
    return tuple("space" if ch == " " else ch for ch in text)


def _number(text: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", "."))
    return float(match.group()) if match else None


def _commit(surface: ProbedSurface, control: Control, text: str) -> Action:
    """Replace a field's text and commit it (Tab), then come back (Shift+Tab). Empty text is
    put back by erasing the selection: selecting alone would leave the old text."""
    return act(surface, control, "ctrl+a", *(_typing(text) or ("backspace",)), "tab", "shift+tab")


def drive_number_field(surface: ProbedSurface, control: Control) -> list[Action]:
    # The label is the text before probing; probing typed into the field since.
    shown = control.label or surface.read_text(control.rect)
    start = _number(shown)
    if start is None:
        return [act(surface, control, "up"), act(surface, control, "down")]
    actions = [
        _commit(surface, control, _format(value))
        for value in sweep_values({"type": "double", "default": start})
    ]
    actions.append(_commit(surface, control, _format(start)))  # back to where it was
    return actions


def _format(value: float) -> str:
    return str(int(value)) if float(value).is_integer() and abs(value) < 1e15 else repr(float(value))


def drive_slider(surface: ProbedSurface, control: Control) -> list[Action]:
    return [act(surface, control, key) for key in ("home", "end", "home", "up", "pageup", "pagedown", "down")]


def drive_checkbox(surface: ProbedSurface, control: Control) -> list[Action]:
    return [act(surface, control, "space"), act(surface, control, "space")]


def drive_options(surface: ProbedSurface, control: Control, limit: int = 300) -> list[Action]:
    """Every option of a dropdown or radio group: to the first (Home), then Down until the
    control itself stops changing or shows an option again (a list that wraps); then back to
    the option it started on. The control's own pixels decide: the rest of the dialog can keep
    moving (Levels' pulsing OK, Image Size's preview, 2026-11-10)."""
    x0, y0, x1, y1 = control.rect
    original = surface.shot()[y0:y1, x0:x1].copy()
    actions = [act(surface, control, "home")]
    states = [surface.shot()[y0:y1, x0:x1].copy()]
    for _ in range(limit):
        step = act(surface, control, "down")
        actions.append(step)
        now = surface.shot()[y0:y1, x0:x1].copy()
        if not step.changed or any(np.array_equal(now, seen) for seen in states):
            break
        states.append(now)
    start = next((i for i, s in enumerate(states) if np.array_equal(s, original)), None)
    if start is not None:
        surface.send(_events(("home", *("down",) * start)))
    return actions


def drive_text_field(surface: ProbedSurface, control: Control) -> list[Action]:
    original = control.label or surface.read_text(control.rect)  # the text before probing
    return [_commit(surface, control, "harness probe"), _commit(surface, control, original)]


def drive_button(surface: ProbedSurface, control: Control) -> list[Action]:
    if never_press(control.label):
        return []
    return [act(surface, control, "space")]


# Mouse-driven controls -------------------------------------------------------------------
Point = tuple[int, int]


def items_in(crop: np.ndarray, min_area: int = 20) -> list[Point]:
    """Centres of the separate things drawn in `crop` (icons, thumbnails, stars, triangles):
    whatever differs from its most common colour, nearby pixels joined."""
    import cv2

    flat = crop.reshape(-1, crop.shape[-1])
    colours, counts = np.unique(flat, axis=0, return_counts=True)
    background = colours[counts.argmax()].astype(np.int16)
    mask = (np.abs(crop.astype(np.int16) - background).max(axis=-1) > 12).astype(np.uint8)
    joined = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    count, _, stats, centres = cv2.connectedComponentsWithStats(joined, connectivity=8)
    found = [
        (round(float(centres[i][0])), round(float(centres[i][1])))
        for i in range(1, count)
        if stats[i][4] >= min_area and stats[i][2] < crop.shape[1] and stats[i][3] < crop.shape[0]
    ]
    return sorted(found, key=lambda p: (p[1] // 8, p[0]))


def mouse_candidates(image: np.ndarray, known: list[Rect], text: list[Rect]) -> list[Rect]:
    """Everything drawn in the dialog that is neither a known tab stop nor text: the places a
    person could click that the keyboard walk cannot reach (icons, thumbs, swatches, handles).
    Each is clicked (unless its text is never pressed) and kept as a control if the dialog
    answers."""
    import cv2

    flat = image.reshape(-1, image.shape[-1])
    colours, counts = np.unique(flat, axis=0, return_counts=True)
    background = colours[counts.argmax()].astype(np.int16)
    mask = (np.abs(image.astype(np.int16) - background).max(axis=-1) > 12).astype(np.uint8)
    for x0, y0, x1, y1 in [*known, *text]:
        mask[max(0, y0 - 2) : y1 + 2, max(0, x0 - 2) : x1 + 2] = 0
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    height, width = image.shape[:2]
    found = []
    for i in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[i])
        if area >= 20 and w * h < 0.5 * width * height:
            found.append((x, y, x + w, y + h))
    return found


def _centre(rect: Rect) -> Point:
    return (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2


def _inside(point: tuple[float, float], rect: Rect, margin: int = 2) -> Point:
    """`point` moved just inside `rect`, so a drag never ends on a neighbouring control."""
    x0, y0, x1, y1 = rect
    return (
        int(min(max(point[0], x0 + margin), x1 - 1 - margin)),
        int(min(max(point[1], y0 + margin), y1 - 1 - margin)),
    )


def _click(surface: ProbedSurface, control: Control, point: Point) -> Action:
    from .input_plan import click

    return act_events(surface, control, click(point), (f"click {point[0]},{point[1]}",))


def _drag(surface: ProbedSurface, control: Control, start: Point, end: Point) -> Action:
    from .input_plan import drag

    return act_events(
        surface, control, drag(start, end, steps=8), (f"drag {start[0]},{start[1]}->{end[0]},{end[1]}",)
    )


def _items(surface: ProbedSurface, control: Control) -> list[Point]:
    x0, y0, x1, y1 = control.rect
    return [(x0 + x, y0 + y) for x, y in items_in(surface.shot()[y0:y1, x0:x1])]


def drive_click_items(surface: ProbedSurface, control: Control) -> list[Action]:
    """Click each thing drawn in the control (each tool, thumbnail, tab, star, toggle, arrow)."""
    points = _items(surface, control) or [_centre(control.rect)]
    return [_click(surface, control, point) for point in points]


def drive_anchor_grid(surface: ProbedSurface, control: Control) -> list[Action]:
    x0, y0, x1, y1 = control.rect
    w, h = x1 - x0, y1 - y0
    cells = [(x0 + w * (2 * c + 1) // 6, y0 + h * (2 * r + 1) // 6) for r in range(3) for c in range(3)]
    return [_click(surface, control, cell) for cell in cells]


def drive_toggle_twice(surface: ProbedSurface, control: Control) -> list[Action]:
    point = _centre(control.rect)
    return [_click(surface, control, point), _click(surface, control, point)]


def drive_open_once(surface: ProbedSurface, control: Control) -> list[Action]:
    """A click that opens something (colour picker, menu): recorded, and closed by `act`."""
    return [_click(surface, control, _centre(control.rect))]


def drive_canvas(surface: ProbedSurface, control: Control) -> list[Action]:
    x0, y0, x1, y1 = control.rect
    c = _centre(control.rect)
    return [
        _click(surface, control, c),
        _drag(surface, control, c, _inside((c[0] + (x1 - x0) / 4, c[1] + (y1 - y0) / 4), control.rect)),
    ]


def drive_angle_dial(surface: ProbedSurface, control: Control) -> list[Action]:
    import math

    x0, y0, x1, y1 = control.rect
    c = _centre(control.rect)
    r = 0.4 * min(x1 - x0, y1 - y0)
    return [
        _drag(surface, control, c, _inside((c[0] + r * math.cos(a), c[1] + r * math.sin(a)), control.rect))
        for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4)
    ]


def drive_point_picker(surface: ProbedSurface, control: Control) -> list[Action]:
    x0, y0, x1, y1 = control.rect
    c = _centre(control.rect)
    dx, dy = (x1 - x0) / 4, (y1 - y0) / 4
    corners = [(c[0] - dx, c[1] - dy), (c[0] + dx, c[1] - dy), (c[0] + dx, c[1] + dy), (c[0] - dx, c[1] + dy)]
    actions = [_drag(surface, control, c, _inside(p, control.rect)) for p in corners]
    actions.append(_drag(surface, control, _inside(corners[-1], control.rect), c))
    return actions


def drive_curve(surface: ProbedSurface, control: Control) -> list[Action]:
    """Add points along the diagonal (bottom-left to top-right) and drag each up a little."""
    x0, y0, x1, y1 = control.rect
    actions = []
    for t in (0.25, 0.5, 0.75):
        point = _inside((x0 + (x1 - x0) * t, y1 - (y1 - y0) * t), control.rect)
        actions.append(_click(surface, control, point))
        actions.append(_drag(surface, control, point, _inside((point[0], point[1] - (y1 - y0) / 8), control.rect)))
    return actions


def drive_handles(surface: ProbedSurface, control: Control, band: float = 0.35) -> list[Action]:
    """Drag each handle (histogram triangles, gradient stops) left and back: handles are the
    things drawn in the bottom part of the control."""
    x0, y0, x1, y1 = control.rect
    top = int(y1 - (y1 - y0) * band)
    handles = [(x0 + x, top + y) for x, y in items_in(surface.shot()[top:y1, x0:x1])]
    handles = handles or [_inside((x0 + 4, y1 - 4), control.rect), _inside((x1 - 4, y1 - 4), control.rect)]
    step = (x1 - x0) / 8
    actions = []
    for handle in handles:
        moved = _inside((handle[0] - step, handle[1]), control.rect)
        actions.append(_drag(surface, control, _inside(handle, control.rect), moved))
        actions.append(_drag(surface, control, moved, _inside(handle, control.rect)))
    return actions


def drive_gradient_bar(surface: ProbedSurface, control: Control) -> list[Action]:
    return [_click(surface, control, _centre(control.rect)), *drive_handles(surface, control)]


def drive_scrollbar_thumb(surface: ProbedSurface, control: Control) -> list[Action]:
    x0, y0, x1, y1 = control.rect
    c = _centre(control.rect)
    along = (c[0] + (x1 - x0) / 4, c[1]) if x1 - x0 >= y1 - y0 else (c[0], c[1] + (y1 - y0) / 4)
    end = _inside(along, control.rect)
    return [_drag(surface, control, c, end), _drag(surface, control, end, c)]


def drive_resize_grip(surface: ProbedSurface, control: Control) -> list[Action]:
    """Grow the window by dragging its grip, then drag the grip (now moved) back."""
    c = _centre(control.rect)
    out = (c[0] + 40, c[1] + 40)
    return [_drag(surface, control, c, out), _drag(surface, control, out, c)]


def drive_tool(surface: ProbedSurface, control: Control) -> list[Action]:
    """Pick the tool, use it on the dialog's preview when known, then click it again."""
    c = _centre(control.rect)
    actions = [_click(surface, control, c)]
    if control.target is not None:
        t = _centre(control.target)
        actions.append(_click(surface, control, t))
        width = control.target[2] - control.target[0]
        actions.append(_drag(surface, control, t, _inside((t[0] + width / 6, t[1]), control.target)))
    actions.append(_click(surface, control, c))
    return actions


def read_text(surface: ProbedSurface, control: Control) -> str:
    return surface.read_text(control.rect)


def read_image(surface: ProbedSurface, control: Control) -> str:
    from .ps_pixels import pixels_sha256

    x0, y0, x1, y1 = control.rect
    return pixels_sha256(surface.shot()[y0:y1, x0:x1])


READERS.update(
    {
        "static_text": read_text,
        "group_box": read_text,
        "progress_bar": read_text,
        "help_link": read_text,  # read only: a help link opens a browser
        "static_image": read_image,
    }
)

# Controls the Tab walk cannot reach take no keys (they never hold focus): placed through the
# catalogue, they are driven by mouse whatever their kind.
PLACED_DRIVERS: dict[str, Driver] = {
    "checkbox": drive_toggle_twice,
    "link_toggle": drive_toggle_twice,
    "list_box": drive_click_items,
    "radio_group": drive_click_items,
    "dropdown": drive_open_once,
    "slider": drive_scrollbar_thumb,
    "number_field": drive_open_once,
    "text_field": drive_open_once,
    "button": drive_open_once,
}

DRIVERS.update(
    {
        "number_field": drive_number_field,
        "slider": drive_slider,
        "checkbox": drive_checkbox,
        "link_toggle": drive_checkbox,
        "dropdown": drive_options,
        "radio_group": drive_options,
        "text_field": drive_text_field,
        "button": drive_button,
        "list_box": drive_options,
        "tool_palette": drive_click_items,
        "thumbnail_grid": drive_click_items,
        "tab": drive_click_items,
        "star_rating": drive_click_items,
        "mode_toggle": drive_click_items,
        "column_headers": drive_click_items,
        "zoom_control": drive_click_items,
        "scroll_arrows": drive_click_items,
        "anchor_grid": drive_anchor_grid,
        "collapsible_section": drive_toggle_twice,
        "color_swatch": drive_open_once,
        "flyout_menu": drive_open_once,
        "address_bar": drive_open_once,
        "canvas_preview": drive_canvas,
        "angle_dial": drive_angle_dial,
        "point_picker": drive_point_picker,
        "curve_graph": drive_curve,
        "histogram_sliders": drive_handles,
        "gradient_bar": drive_gradient_bar,
        "scrollbar_thumb": drive_scrollbar_thumb,
        "resize_grip": drive_resize_grip,
        "eyedropper": drive_tool,
        "on_image_adjust_tool": drive_tool,
    }
)
