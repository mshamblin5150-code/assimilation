"""Run probes only while the person is away, and give the machine back the moment they return.

Windows' own idle timer counts the harness's simulated input too, so it can never tell the
person apart from the probes. Low-level hooks can: every event carries an "injected" flag.
The watcher keeps only the time of the last real (not injected) event; it never records which
key or where the pointer went.
"""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Literal

from .input_plan import Event, KeyDown, KeyUp, MouseDown, MouseUp

Decision = Literal["run", "wait", "stop"]


class Interrupted(Exception):  # an interruption, not an error: no Error suffix
    """The machine stopped being available to the probes (the person returned, or locked it)."""


def decide(*, now: float, last_real_input: float, threshold_s: float, running: bool) -> Decision:
    if now - last_real_input >= threshold_s:
        return "run"
    return "stop" if running else "wait"


def release_plan(sent: list[Event]) -> list[Event]:
    """Events that let go of whatever `sent` left held: the mouse button first, then keys."""
    held: list[str] = []
    button_down = False
    for event in sent:
        if isinstance(event, KeyDown):
            held.append(event.key)
        elif isinstance(event, KeyUp) and event.key in held:
            held.remove(event.key)
        elif isinstance(event, MouseDown):
            button_down = True
        elif isinstance(event, MouseUp):
            button_down = False
    release: list[Event] = [MouseUp()] if button_down else []
    return release + [KeyUp(key) for key in reversed(held)]


WH_KEYBOARD_LL, WH_MOUSE_LL, HC_ACTION = 13, 14, 0
LLKHF_INJECTED, LLMHF_INJECTED = 0x10, 0x01
WM_MOUSEMOVE = 0x0200
_HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = (
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class _MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = (
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


# An attended run starts after this many quiet seconds; the person's input stops it at once.
ATTENDED_QUIET_S = 10.0


class PersonInput:
    """Which real (not injected) input events are the person. Keys, clicks and the wheel always
    are. A pointer move is only once it is more than DRIFT_PX from where the person last left
    it: an idle mouse reported 1 px moves about once a minute (2026-11-11), which never add up
    to that, while a hand on the mouse goes past it at once."""

    DRIFT_PX = 4

    def __init__(self) -> None:
        self.anchor: tuple[int, int] | None = None

    def counts(self, kind: str, at: tuple[int, int] | None = None) -> bool:
        if kind != "move":
            self.anchor = at or self.anchor
            return True
        if at is None:
            return True
        if self.anchor is None:
            self.anchor = at
            return False
        if max(abs(at[0] - self.anchor[0]), abs(at[1] - self.anchor[1])) <= self.DRIFT_PX:
            return False
        self.anchor = at
        return True


class RealInputWatcher:
    """Background hooks that note when the person last used the keyboard or mouse."""

    def __init__(self) -> None:
        self.last_real_input = time.monotonic()
        self.person = PersonInput()
        self._ready = threading.Event()
        self._thread_id = 0
        self._thread = threading.Thread(target=self._run, name="real-input-watcher", daemon=True)

    def start(self) -> RealInputWatcher:
        self._thread.start()
        if not self._ready.wait(5):
            raise RuntimeError("The input hooks did not start.")
        return self

    def stop(self) -> None:
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
        self._thread.join(5)

    def idle_s(self) -> float:
        return time.monotonic() - self.last_real_input

    def _run(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.SetWindowsHookExW.argtypes = (
            ctypes.c_int,
            _HOOKPROC,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        )
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.CallNextHookEx.argtypes = (
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        # Keep callbacks trivial: Windows drops hooks that answer slowly.
        def on_key(code: int, wparam: int, lparam: int) -> int:
            if code == HC_ACTION:
                event = ctypes.cast(lparam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if not event.flags & LLKHF_INJECTED:
                    self.last_real_input = time.monotonic()
            return user32.CallNextHookEx(None, code, wparam, lparam)

        def on_mouse(code: int, wparam: int, lparam: int) -> int:
            if code == HC_ACTION:
                event = ctypes.cast(lparam, ctypes.POINTER(_MSLLHOOKSTRUCT)).contents
                kind = "move" if wparam == WM_MOUSEMOVE else "click"
                if not event.flags & LLMHF_INJECTED and self.person.counts(kind, (event.pt.x, event.pt.y)):
                    self.last_real_input = time.monotonic()
            return user32.CallNextHookEx(None, code, wparam, lparam)

        key_proc, mouse_proc = _HOOKPROC(on_key), _HOOKPROC(on_mouse)
        hooks = [
            user32.SetWindowsHookExW(WH_KEYBOARD_LL, key_proc, None, 0),
            user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_proc, None, 0),
        ]
        if not all(hooks):
            raise ctypes.WinError(ctypes.get_last_error())
        self._ready.set()
        message = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                pass
        finally:
            for hook in hooks:
                user32.UnhookWindowsHookEx(hook)
