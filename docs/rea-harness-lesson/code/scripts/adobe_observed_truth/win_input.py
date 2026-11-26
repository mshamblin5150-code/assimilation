"""Send an input plan to one target process with SendInput, refusing any other foreground window."""

from __future__ import annotations

import ctypes
import math
import time
from collections.abc import Callable
from ctypes import wintypes

from .idle import Interrupted, release_plan
from .input_plan import Event, KeyDown, KeyUp, MouseDown, MouseMove, MouseUp

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
SPI_GETSCREENSAVERRUNNING = 0x0072
WM_CLOSE = 0x0010
SCREENSAVER_POLL_S = 0.1
DESKTOP_READOBJECTS, DESKTOP_WRITEOBJECTS = 0x0001, 0x0080
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.OpenDesktopW.restype = wintypes.HANDLE
user32.EnumDesktopWindows.argtypes = (wintypes.HANDLE, WNDENUMPROC, wintypes.LPARAM)
user32.CloseDesktop.argtypes = (wintypes.HANDLE,)

NAMED_KEYS = {
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "escape": 0x1B,
    "enter": 0x0D,
    "delete": 0x2E,
    "backspace": 0x08,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "[": 0xDB,
    "]": 0xDD,
}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class _INPUTUNION(ctypes.Union):
    # HARDWAREINPUT is never sent; MOUSEINPUT already sets the union size.
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT))


class INPUT(ctypes.Structure):
    _fields_ = (("type", wintypes.DWORD), ("u", _INPUTUNION))


def make_dpi_aware() -> None:
    # Per-monitor v2, so window rectangles and cursor positions share physical pixels.
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))


def foreground_pid() -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


def workstation_locked() -> bool:
    # While locked, the foreground belongs to LockApp.exe and input or captures cannot work.
    handle = kernel32.OpenProcess(0x1000, False, foreground_pid())  # QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    image = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(1024)
    kernel32.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size))
    kernel32.CloseHandle(handle)
    return image.value.lower().endswith("\\lockapp.exe")


def screensaver_running() -> bool:
    running = wintypes.BOOL()
    if not user32.SystemParametersInfoW(SPI_GETSCREENSAVERRUNNING, 0, ctypes.byref(running), 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return bool(running.value)


def close_screensaver() -> bool:
    """Ask the screensaver's windows to close; False if none could be reached."""
    # Windows runs even a non-secure screensaver on its own "Screen-saver" desktop, one window
    # per monitor (observed 2026-11-09: four D3DSaverWndClass windows for Mystify).
    access = DESKTOP_READOBJECTS | DESKTOP_WRITEOBJECTS
    desktop = user32.OpenDesktopW("Screen-saver", 0, False, access)
    if not desktop:
        return False
    posted: list[bool] = []

    def close(hwnd: int, _: int) -> bool:
        if user32.IsWindowVisible(hwnd):
            posted.append(bool(user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)))
        return True

    try:
        user32.EnumDesktopWindows(desktop, WNDENUMPROC(close), 0)
    finally:
        user32.CloseDesktop(desktop)
    return any(posted)


def clear_screensaver(
    *,
    running: Callable[[], bool] = screensaver_running,
    close: Callable[[], bool] = close_screensaver,
    sleep: Callable[[float], None] = time.sleep,
    timeout_s: float = 5.0,
) -> None:
    """Close a running screensaver without spending simulated input on waking it."""
    if not running():
        return
    if not close():
        # Unreachable, e.g. a password-protected screensaver whose desktop refuses this process.
        raise RuntimeError(
            "A screensaver is running but has no window the harness can close "
            "(password-protected?); input stopped."
        )
    for _ in range(max(1, math.ceil(timeout_s / SCREENSAVER_POLL_S))):
        sleep(SCREENSAVER_POLL_S)
        if not running():
            return
    raise RuntimeError(f"The screensaver did not close within {timeout_s:g} s; input stopped.")


def _take_foreground(hwnd: int) -> None:
    # Windows refuses SetForegroundWindow from a background process (this PC's foreground lock
    # timeout is the maximum). Sharing the foreground thread's input state lifts that, with no
    # simulated keystroke: 0/5 plain vs 5/5 attached after a screensaver clear, 2026-11-09.
    foreground_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    own_thread = kernel32.GetCurrentThreadId()
    attached = (
        foreground_thread != 0
        and foreground_thread != own_thread
        and bool(user32.AttachThreadInput(own_thread, foreground_thread, True))
    )
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(own_thread, foreground_thread, False)


_session_guard: Callable[[], bool] | None = None


def set_session_guard(should_stop: Callable[[], bool] | None) -> None:
    """The guard every focus and perform obeys when the caller passes none of its own: a
    session (run.py) sets the person-is-back check once, so no call can skip it."""
    global _session_guard
    _session_guard = should_stop


def _guard(should_stop: Callable[[], bool] | None) -> Callable[[], bool] | None:
    return should_stop if should_stop is not None else _session_guard


def focus(hwnd: int, pid: int, settle_s: float = 0.4, should_stop: Callable[[], bool] | None = None) -> None:
    # The foreground is the person's once they are back: asked before anything is touched.
    should_stop = _guard(should_stop)
    if should_stop is not None and should_stop():
        raise InputInterrupted("The person is back; the foreground stays theirs.")
    # A running screensaver owns the foreground, so close it before focusing the target.
    clear_screensaver()
    if workstation_locked():
        raise InputInterrupted("The workstation is locked; probes wait until it is unlocked.")
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE; never un-maximise a visible window
    _take_foreground(hwnd)
    time.sleep(settle_s)
    if foreground_pid() != pid:
        raise RuntimeError(
            "The target app is not the foreground window; click its title bar and rerun."
        )


class InputInterrupted(Interrupted, RuntimeError):
    """A plan stopped early; anything it held down has been released."""


TAKE_BACKS = 3  # times one plan brings its window back before giving up


def _take_back(hwnd: int, pid: int) -> bool:
    """Bring back `hwnd` (the window a plan began in) if it still belongs to `pid`."""
    owner = wintypes.DWORD()
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    if owner.value != pid:
        return False
    _take_foreground(hwnd)
    time.sleep(0.2)
    return True


def perform(
    plan: list[Event],
    *,
    pid: int,
    delay_s: float = 0.04,
    should_stop: Callable[[], bool] | None = None,
    send: Callable[[Event], None] | None = None,
    foreground: Callable[[], int] = foreground_pid,
    take_back: Callable[[], bool] | None = None,
) -> None:
    """Send `plan` to `pid`; stop between events if it loses the foreground or `should_stop()`.

    Another program that comes forward while the person is away (no real input: the Claude
    app raised itself mid-command, 2026-11-24) is answered by `take_back()`, which brings back
    the window the plan began in (default), at most TAKE_BACKS times; the person coming back
    still stops the plan at once.

    However it ends early, anything the plan pressed is released before the error propagates:
    a held Shift or mouse button would follow the person into whatever they do next.
    """
    should_stop = _guard(should_stop)
    deliver = send or (lambda event: _send(_to_input(event)))
    sent: list[Event] = []
    began_in = user32.GetForegroundWindow() if take_back is None and send is None else 0
    take_back = take_back or (lambda: _take_back(began_in, pid))
    takes = 0
    try:
        for event in plan:
            if should_stop is not None and should_stop():
                raise InputInterrupted(f"Stopped before {event}: should_stop() was true.")
            owner = foreground()
            for _ in range(10):  # no foreground window at all (mid window resize): give it a moment
                if owner != 0:
                    break
                time.sleep(0.05)
                owner = foreground()
            if owner != pid and owner != 0 and should_stop is not None and takes < TAKE_BACKS:
                takes += 1
                if take_back():
                    owner = foreground()
            if owner != pid:
                raise InputInterrupted(f"Foreground left the target process before {event} (to process {owner}).")
            deliver(event)
            sent.append(event)
            time.sleep(delay_s)
    except BaseException:
        for release in release_plan(sent):
            deliver(release)
        raise


def _to_input(event: Event) -> INPUT:
    if isinstance(event, (KeyDown, KeyUp)):
        up = KEYEVENTF_KEYUP if isinstance(event, KeyUp) else 0
        if _typed_as_character(event.key):
            # Typed as the character itself: the bare key of a capital or symbol types something
            # else ("D" types d; "%" has no key of its own).
            return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, ord(event.key), _KEYEVENTF_UNICODE | up, 0, 0)))
        vk = _virtual_key(event.key)
        flags = up
        scan = user32.MapVirtualKeyW(vk, 0)
        return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(vk, scan, flags, 0, 0)))
    if isinstance(event, MouseMove):
        dx, dy = _absolute(event.x, event.y)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        return INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(dx, dy, 0, flags, 0, 0)))
    flags = MOUSEEVENTF_LEFTDOWN if isinstance(event, MouseDown) else MOUSEEVENTF_LEFTUP
    assert isinstance(event, (MouseDown, MouseUp))
    return INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(0, 0, 0, flags, 0, 0)))


_MORE_KEYS = {
    "tab": 0x09,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "insert": 0x2D,
    "-": 0xBD,
    "=": 0xBB,
    "+": 0xBB,  # the =/+ key: Photoshop's "Ctrl++" is Ctrl with this key
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
    ";": 0xBA,
    "'": 0xDE,
    "`": 0xC0,
    "\\": 0xDC,
}


_KEYEVENTF_UNICODE = 0x0004


def _typed_as_character(key: str) -> bool:
    """A single printable character with no key code of its own for typing it: capitals and
    symbols. Lowercase letters, digits and the punctuation keys above keep their key codes
    (shortcuts such as Ctrl+A and Ctrl++ need them)."""
    return len(key) == 1 and key.isprintable() and key != " " and not (key.islower() or key.isdigit()) and key not in _MORE_KEYS


def _virtual_key(key: str) -> int:
    if key in NAMED_KEYS:
        return NAMED_KEYS[key]
    if key in _MORE_KEYS:
        return _MORE_KEYS[key]
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        return 0x6F + int(key[1:])  # VK_F1 is 0x70
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    raise ValueError(f"No virtual-key mapping for {key!r}")


_MODIFIER_FLAGS = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
_MOD_NOREPEAT = 0x4000


def hotkey(shortcut: str) -> tuple[int, int]:
    """'shift+ctrl+z' as RegisterHotKey's (modifier flags, virtual key)."""
    keys = [*shortcut[:-2].split("+"), "+"] if shortcut.endswith("++") else shortcut.split("+")
    *modifiers, key = keys
    return sum(_MODIFIER_FLAGS[m] for m in modifiers), _virtual_key(key)


def _register_and_release(modifiers: int, key: int) -> bool:
    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, 0xBEEF, modifiers | _MOD_NOREPEAT, key):
        return False
    user32.UnregisterHotKey(None, 0xBEEF)
    return True


def owned_elsewhere(
    shortcut: str, register: Callable[[int, int], bool] = _register_and_release
) -> bool:
    """Whether another program holds this key combination system-wide (Windows refuses to
    register it), so pressing it would make that program act instead of Photoshop."""
    combination = hotkey(shortcut)
    if combination == (0, _VK_F12):  # reserved for debuggers: always refused, yet free to press
        return False
    return not register(*combination)


_VK_F12 = 0x7B


def _absolute(x: int, y: int) -> tuple[int, int]:
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return (
        round((x - left) * 65535 / (width - 1)),
        round((y - top) * 65535 / (height - 1)),
    )


def _send(item: INPUT) -> None:
    if user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT)) != 1:
        raise ctypes.WinError(ctypes.get_last_error())
