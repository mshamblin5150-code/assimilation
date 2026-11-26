"""Drive every control of one open dialog and record what each action did.

Keyboard controls are found by walking the dialog with Tab and told apart by how they answer
keys (controls.probe), with no help from the catalogue. Controls the keyboard cannot reach
(dials, curves, swatches, previews) and controls that only show something (group boxes, text,
pictures) are placed through the catalogue (dialog-controls.jsonl): the drawn thing of the
right shape nearest its label as OCR reads it. A catalogued control that cannot be placed is
recorded as unplaced, never guessed. One row per control, the format control-actions.jsonl and
its coverage gate read.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable
from dataclasses import asdict, replace
from typing import Any, Protocol

from .control_drivers import (
    DRIVERS,
    PLACED_DRIVERS,
    READERS,
    Action,
    Control,
    Driver,
    mouse_candidates,
)
from .controls import (
    DialogClosed,
    ProbedSurface,
    Rect,
    WindowLeftOpen,
    _overlap,
    _within,
    focus_on,
    focus_walk,
    never_press,
    probe,
)
from .idle import Interrupted

# Kinds the probe names from how a focused control answers keys (controls.probe).
PROBED = frozenset({"number_field", "slider", "checkbox", "dropdown", "radio_group", "text_field", "button"})
_SQUARE = frozenset(
    {"angle_dial", "anchor_grid", "point_picker", "curve_graph", "color_swatch", "eyedropper", "on_image_adjust_tool"}
)
_WIDE = frozenset({"histogram_sliders", "gradient_bar", "star_rating", "column_headers"})
_TOOLS = frozenset({"eyedropper", "on_image_adjust_tool"})
_GRIP = 16  # a resize grip's size in the dialog's bottom-right corner
_MAX_GAP = 200  # a control further than this from its label is not taken to be its control
_ROW_GAP = 400  # ...unless on the label's own row (Levels' gear sits past the Preset dropdown)
# Words that describe a control rather than appear on screen ("Preset options", "gear menu").
_DESCRIPTORS = frozenset(
    ["options", "option", "menu", "icon", "button", "eyedropper", "slider", "sliders", "field", "toggle", "dropdown", "list", "box", "tool", "arrow", "arrows", "handle", "handles", "control", "bar", "swatch", "picker", "graph", "grid", "scroll", "scrollbar", "link", "tab", "tabs", "gear", "the", "a", "of", "for"]
)
_LABEL_GAP = 40  # a focusable control sits this close to its own label (field, box, slider)

Line = tuple[str, Rect]


class WordSurface(ProbedSurface, Protocol):
    def words(self) -> list[dict[str, Any]]: ...  # OCR of the whole dialog, with boxes


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _label_line(label: str | None, lines: list[Line]) -> Rect | None:
    """The line of text that is `label`: the same words, or starting with them."""
    want = _norm(label or "")
    if not want:
        return None
    exact = [r for text, r in lines if _norm(text) == want]
    if exact:
        return exact[0]
    starts = [r for text, r in lines if _norm(text).startswith(want + " ")]
    if starts:
        return starts[0]
    # A label that describes the control ("Preset options") is found by its distinctive words.
    core = " ".join(w for w in want.split() if w not in _DESCRIPTORS)
    if not core or core == want:
        return None
    near = [r for text, r in lines if _norm(text) == core or _norm(text).startswith(core + " ")]
    return near[0] if near else None


def _fits(kind: str, rect: Rect) -> bool:
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    aspect = w / h if h else math.inf
    if kind in _SQUARE:
        return 0.6 <= aspect <= 1.6
    if kind in _WIDE:
        return aspect >= 2
    if kind == "scrollbar_thumb":
        return aspect >= 3 or aspect <= 1 / 3
    return True


def _gap(a: Rect, b: Rect) -> float:
    dx = max(0, a[0] - b[2], b[0] - a[2])
    dy = max(0, a[1] - b[3], b[1] - a[3])
    return math.hypot(dx, dy)


def _same_row(label: Rect, rect: Rect, slack: int = 10) -> bool:
    return rect[1] < label[3] + slack and label[1] - slack < rect[3]


def _area(rect: Rect) -> int:
    return (rect[2] - rect[0]) * (rect[3] - rect[1])


def place(
    expected: list[dict[str, Any]], lines: list[Line], candidates: list[Rect], size: tuple[int, int]
) -> list[tuple[dict[str, Any], Control | None]]:
    """Where each catalogued control is on screen, in `expected` order (None: not placed).
    Shown types are their label's line; a mouse control is the nearest drawn thing of its
    shape beside its label (same row first); a resize grip is the bottom-right corner; the
    preview, the largest drawn thing left. Each drawn thing is claimed once."""
    height, width = size
    claimed: set[Rect] = set()
    found: dict[int, Control | None] = {}
    order = sorted(range(len(expected)), key=lambda i: expected[i]["type"] == "canvas_preview")
    for i in order:
        entry = expected[i]
        kind, label = entry["type"], entry.get("label") or ""
        anchor = _label_line(label, lines)
        rect: Rect | None = None
        if entry.get("box"):
            rect = _at_box(entry["box"], size, candidates, claimed)
        elif kind in READERS and kind != "static_image":
            rect = anchor
        elif kind == "resize_grip":
            rect = (width - _GRIP, height - _GRIP, width, height)
        elif kind == "canvas_preview":
            free = [c for c in candidates if c not in claimed]
            rect = max(free, key=_area) if free else None
        elif anchor is not None:
            near = [
                c for c in candidates
                if c not in claimed and _fits(kind, c) and _sized(kind, c)
                and _gap(anchor, c) <= (_ROW_GAP if _same_row(anchor, c) else _MAX_GAP)
            ]
            if near:
                rect = min(near, key=lambda c: (not _same_row(anchor, c), _gap(anchor, c)))
        if rect is not None and rect in candidates:
            claimed.add(rect)
            if kind in _TRACKS:
                rect = _with_handles(rect, candidates, claimed)
        found[i] = Control(kind, rect, label) if rect is not None else None
    _place_runs(expected, found, candidates, claimed)
    return [(expected[i], found[i]) for i in range(len(expected))]


def _scaled(box: list[float], size: tuple[int, int]) -> Rect:
    height, width = size
    return (round(box[0] * width), round(box[1] * height), round(box[2] * width), round(box[3] * height))


def _at_box(box: list[float], size: tuple[int, int], candidates: list[Rect], claimed: set[Rect]) -> Rect:
    """Where the catalogue's box is in the dialog as it is now: the drawn thing that mostly fills
    it (exact for this capture), else the box itself, scaled."""
    target = _scaled(box, size)
    free = [c for c in candidates if c not in claimed]
    best = max(free, key=lambda c: _overlap(c, target), default=None)
    return best if best is not None and _overlap(best, target) >= 0.5 else target


_TRACKS = frozenset({"histogram_sliders", "gradient_bar"})


def _with_handles(track: Rect, candidates: list[Rect], claimed: set[Rect]) -> Rect:
    """A slider track with the pieces it is drawn in (Levels' output bar is two, side by side on
    one row) and the small handles hanging just under it (its triangles), claimed with it: they
    are its parts, not controls."""
    x0, y0, x1, y1 = track
    grown = True
    while grown:  # pieces on the same row, one after another
        pieces = [
            c for c in candidates
            if c not in claimed and abs(c[1] - y0) <= 2 and abs(c[3] - y1) <= 2
            and (0 <= c[0] - x1 <= 40 or 0 <= x0 - c[2] <= 40)
        ]
        claimed.update(pieces)
        grown = bool(pieces)
        x0, x1 = min([x0, *(c[0] for c in pieces)]), max([x1, *(c[2] for c in pieces)])
    handles = [
        c for c in candidates
        if c not in claimed and max(c[2] - c[0], c[3] - c[1]) <= 24
        and c[0] >= x0 - 8 and c[2] <= x1 + 8 and y1 - 2 <= c[1] <= y1 + 24
    ]
    claimed.update(handles)
    return (
        min([x0, *(c[0] for c in handles)]),
        y0,
        max([x1, *(c[2] for c in handles)]),
        max([y1, *(c[3] for c in handles)]),
    )


# Sides (px) of the drawn things each kind can be, for placing controls no label names.
_SIDES = {
    "histogram_sliders": (30, 1000),
    "gradient_bar": (6, 1000),  # not a 1 px separator line
    "eyedropper": (12, 40),
    "on_image_adjust_tool": (12, 40),
    "color_swatch": (10, 60),
    "flyout_menu": (8, 30),
    "mode_toggle": (10, 40),
    "anchor_grid": (40, 130),
    "angle_dial": (20, 90),
    "point_picker": (40, 400),
    "curve_graph": (120, 600),
}


def _sized(kind: str, rect: Rect) -> bool:
    """Within the sides that kind of control is drawn at (any size if not known)."""
    low, high = _SIDES.get(kind, (0, 10_000))
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    return low <= min(w, h) and max(w, h) <= high


def _like(a: Rect, b: Rect) -> bool:
    """Same size within a quarter, on one row or one column."""
    wa, ha, wb, hb = a[2] - a[0], a[3] - a[1], b[2] - b[0], b[3] - b[1]
    same_size = abs(wa - wb) <= 0.25 * wa and abs(ha - hb) <= 0.25 * ha
    in_line = abs((a[1] + a[3]) - (b[1] + b[3])) <= 10 or abs((a[0] + a[2]) - (b[0] + b[2])) <= 10
    return same_size and in_line


def _place_runs(
    expected: list[dict[str, Any]], found: dict[int, Control | None], candidates: list[Rect], claimed: set[Rect]
) -> None:
    """Catalogued controls of one kind that no label placed (Levels' "Set Black Point
    eyedropper" is not text on screen) go, in catalogue order, onto the drawn things of that
    kind's shape and size read left to right: one onto the only one that fits, several onto the
    one run of like things of exactly that count. Anything less certain stays unplaced."""
    by_kind: dict[str, list[int]] = {}
    for i, entry in enumerate(expected):
        if found[i] is None and entry["type"] in _SIDES:
            by_kind.setdefault(entry["type"], []).append(i)
    for kind, wanted in by_kind.items():
        fit = [c for c in candidates if c not in claimed and _fits(kind, c) and _sized(kind, c)]
        if len(wanted) == 1:
            runs = [[c] for c in fit] if len(fit) == 1 else []
        else:
            runs = {tuple(sorted(d for d in fit if _like(c, d))) for c in fit}
            runs = [list(r) for r in runs if len(r) == len(wanted)]
        if len(runs) != 1:
            continue
        for i, rect in zip(wanted, sorted(runs[0], key=lambda r: (r[1] // 8, r[0])), strict=True):
            found[i] = Control(kind, rect, expected[i].get("label") or "")
            claimed.add(rect)


_LABEL_CHARS = 40  # a control's name; longer text is Adobe's prose, never published


def _fingerprint(text: str) -> dict[str, Any]:
    return {"chars": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest()}


def known_labels(catalogue: list[dict[str, Any]], strings: list[str]) -> set[str]:
    """Every catalogued label and every Photoshop interface string (mnemonic marks removed),
    normalised: the only text a published row may carry."""
    labels = {c.get("label") or "" for row in catalogue for c in row.get("controls", [])}
    drawn = {s.replace("&", "").replace("^", "") for s in strings}
    return {n for n in map(_norm, labels | drawn) if n}


def publishable(row: dict[str, Any], known: set[str] | None = None) -> dict[str, Any]:
    """`row` as it may go in the published dataset: no text read off the dialog (a reading
    becomes its length and hash, enough to show it was read and whether it changed), only
    labels short enough to be a control's name, as in dialog-controls.jsonl. Given `known`
    (Photoshop's own labels, normalised), a label is kept only if it is one of them: a file
    dialog lists the person's own files."""
    out = dict(row)
    if isinstance(out.get("read"), str):
        out["read"] = _fingerprint(out["read"])
    for key in ("label", "name"):
        text = out.get(key)
        if not isinstance(text, str) or not text:
            continue
        if len(text) > _LABEL_CHARS or (known is not None and _norm(text) not in known):
            out[key] = _fingerprint(text)
    if "actions" in out:
        out["actions"] = [{k: v for k, v in a.items() if k != "text_after"} for a in out["actions"]]
    return out


def controls_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per dialog: the kinds driven with an effect, driven with none, read, and not placed."""
    driven = {r["kind"] for r in rows if any(a.get("changed") for a in r.get("actions", []))}
    tried = {r["kind"] for r in rows if "actions" in r}
    return {
        "rows": len(rows),
        "driven": sorted(driven),
        "no_effect": sorted(tried - driven),
        "read": sorted({r["kind"] for r in rows if r.get("read")}),
        "unplaced": sorted({r["kind"] for r in rows if r.get("placed") is False}),
    }


def catalogued(rows: list[dict[str, Any]]) -> Callable[[str], list[dict[str, Any]]]:
    """Look up a menu path's catalogued controls (the fullest capture of it), matching by words
    ("Black  White" was "Black & White"). Captures reached by shortcut name no menu path."""
    best: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        command = row.get("command") or ""
        if command.startswith("Keyboard Shortcuts > "):
            continue
        key = _norm(command)
        if len(row["controls"]) > len(best.get(key, [])):
            best[key] = row["controls"]
    return lambda path: best.get(_norm(path), [])


def _lines(words: list[dict[str, Any]]) -> list[Line]:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    for word in words:
        grouped.setdefault(word["line"], []).append(word)
    out = []
    for ws in grouped.values():
        rect = (
            min(w["x"] for w in ws),
            min(w["y"] for w in ws),
            max(w["x"] + w["w"] for w in ws),
            max(w["y"] + w["h"] for w in ws),
        )
        out.append((" ".join(w["text"] for w in ws), rect))
    return out


def drive_dialog(
    surface: WordSurface,
    expected: list[dict[str, Any]],
    dialog: str,
    off_limits: list[Rect] | None = None,
    drive: bool = True,
) -> list[dict[str, Any]]:
    """Drive (or read) every control of the open dialog `dialog`; one row per control. With
    `drive` False it is a survey: each keyboard control is found and named (kind, label) but
    not driven through its values, which took about 4 minutes a dialog. If the
    dialog closes on the way, the rows so far are kept and the last names what closed it; so
    when a window it opened will not close (no key is sent past it). If
    input is stopped (the person is back, the foreground left), the stop goes on up with the
    rows so far (`.rows`), the last naming the control being driven."""
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {"dialog": dialog, "source": "walk"}
    try:
        _drive(surface, expected, dialog, rows, current, off_limits or [], drive)
    except DialogClosed:
        rows.append({"kind": "unknown", **current, "closed_dialog": True})  # kind if known
    except WindowLeftOpen as stuck:
        rows.append({"kind": "unknown", **current, "window_left_open": True, "left_open": getattr(stuck, "classes", [])})
    except Interrupted as stopped:
        rows.append({"kind": "unknown", **current, "interrupted": str(stopped)})
        stopped.rows = rows
        raise
    return rows


def _drive(
    surface: WordSurface,
    expected: list[dict[str, Any]],
    dialog: str,
    rows: list[dict[str, Any]],
    current: dict[str, Any],
    off_limits: list[Rect],
    drive: bool = True,
) -> None:
    lines = _lines(surface.words())  # labels as the dialog opened: driving can rename them
    size = surface.shot().shape[:2]
    menus = [_scaled(e["box"], size) for e in expected if e.get("box") and _is_command_menu(dialog, e)]
    stops = focus_walk(surface)
    for rect in stops:
        base = {"dialog": dialog, "rect": list(rect), "source": "keyboard"}
        current.clear()
        current.update(base)
        if any(_within(rect, area) > 0.5 for area in off_limits):
            rows.append({**base, "kind": "unknown", "skipped": "off limits"})
            continue
        if any(max(_within(rect, m), _within(m, rect)) > 0.5 for m in menus):
            rows.append({**base, "kind": "dropdown", "skipped": COMMAND_MENU_SKIPPED})
            continue
        if not focus_on(surface, rect):
            rows.append({**base, "kind": "unknown", "focused": False})
            continue
        found = probe(surface, rect, known=stops)
        if not drive:  # a survey: named, not driven
            rows.append({**base, "kind": found.kind, "label": found.label, "probe": list(found.answers)})
            continue
        if found.commands:  # choosing an entry runs it (Explorer opened from File Info)
            rows.append({**base, "kind": found.kind, "label": found.label, "probe": list(found.answers), "actions": [],
                         "skipped": "lists commands: opened and read, never chosen"})
            continue
        control = Control(found.kind, rect, found.label)
        if found.kind == "button" and found.pressed:
            # The probe pressed it already; a second press can show nothing new ("Pressed").
            actions = [Action(("space",), found.changed, None, found.opened_popup, surface.read_text(rect))]
        else:
            driver = DRIVERS.get(found.kind)
            actions = driver(surface, control) if driver else []
        rows.append({**base, "kind": found.kind, "label": found.label, "probe": list(found.answers), "actions": [asdict(a) for a in actions]})

    image = surface.shot()
    candidates = [
        c for c in mouse_candidates(image, stops, [r for _, r in lines])
        if not any(_within(c, area) > 0.5 for area in off_limits)
    ]
    wanted = _not_walked([e for e in expected if e["type"] != "unknown"], lines, rows, image.shape[:2])
    placed = place(wanted, lines, candidates, image.shape[:2])
    preview = next((c.rect for _, c in placed if c is not None and c.kind == "canvas_preview"), None)
    quiet: list[_Placed] = []  # driven, answered nothing: maybe hidden until something shows it
    for entry, control in placed:
        base = {"dialog": dialog, "kind": entry["type"], "label": entry.get("label") or "", "source": "catalogue label"}
        if control is None:
            rows.append({**base, "placed": False})
            continue
        base = {**base, "rect": list(control.rect), "placed": True}
        current.clear()
        current.update(base)
        if control.kind in READERS:
            rows.append({**base, "read": READERS[control.kind](surface, control)})
            continue
        if control.kind in _TOOLS and preview is not None:
            control = replace(control, target=preview)
        if never_press(control.label):
            rows.append({**base, "actions": [], "skipped": "never pressed"})
            continue
        if _is_command_menu(dialog, entry):
            rows.append({**base, "actions": [], "skipped": COMMAND_MENU_SKIPPED})
            continue
        # What is drawn there decides, not the catalogue's label: Hue/Saturation's self-drawn
        # OK took a placed "Preset" dropdown and the click accepted the dialog (2026-11-10).
        shown = [text for text, r in lines if _within(r, control.rect) > 0.5 and never_press(text)]
        if shown:
            rows.append({**base, "actions": [], "skipped": f"shows {shown[0]}: never pressed"})
            continue
        driver = PLACED_DRIVERS.get(control.kind) or DRIVERS[control.kind]
        actions = driver(surface, control)
        rows.append({**base, "actions": [asdict(a) for a in actions]})
        if not any(a.changed for a in actions):
            quiet.append((base, control, driver))
        elif control.kind == "button" and quiet:
            _retry_shown(surface, rows, quiet, base, control, driver)
    # Drawn but in no catalogue entry: an unlabelled icon may delete a preset, so it is only
    # recorded, for a catalogue update to name it.
    taken = {c.rect for _, c in placed if c is not None}
    for rect in candidates:
        if rect not in taken:
            rows.append({"dialog": dialog, "kind": "unknown", "rect": list(rect), "source": "drawn", "clicked": False})


# Catalogued dropdowns that are menus of commands, not settings: any key or click runs an
# entry. File Info's Template Folder: Home opened Explorer, Alt+Down opened Import's file
# dialog on the person's own folders (2026-11-11). Never keyed, probed or clicked.
COMMAND_MENUS = frozenset({("File > File Info", "Template Folder")})
COMMAND_MENU_SKIPPED = "a menu of commands: never keyed or clicked"


def _is_command_menu(dialog: str, entry: dict[str, Any]) -> bool:
    return (dialog, entry.get("label") or "") in COMMAND_MENUS


_Placed = tuple[dict[str, Any], Control, Driver]  # a catalogue row's base, where it is, its driver


def _retry_shown(
    surface: WordSurface, rows: list[dict[str, Any]], quiet: list[_Placed], base: dict[str, Any], button: Control, driver: Driver
) -> None:
    """A button changed the dialog: the controls that answered nothing are tried again (Filter
    Gallery hides its thumbnails until "Collapse/expand" is pressed, 2026-11-10). If one
    answers now, the button showed it; Photoshop keeps that after Cancel, so it is pressed
    again to leave the dialog as the person had it."""
    shown = False
    for entry in list(quiet):
        retry_base, control, retry = entry
        actions = retry(surface, control)
        rows.append({**retry_base, "retried_after": base["label"], "actions": [asdict(a) for a in actions]})
        if any(a.changed for a in actions):
            quiet.remove(entry)
            shown = True
    if shown:
        rows.append({**base, "put_back": True, "actions": [asdict(a) for a in driver(surface, button)]})


def _not_walked(
    expected: list[dict[str, Any]],
    lines: list[Line],
    walked: list[dict[str, Any]],
    size: tuple[int, int] | None = None,
) -> list[dict[str, Any]]:
    """The catalogued controls the Tab walk did not find. An entry with a box is found when a
    walked control sits at that box, whatever the probe called it (the row then keeps the
    catalogue's kind too, so a disagreement shows, and a disagreeing entry is placed and driven
    as the catalogue's kind as well). Without a box, an entry of a kind the probe
    names is found when a walked control of that kind sits by its label (or, its label not
    being on screen, when one of that kind is left over); everything else is placed."""
    claimed: set[int] = set()
    left: list[dict[str, Any]] = []
    for entry in expected:
        kind = entry["type"]
        if entry.get("box") and size is not None:
            target = _scaled(entry["box"], size)
            at = [
                i for i, r in enumerate(walked)
                if i not in claimed and r.get("source") == "keyboard"
                and (_overlap(tuple(r["rect"]), target) >= 0.3 or _within(target, tuple(r["rect"])) > 0.6
                     or _within(tuple(r["rect"]), target) > 0.6)
            ]
            if at:
                best = max(at, key=lambda i: _overlap(tuple(walked[i]["rect"]), target))
                claimed.add(best)
                walked[best]["name"], walked[best]["catalogued_as"] = entry.get("label"), kind
                if walked[best].get("kind") != kind:
                    left.append(entry)  # driven the catalogue's way too: the probe may be wrong
            else:
                left.append(entry)
            continue
        same = [i for i, r in enumerate(walked) if r.get("kind") == kind and i not in claimed]
        if kind not in PROBED or not same:
            left.append(entry)
            continue
        anchor = _label_line(entry.get("label"), lines)
        if anchor is None:
            claimed.add(same[0])
            continue
        near = [i for i in same if _gap(anchor, tuple(walked[i]["rect"])) <= _LABEL_GAP]
        if near:
            best = min(near, key=lambda i: (not _same_row(anchor, tuple(walked[i]["rect"])), _gap(anchor, tuple(walked[i]["rect"]))))
            claimed.add(best)
            walked[best]["name"] = entry.get("label")
        else:
            left.append(entry)
    for row in walked:
        if row.get("source") == "keyboard" and "name" not in row:
            row["name"] = _text_beside(tuple(row["rect"]), lines)
    return left


def _text_beside(rect: Rect, lines: list[Line]) -> str | None:
    """The text on the control's own row nearest to it: what a person would call it."""
    beside = [(text, r) for text, r in lines if _same_row(rect, r, slack=0) and _gap(rect, r) <= _LABEL_GAP]
    return min(beside, key=lambda line: _gap(rect, line[1]))[0] if beside else None


def main() -> None:
    """Write control-families.jsonl: one dialog_controls spec per catalogued dialog whose menu
    command may run unattended (the runner runs them with --specs control-families.jsonl)."""
    import argparse
    import json
    from pathlib import Path

    from .control_catalogue import load
    from .families import controls_scenario
    from .inventory import load_inventory

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    found = catalogued(load(args.dataset / "dialog-controls.jsonl"))
    specs = [
        spec
        for item in load_inventory(args.dataset / "inventory.jsonl")
        if item.kind == "menu_command" and found(item.path)
        if (spec := controls_scenario(item, sandbox=True)) is not None
    ]
    with (args.dataset / "control-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for spec in specs:
            out.write(json.dumps(asdict(spec)) + "\n")
    print(f"{len(specs)} dialogs to drive")


if __name__ == "__main__":
    main()
