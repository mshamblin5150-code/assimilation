"""Exact, ordered keyboard and mouse events for one observed behaviour.

Plans carry no timing; the executor paces events. Points are screen pixels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class KeyDown:
    key: str


@dataclass(frozen=True)
class KeyUp:
    key: str


@dataclass(frozen=True)
class MouseMove:
    x: int
    y: int


@dataclass(frozen=True)
class MouseDown:
    pass


@dataclass(frozen=True)
class MouseUp:
    pass


Event = KeyDown | KeyUp | MouseMove | MouseDown | MouseUp
Point = tuple[int, int]


def drag(
    start: Point,
    end: Point,
    *,
    steps: int,
    hold: tuple[str, ...] = (),
    hold_from: Literal["before_press", "mid_drag"] = "before_press",
) -> list[Event]:
    """Press, move in equal steps, release; hold keys from before the press or mid-drag."""
    moves: list[Event] = [
        MouseMove(
            round(start[0] + (end[0] - start[0]) * step / steps),
            round(start[1] + (end[1] - start[1]) * step / steps),
        )
        for step in range(1, steps + 1)
    ]
    presses = [KeyDown(key) for key in hold]
    if hold_from == "mid_drag":
        # After the first move, so the app has already begun the drag.
        moves[1:1] = presses
        presses = []
    return [
        *presses,
        MouseMove(*start),
        MouseDown(),
        *moves,
        MouseUp(),
        *(KeyUp(key) for key in reversed(hold)),
    ]


def chord(shortcut: str) -> list[Event]:
    """'shift+ctrl+z': press modifiers in written order, tap the last key, release in reverse."""
    # "ctrl++" is Ctrl with the plus key, not an empty key name.
    keys = [*shortcut[:-2].split("+"), "+"] if shortcut.endswith("++") else shortcut.split("+")
    return [*(KeyDown(key) for key in keys), *(KeyUp(key) for key in reversed(keys))]


def click(point: Point, *, hold: tuple[str, ...] = ()) -> list[Event]:
    return [
        *(KeyDown(key) for key in hold),
        MouseMove(*point),
        MouseDown(),
        MouseUp(),
        *(KeyUp(key) for key in reversed(hold)),
    ]
