"""Capture a window's own pixels, unaffected by windows overlapping it.

PrintWindow(PW_RENDERFULLCONTENT) asks the window to render itself, including
DirectComposition and GPU content, into our bitmap. The result is cropped to
DWMWA_EXTENDED_FRAME_BOUNDS, which excludes the invisible resize borders that
GetWindowRect includes. Coordinates are physical pixels (per-monitor DPI aware).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import TYPE_CHECKING

from .photoshop import sha256_file

if TYPE_CHECKING:
    from PIL.Image import Image

Rect = tuple[int, int, int, int]


PW_RENDERFULLCONTENT = 2
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = (
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    )


def frame_bounds(hwnd: int) -> Rect:
    """The window's visible frame in physical screen pixels: left, top, right, bottom."""
    from . import win_input

    win_input.make_dpi_aware()
    rect = wintypes.RECT()
    result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    if result != 0:
        raise OSError(f"DwmGetWindowAttribute failed: 0x{result & 0xFFFFFFFF:08X}")
    return rect.left, rect.top, rect.right, rect.bottom


def capture_window(hwnd: int, destination: Path, region: Rect | None = None) -> str:
    """Save the window's own rendering of `region` (default: its visible frame) as PNG; returns its SHA-256."""
    return save_png(grab(hwnd, region), destination)


def save_png(image: Image, destination: Path) -> str:
    """Write the image as PNG; returns the file's SHA-256."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
    return sha256_file(destination)


def grab(hwnd: int, region: Rect | None = None) -> Image:
    """The window's own rendering of `region`, in physical screen pixels (default: its visible frame)."""
    from PIL import Image as PILImage

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    user32.GetWindowDC.restype = ctypes.c_void_p
    gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
    gdi32.CreateCompatibleBitmap.restype = ctypes.c_void_p
    gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    gdi32.CreateCompatibleBitmap.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
    gdi32.GetDIBits.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
    ]
    user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.PrintWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]

    frame = frame_bounds(hwnd)
    window = wintypes.RECT()
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(window))
    width, height = window.right - window.left, window.bottom - window.top

    window_dc = user32.GetWindowDC(hwnd)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not user32.PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT):
            raise OSError("PrintWindow failed")
        header = BITMAPINFOHEADER(
            biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=width, biHeight=-height,  # top-down rows
            biPlanes=1, biBitCount=32, biCompression=0,
        )
        pixels = ctypes.create_string_buffer(width * height * 4)
        gdi32.SelectObject(memory_dc, previous)
        if gdi32.GetDIBits(memory_dc, bitmap, 0, height, pixels, ctypes.byref(header), DIB_RGB_COLORS) != height:
            raise OSError("GetDIBits failed")
    finally:
        gdi32.SelectObject(memory_dc, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)

    left, top, right, bottom = region or frame
    image = PILImage.frombuffer("RGB", (width, height), pixels.raw, "raw", "BGRX", 0, 1)
    return image.crop((left - window.left, top - window.top, right - window.left, bottom - window.top))
