"""Pen strokes sent as Windows pointer input (a synthetic pen device, InjectSyntheticPointerInput),
so an app reads pressure, tilt and rotation as it would from a tablet through Windows Ink.

pen_frames builds the frame sequence (hover in, press, move, lift, leave); inject sends it.

The synthetic pen reads its points from the virtual desktop's top-left corner, not the primary
monitor's (2026-11-26: with the desktop starting at x = -1440, a hover sent at 405 landed at
-1035), so inject moves every point by that corner (to_device). It only landed on the primary
monitor in that check, so inject hovers first and presses only if the cursor came to the first
point.
"""

from __future__ import annotations

import ctypes
import time
from collections.abc import Callable, Sequence
from ctypes import wintypes
from dataclasses import dataclass

INRANGE, INCONTACT, FIRSTBUTTON = 0x2, 0x4, 0x10
DOWN, UPDATE, UP = 0x10000, 0x20000, 0x40000
PT_PEN = 3
PRESSURE_MAX = 1024
PEN_MASK_PRESSURE, PEN_MASK_ROTATION, PEN_MASK_TILT_X, PEN_MASK_TILT_Y = 0x1, 0x2, 0x4, 0x8


@dataclass(frozen=True)
class Frame:
    flags: int
    x: int
    y: int
    pressure: int = 0
    tilt_x: int = 0
    tilt_y: int = 0
    rotation: int = 0


def pen_frames(points: Sequence[tuple[int, int]], pressures: Sequence[float],
               tilts: Sequence[tuple[int, int]] | None = None, rotations: Sequence[int] | None = None) -> list[Frame]:
    """One stroke through screen `points`, with pressure 0..1 at each (sent as 0..1024), and
    optional tilt (degrees, x and y) and rotation (degrees)."""
    tilts = tilts or [(0, 0)] * len(points)
    rotations = rotations or [0] * len(points)
    contact = INRANGE | INCONTACT | FIRSTBUTTON
    frames = [Frame(INRANGE | UPDATE, *points[0])]
    for i, (x, y) in enumerate(points):
        pressure = round(min(1.0, max(0.0, pressures[i])) * PRESSURE_MAX)
        frames.append(Frame(contact | (DOWN if i == 0 else UPDATE), x, y, pressure, *tilts[i], rotations[i]))
    frames += [Frame(INRANGE | UP, *points[-1]), Frame(UPDATE, *points[-1])]
    return frames


def to_device(point: tuple[int, int], virtual_origin: tuple[int, int]) -> tuple[int, int]:
    """A screen point as the synthetic pen takes it: from the virtual desktop's top-left corner."""
    return point[0] - virtual_origin[0], point[1] - virtual_origin[1]


class POINTER_INFO(ctypes.Structure):
    _fields_ = [("pointerType", wintypes.DWORD), ("pointerId", ctypes.c_uint32), ("frameId", ctypes.c_uint32),
                ("pointerFlags", ctypes.c_uint32), ("sourceDevice", wintypes.HANDLE), ("hwndTarget", wintypes.HWND),
                ("ptPixelLocation", wintypes.POINT), ("ptHimetricLocation", wintypes.POINT),
                ("ptPixelLocationRaw", wintypes.POINT), ("ptHimetricLocationRaw", wintypes.POINT),
                ("dwTime", wintypes.DWORD), ("historyCount", ctypes.c_uint32), ("InputData", ctypes.c_int32),
                ("dwKeyStates", wintypes.DWORD), ("PerformanceCount", ctypes.c_uint64), ("ButtonChangeType", ctypes.c_int)]


class POINTER_PEN_INFO(ctypes.Structure):
    _fields_ = [("pointerInfo", POINTER_INFO), ("penFlags", ctypes.c_uint32), ("penMask", ctypes.c_uint32),
                ("pressure", ctypes.c_uint32), ("rotation", ctypes.c_uint32), ("tiltX", ctypes.c_int32), ("tiltY", ctypes.c_int32)]


class POINTER_TOUCH_INFO(ctypes.Structure):  # only for the union's size
    _fields_ = [("pointerInfo", POINTER_INFO), ("touchFlags", ctypes.c_uint32), ("touchMask", ctypes.c_uint32),
                ("rcContact", wintypes.RECT), ("rcContactRaw", wintypes.RECT), ("orientation", ctypes.c_uint32),
                ("pressure", ctypes.c_uint32)]


class _Info(ctypes.Union):
    _fields_ = [("touchInfo", POINTER_TOUCH_INFO), ("penInfo", POINTER_PEN_INFO)]


class POINTER_TYPE_INFO(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _Info)]


_device: int | None = None


def _pen_device() -> int:
    global _device
    if _device is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.CreateSyntheticPointerDevice.restype = wintypes.HANDLE
        handle = user32.CreateSyntheticPointerDevice(PT_PEN, 1, 1)  # one pen, default feedback
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        _device = handle
    return _device


def inject(frames: Sequence[Frame], delay_s: float = 0.008, should_stop: Callable[[], bool] | None = None) -> None:
    """Send `frames` (screen points) through the synthetic pen; on a stop, the pen is lifted before
    returning. Nothing is pressed unless the first hover brings the cursor to the first point."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    origin = (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77))  # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN
    user32.InjectSyntheticPointerInput.argtypes = [wintypes.HANDLE, ctypes.POINTER(POINTER_TYPE_INFO), ctypes.c_uint32]
    device = _pen_device()

    def send(frame: Frame) -> None:
        info = POINTER_TYPE_INFO(type=PT_PEN)
        pen = info.penInfo
        pen.pointerInfo.pointerType = PT_PEN
        pen.pointerInfo.pointerFlags = frame.flags
        pen.pointerInfo.ptPixelLocation = wintypes.POINT(*to_device((frame.x, frame.y), origin))
        pen.penMask = PEN_MASK_PRESSURE | PEN_MASK_ROTATION | PEN_MASK_TILT_X | PEN_MASK_TILT_Y
        pen.pressure, pen.rotation, pen.tiltX, pen.tiltY = frame.pressure, frame.rotation, frame.tilt_x, frame.tilt_y
        if not user32.InjectSyntheticPointerInput(device, ctypes.byref(info), 1):
            raise ctypes.WinError(ctypes.get_last_error())

    for i, frame in enumerate(frames):
        if should_stop is not None and should_stop():
            last = frames[i - 1] if i else frame
            if last.flags & INCONTACT:
                send(Frame(INRANGE | UP, last.x, last.y))
            raise RuntimeError("stopped mid-stroke; the pen was lifted")
        send(frame)
        time.sleep(delay_s)
        if i == 0:
            time.sleep(0.1)
            at = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(at))
            if abs(at.x - frame.x) > 1 or abs(at.y - frame.y) > 1:
                send(Frame(UPDATE, frame.x, frame.y))
                raise RuntimeError(f"the pen's hover came to ({at.x}, {at.y}), not ({frame.x}, {frame.y}); nothing was pressed")
