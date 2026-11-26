"""Discover and drive a dialog's controls from its pixels and real input alone.

Most Photoshop dialogs are drawn by Photoshop itself, so UI Automation sees nothing inside
them. A person still can: this module works the way they do, through a `Surface` (a picture of
the dialog, and key presses and clicks sent to it). See the REA harness lesson's guide
(04-guide.md).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from .families import NEVER_PRESS as SENDS_OR_SPENDS
from .input_plan import Event, chord

Rect = tuple[int, int, int, int]  # x0, y0, x1, y1 (exclusive), dialog coordinates


class DialogClosed(Exception):
    """The dialog went away while it was being driven (raised by a surface's shot or send)."""


class WindowLeftOpen(Exception):
    """A window the dialog opened would not close (Liquify's face notice ignores Escape):
    every key sent from now on would go to it, so driving this dialog stops."""


class Surface(Protocol):
    def shot(self) -> np.ndarray: ...  # the dialog as an H x W x 3 image

    def send(self, events: list[Event]) -> None: ...  # input in dialog coordinates


class ProbedSurface(Surface, Protocol):
    def popups(self) -> int: ...  # windows the dialog has open on top of it (lists, menus...)

    def read_text(self, rect: Rect) -> str: ...  # OCR of that part of the dialog


# Buttons that act at once on presets, files, settings or the account: cancelling the dialog
# afterwards would not undo them. (Load opens a file picker, closed again with Escape.)
_OUTLIVES_CANCEL = (
    "delete", "remove", "rename", "reset", "restore", "save", "export", "clear", "purge",
    "sign", "install", "update", "buy", "download", "sync", "send", "print",
    "append", "new", "add", "make default", "import", "replace",
    # A file dialog's own buttons act on real files; Done closes Save for Web like OK.
    "open", "place", "select folder", "done",
    # They leave the dialog for another program on the person's desktop (File Info's Go to
    # URL started Chrome, 2026-11-11).
    "go to", "learn more", "more info", "help", "visit",
)
# Never pressed while driving: OK and Cancel end the dialog, then the buttons that spend
# credits or send content (the runner's list, families.NEVER_PRESS) and those above.
NEVER_PRESS = ("ok", "cancel", *(w.lower() for w in SENDS_OR_SPENDS), *_OUTLIVES_CANCEL)


@dataclass(frozen=True)
class Probe:
    """What the focused control is, from how it answered: kind, its own text, and whether
    pressing it opened something (closed again before returning)."""

    kind: str
    label: str
    opened_popup: bool = False
    answers: tuple[str, ...] = ()
    pressed: bool = False  # Space was pressed on it: a button's press is already done
    changed: bool = False  # ...and the control answered it
    commands: bool = False  # a dropdown whose list holds commands, not values: never chosen from


# A list entry that does something rather than set a value: File Info's Template Folder list
# (Import..., Export..., showing the folder in Explorer, 2026-11-11). OCR reads an ellipsis as
# "_" or "-" ("Import_", "Epot-").
COMMAND_WORDS = frozenset({"import", "export", "load", "save", "delete", "remove", "rename", "show", "open", "browse", "reveal", "manage"})


def lists_commands(lines: list[str]) -> bool:
    """Whether a dropdown's list holds commands: an entry ending in an ellipsis or starting
    with a command word."""
    for line in lines:
        text = line.strip()
        first = text.split()[0].lower().strip("&.:") if text else ""
        if text.endswith(("...", "…", "_", "-")) or first in COMMAND_WORDS:
            return True
    return False


def never_press(label: str) -> bool:
    # OCR reads O as 0 ("0K"): compare with that undone.
    words = label.strip().lower().replace("0", "o").rstrip(".").strip()
    return any(words == w or words.startswith(w + " ") for w in NEVER_PRESS)


def close_popups(surface: ProbedSurface) -> None:
    """Close what the dialog opened, never the dialog: a real dialog closes its own popups (a
    blind Escape can reach the dialog and cancel it); a stand-in surface takes Escape."""
    closer = getattr(surface, "close_popups", None)
    if closer is not None:
        closer()
    else:
        surface.send(chord("escape"))
    if surface.popups():
        stuck = WindowLeftOpen("a window the dialog opened would not close")
        stuck.classes = getattr(surface, "popup_classes", lambda: [])()  # what it was, never its text
        raise stuck


def probe(surface: ProbedSurface, rect: Rect, known: list[Rect] | None = None) -> Probe:
    """Tell what the focused control at `rect` is by how it answers keys, most harmless first:
    Alt+Down first (a dropdown opens a list, read and closed with no arrow key pressed: on some
    lists an arrow runs the entry it lands on), then Up/Down (numbers, sliders, radio buttons),
    a typed digit (fields), then Space (checkboxes, buttons). A button whose own text is OK,
    Cancel or a never-press word is identified and left unpressed. `known` are the dialog's
    tab stops: arrow keys that only move focus to one of them are navigation, while focus
    moving to a spot that is not a tab stop is a radio group's next option."""
    label = surface.read_text(rect)
    if never_press(label):
        return Probe("button", label, answers=("label",))
    x0, y0, x1, y1 = rect

    def inside(shape: tuple[int, ...]) -> np.ndarray:
        # Made at each comparison's size: a control can grow its dialog (Shadows/Highlights'
        # Show More Options, Apply Image's Mask, 2026-11-24).
        mask = np.zeros(shape[:2], dtype=bool)
        mask[y0:y1, x0:x1] = True
        return mask

    steady = _Steady(surface)
    others = [r for r in (known or []) if _overlap(r, rect) <= 0.5]
    answers: list[str] = []
    shown = [label]  # the control's text at the last reading

    def answer(keys: str) -> tuple[bool, list[Rect], bool]:
        """Send `keys`; did the control itself change (its pixels, or its text: a focused
        Photoshop field blinks its whole box, which the blink mask then hides), where else did
        anything change, and did its text change?"""
        before = steady.shot()
        surface.send(chord(keys))
        changed = steady.changed(before, steady.shot())
        text = surface.read_text(rect)
        text_changed, shown[0] = text != shown[0], text
        here = inside(changed.shape)
        return bool((changed & here).any()) or text_changed, regions(changed & ~here), text_changed

    # A dropdown first, by opening its list: on some an arrow key chooses an entry, and an
    # entry can be a command (File Info's Template Folder list opened Explorer, 2026-11-11).
    surface.send(chord("alt+down"))
    if surface.popups():
        listed = getattr(surface, "popup_lines", lambda: [])()  # read before it closes
        close_popups(surface)
        return Probe("dropdown", label, answers=("alt+down opens a list",), commands=lists_commands(listed))
    stepped, elsewhere, stepped_text = answer("up")
    elsewhere = _still(steady, elsewhere)  # a pulsing default button is not focus moving
    if any(_overlap(r, o) > 0.3 or _within(r, o) > 0.5 for r in elsewhere for o in others):
        # Focus went to another tab stop (WPF arrow navigation); this control changed only as
        # its focus frame left. Down may not undo it (focus can wrap): bring focus back by Tab.
        answers.append("arrow keys navigate")
        stepped = stepped_text = False
        focus_on(surface, rect)
        shown[0] = surface.read_text(rect)
    elif stepped:
        answer("down")  # back where it was
    else:
        # At the top of its range (Levels' white field shows 255) Up does nothing; Down can.
        stepped, below, stepped_text = answer("down")
        if stepped:
            answer("up")  # back where it was
            elsewhere = below
    if not answers:
        if elsewhere and not stepped:
            return Probe("radio_group", label, answers=("up moves focus off the tab stops",))
        if stepped:
            answers.append("arrow keys change it")
    # A field shows what is typed into it. A button's box can redraw when a key is pressed
    # (Curves' Auto, 2026-11-10), so a change alone does not make a field.
    typed, _, _ = answer("7")
    if typed and "7" in shown[0]:
        answers.append("typing changes it")
        kind = "number_field" if stepped_text else "text_field"
        return Probe(kind, label, answers=tuple(answers))
    if stepped:
        return Probe("slider", label, answers=tuple(answers))
    toggled, _, _ = answer("space")
    if surface.popups():
        close_popups(surface)
        return Probe("button", label, opened_popup=True, answers=("space opens a window",), pressed=True, changed=True)
    if toggled:
        return Probe("checkbox" if not label else "button", label, answers=("space toggles it",), pressed=True, changed=True)
    return Probe("button" if label else "unknown", label, answers=("no answer to keys",), pressed=True)


def _still(steady: _Steady, changes: list[Rect]) -> list[Rect]:
    """The changes that stay put when nothing is pressed: three more shots, and whatever changes
    among them is animation (Levels' pulsing OK button), not an answer to a key. Two shots
    missed a slow pulse at a third of its phases (found 2026-11-24)."""
    if not changes:
        return changes
    shots = [steady.shot() for _ in range(3)]
    if len({shot.shape for shot in shots}) > 1:  # the window is still changing size: nothing is still
        return []
    moving = np.any(shots[0] != shots[1], axis=-1) | np.any(shots[1] != shots[2], axis=-1)
    return [r for r in changes if not moving[r[1] : r[3], r[0] : r[2]].any()]


def focus_on(surface: Surface, rect: Rect, max_steps: int = 80) -> bool:
    """Tab until focus is on the control at `rect`. A change there can be focus arriving or
    leaving; one more Tab tells which (it changes again only if focus was there), then
    Shift+Tab steps back."""
    steady = _Steady(surface)
    previous = steady.shot()

    def touched(before: np.ndarray, after: np.ndarray) -> bool:
        return any(
            _overlap(r, rect) > 0.5 or _within(r, rect) > 0.5 for r in regions(steady.changed(before, after))
        )

    for _ in range(max_steps):
        surface.send(chord("tab"))
        if getattr(surface, "popups", lambda: 0)():
            # A Tab committed a bad value and an alert opened (Place Scale Marker's "a value
            # between 0 and 600", 2026-11-24): it takes every key until answered.
            close_popups(surface)
            previous = steady.shot()
            continue
        now = steady.shot()
        if touched(previous, now):
            surface.send(chord("tab"))
            beyond = steady.shot()
            surface.send(chord("shift+tab"))
            if touched(now, beyond):
                return True
            now = steady.shot()
        previous = now
    return False


class _Steady:
    """Shots with flicker removed: pixels that changed between two shots taken back to back
    (a blinking caret, an animation) are ignored from then on."""

    def __init__(self, surface: Surface) -> None:
        self.surface = surface
        self.noise: np.ndarray | None = None  # every pixel seen blinking (for callers' reports)
        self._blinks: list[tuple[np.ndarray, np.ndarray]] = []  # (shot, its blinking pixels)

    def shot(self, tries: int = 10) -> np.ndarray:
        """A shot once the window keeps its size (Save As grows as it opens), its blinking
        pixels noted."""
        second = self.surface.shot()
        for _ in range(tries):
            first = second
            # A caret blinks every ~530 ms: shots one blink apart catch it (real windows only).
            if pause := getattr(self.surface, "flicker_s", 0.0):
                time.sleep(pause)
            second = self.surface.shot()
            if second.shape == first.shape:
                break
        flicker = (np.any(first != second, axis=-1) if second.shape == first.shape
                   else np.zeros(second.shape[:2], dtype=bool))
        self.noise = flicker if self.noise is None or self.noise.shape != flicker.shape else self.noise | flicker
        self._blinks = [*self._blinks[-15:], (second, flicker)]
        return second

    def _blinking(self, image: np.ndarray) -> np.ndarray | None:
        return next((f for shot, f in self._blinks if shot is image), None)

    def changed(self, before: np.ndarray, after: np.ndarray) -> np.ndarray:
        """Pixels that changed: steady in both shots and different, or blinking in only one
        (focus arriving at or leaving a Photoshop field, which shows focus by blinking its
        box). A pixel blinking in both (a caret) is noise."""
        if before.shape != after.shape:
            return np.ones(after.shape[:2], dtype=bool)
        mask = np.any(before != after, axis=-1)
        blink_before, blink_after = self._blinking(before), self._blinking(after)
        if blink_before is None or blink_after is None:
            # Noise noted at another size (Apply Image grows with Mask, 2026-11-24) says nothing here.
            noise = self.noise if self.noise is not None and self.noise.shape == mask.shape else None
            return mask & ~noise if noise is not None else mask
        return (blink_before ^ blink_after) | (mask & ~blink_before & ~blink_after)


def regions(mask: np.ndarray, min_area: int = 40) -> list[Rect]:
    """The bounding boxes of the separate changed areas in `mask`, tiny specks left out.
    Pixels within 2 px of each other join first, so a dotted focus rectangle is one area."""
    joined = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    out = []
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if area >= min_area:
            out.append((int(x), int(y), int(x + w), int(y + h)))
    return out


def _overlap(a: Rect, b: Rect) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def _within(inner: Rect, outer: Rect) -> float:
    """The share of `inner` that lies inside `outer` (a focus frame drawn inside a control)."""
    ix = max(0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    iy = max(0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return ix * iy / area if area else 0.0


def _shared(first: list[Rect], second: list[Rect]) -> Rect | None:
    """The area that changed in both steps: focus arrived there in one and left in the next."""
    best, score = None, 0.5
    for a in first:
        for b in second:
            if (s := _overlap(a, b)) > score:
                best, score = a, s
    return best


def _focus_landed(steps: list[list[Rect]]) -> Rect | None:
    """The control focus visited on the last-but-one Tab: what changed on that Tab and the last
    (focus arriving, then leaving) but not on the one before. Something changing on three Tabs
    in a row is animation (Levels' pulsing default OK, 2026-11-10). With two controls every
    Tab changes both, so then the shared change is taken as it is."""
    def moving(step: list[Rect]) -> list[Rect]:
        return [r for r in step if not any(_overlap(r, q) > 0.5 for q in steps[-3])]

    return _shared(moving(steps[-2]), moving(steps[-1])) or _shared(steps[-2], steps[-1])


def _other(changes: list[Rect], known: Rect | None) -> Rect | None:
    rest = [r for r in changes if known is None or _overlap(r, known) <= 0.5]
    return max(rest, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])) if rest else None


def focus_walk(surface: Surface, max_steps: int = 80) -> list[Rect]:
    """Press Tab round the dialog once and return where focus lands, in tab order from the
    control focused at the start (or the first one Tab reaches, when nothing was). Each step's
    pixel change holds the focus leaving one control and arriving at the next; the area shared
    by consecutive steps is a control. The walk ends when the first control comes round
    again, or after `max_steps`."""
    steady = _Steady(surface)
    previous = steady.shot()
    steps: list[list[Rect]] = []
    landed: list[Rect] = []
    lap = False
    for _ in range(max_steps):
        surface.send(chord("tab"))
        now = steady.shot()
        steps.append(regions(steady.changed(previous, now)))
        previous = now
        if len(steps) > 2 and (rect := _focus_landed(steps)) is not None:
            if landed and _overlap(rect, landed[0]) > 0.5:
                lap = True
                break
            landed.append(rect)
    if not steps:
        return []
    last = None if lap else _other(steps[-1], landed[-1] if landed else None)
    if last is not None and not any(_overlap(last, r) > 0.5 for r in landed):
        landed.append(last)
    # Focused before the first Tab: what the first Tab changed besides the control it reached
    # (that one changed again on the second Tab, as focus left it).
    first_reached = next(
        (r for r in landed if any(_overlap(r, a) > 0.5 for a in steps[0]) and len(steps) > 1
         and any(_overlap(r, b) > 0.5 for b in steps[1])),
        None,
    )
    start = _other(steps[0], first_reached)
    if start is not None:
        for index, rect in enumerate(landed):
            if _overlap(rect, start) > 0.5:
                return landed[index:] + landed[:index]
    return landed
