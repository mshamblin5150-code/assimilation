"""A real Photoshop dialog as a controls.Surface: its own rendering (PrintWindow), real input
(SendInput, only while it is in the foreground), the windows it opens, and OCR of its text.

Photoshop draws most dialog text light on dark; OCR reads it inverted and enlarged (OCR_SCALE).
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import tempfile
import time
from ctypes import wintypes
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from . import capture, win_input
from .controls import DialogClosed
from .corpus import CORPUS
from .input_plan import Event, MouseMove, chord, click
from .ocr_correct import Corrector

Rect = tuple[int, int, int, int]
OCR_EXE = (
    Path(__file__).parent / "win_ocr" / "bin" / "Release" / "net9.0-windows10.0.19041.0" / "WinOcr.exe"
)


RAPID_PYTHON = CORPUS / "ocr-venv" / "Scripts" / "python.exe"
RAPID_SERVER = Path(__file__).parent / "rapid_ocr_server.py"


def ocr_command() -> list[str]:
    """RapidOCR when its venv is installed (it read more labels than Windows OCR), else
    Windows' built-in OCR. Both take one image path per line and answer one JSON line."""
    if RAPID_PYTHON.exists():
        return [str(RAPID_PYTHON), "-I", str(RAPID_SERVER)]
    return [str(OCR_EXE)]


class Ocr:
    """OCR through one long-lived reader process (RapidOCR, or Windows OCR as fallback), each word
    corrected against Photoshop's own labels (`corrector`; default: the local strings list, if
    extracted)."""

    def __init__(self, command: list[str] | None = None, corrector: Corrector | None = None) -> None:
        self.corrector = corrector or Corrector.from_file()
        self.process = subprocess.Popen(
            command or ocr_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.folder = Path(tempfile.mkdtemp(prefix="harness-ocr-"))

    def words(self, image: np.ndarray) -> list[dict[str, Any]]:
        """Words in `image` with boxes in its pixels."""
        if image.size == 0:
            return []
        prepared = prepare_for_ocr(image)
        self.reads = getattr(self, "reads", 0) + 1
        path = self.folder / f"read-{self.reads}.png"  # OCR may still hold the last one open
        Image.fromarray(prepared).save(path)
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(f"{path}\n")
        self.process.stdin.flush()
        answer = json.loads(self.process.stdout.readline())
        s = OCR_SCALE
        fix = self.corrector.word if self.corrector else str
        return [
            {**w, "text": fix(w["text"]), "x": w["x"] // s, "y": w["y"] // s, "w": w["w"] // s, "h": w["h"] // s}
            for w in answer["words"]
        ]

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.wait(timeout=10)


OCR_SCALE = 3  # scored on the 142 catalogued dialogs: RapidOCR 78.6% at 3x, 63.6% at 2x


def prepare_for_ocr(image: np.ndarray, scale: int = OCR_SCALE) -> np.ndarray:
    """Dark text on light, enlarged: what the OCR engines read best."""
    grey = np.asarray(Image.fromarray(image[..., :3]).convert("L"))
    if grey.mean() < 128:
        grey = 255 - grey
    size = (grey.shape[1] * scale, grey.shape[0] * scale)
    return np.asarray(Image.fromarray(grey).resize(size, Image.LANCZOS))


def to_screen(events: list[Event], origin: tuple[int, int]) -> list[Event]:
    """Mouse positions from dialog coordinates to screen coordinates; keys unchanged."""
    ox, oy = origin
    return [replace(e, x=e.x + ox, y=e.y + oy) if isinstance(e, MouseMove) else e for e in events]


READ_MARGIN = 6  # px of dialog read round a region: text cropped tight reads worse


class DialogSurface:
    """One dialog window of the Photoshop process `pid`."""

    flicker_s = 0.6  # two shots this far apart catch a blinking caret

    def __init__(self, hwnd: int, pid: int, ocr: Ocr | None = None, should_stop=lambda: False) -> None:
        self.hwnd, self.pid, self.ocr, self.should_stop = hwnd, pid, ocr, should_stop
        self.before = set(_visible_windows(pid))

    def _open(self) -> None:
        if not ctypes.windll.user32.IsWindow(self.hwnd):
            raise DialogClosed(f"dialog window {self.hwnd} is gone")

    def shot(self) -> np.ndarray:
        self._open()
        return np.asarray(capture.grab(self.hwnd).convert("RGB"))

    def send(self, events: list[Event]) -> None:
        self._open()
        left, top, _, _ = capture.frame_bounds(self.hwnd)
        # A list or menu the dialog opened stays in front: focusing the dialog would close it
        # and the Escape meant for it would cancel the dialog (Hue/Saturation, 2026-11-10).
        if not self._popup_windows():
            win_input.focus(self.hwnd, self.pid, settle_s=0.1, should_stop=self.should_stop)
        win_input.perform(to_screen(events, (left, top)), pid=self.pid, should_stop=self.should_stop)

    def _popup_windows(self) -> list[int]:
        return [
            h
            for h in _visible_windows(self.pid)
            if h not in self.before and h != self.hwnd and is_popup(_class_name(h))
        ]

    def popups(self) -> int:
        return len(self._popup_windows())

    def popup_classes(self) -> list[str]:
        """The window classes of what the dialog has open: what a stuck window was."""
        return [_class_name(h) for h in self._popup_windows()]

    def popup_lines(self) -> list[str]:
        """The lines of text OCR reads in what the dialog has open (a dropdown's list)."""
        if self.ocr is None:
            return []
        lines: list[str] = []
        for popup in self._popup_windows():
            words = self.ocr.words(np.asarray(capture.grab(popup).convert("RGB")))
            by_line: dict[int, list[str]] = {}
            for word in words:
                by_line.setdefault(word["line"], []).append(word["text"])
            lines += [" ".join(texts) for _, texts in sorted(by_line.items())]
        return lines

    def is_file_dialog(self) -> bool:
        """A Windows file dialog (Place Linked, Save a Copy...): it has the File name box."""
        return is_file_dialog(self.hwnd)

    def close_popups(self) -> None:
        """Close what the dialog opened without cancelling the dialog. Photoshop's lists do
        not take keyboard focus, so an Escape would reach the dialog: Escape goes to the
        popup only once it is in front; otherwise a click on the dialog's title bar (no
        control there) closes it. A window with real buttons (Liquify's face notice, which
        ignores Escape) is answered as Cancel: its Cancel, or OK on a notice, never "Don't show
        again"."""
        from . import photoshop

        user32 = ctypes.windll.user32
        windows = {d.hwnd: d for d in photoshop.list_dialogs(self.pid)}
        for popup in self._popup_windows():
            action, button = photoshop.cancel_action(windows[popup]) if popup in windows else ("", None)
            if action in ("click", "cancel_command", "button_command"):
                photoshop.answer(windows[popup], action, button)
                time.sleep(0.5)
                continue
            user32.SetForegroundWindow(popup)
            time.sleep(0.2)
            if user32.GetForegroundWindow() == popup:
                win_input.perform(chord("escape"), pid=self.pid, should_stop=self.should_stop)
            else:
                left, top, right, _ = capture.frame_bounds(self.hwnd)
                win_input.perform(click(((left + right) // 2, top + 12)), pid=self.pid, should_stop=self.should_stop)
            time.sleep(0.3)

    def words(self) -> list[dict[str, Any]]:
        """OCR of the whole dialog: words with boxes in dialog pixels."""
        return self.ocr.words(self.shot()) if self.ocr is not None else []

    def read_text(self, rect: Rect) -> str:
        if self.ocr is None:
            return ""
        image = self.shot()
        m = READ_MARGIN
        x0, y0, x1, y1 = rect
        crop = image[max(0, y0 - m) : y1 + m, max(0, x0 - m) : x1 + m]
        return " ".join(w["text"] for w in self.ocr.words(crop))


FILE_NAME_BOX = 1148  # cmb13: a Windows file dialog's File name box
_SAVE_NAME_BOX = 1001  # a Save dialog's File name box
WM_SETTEXT = 0x000C


@dataclass(frozen=True)
class EditBox:
    """An Edit somewhere inside a file dialog: its own control id and its parent's."""

    hwnd: int
    control_id: int
    parent_id: int
    visible: bool


def pick_file_name_box(edits: list[EditBox]) -> int:
    """The visible File name Edit: id 1001 (Save's, nested in a combo below the dialog's own
    children in Photoshop's Save As, 2026-11-24) or the Edit inside the cmb13 combo (Open's)."""
    for edit in edits:
        if edit.visible and (edit.control_id in (_SAVE_NAME_BOX, FILE_NAME_BOX) or edit.parent_id == FILE_NAME_BOX):
            return edit.hwnd
    return 0


def _file_name_box(hwnd: int) -> int:
    """The Edit a file dialog's File name is typed into, wherever it is nested."""
    user32 = ctypes.windll.user32
    edits: list[EditBox] = []

    def visit(child: int, _: int) -> bool:
        if _class_name(child) == "Edit":
            parent = user32.GetParent(child)
            edits.append(EditBox(child, user32.GetDlgCtrlID(child), user32.GetDlgCtrlID(parent),
                                 bool(user32.IsWindowVisible(child))))
        return True

    user32.EnumChildWindows(hwnd, win_input.WNDENUMPROC(visit), 0)
    return pick_file_name_box(edits)


def is_file_dialog(hwnd: int) -> bool:
    """A Windows file dialog (Place Linked, Save a Copy...): Open's File name box, or the shell
    view every Open and Save dialog hosts."""
    return bool(ctypes.windll.user32.GetDlgItem(hwnd, FILE_NAME_BOX) or _descendant(hwnd, "DUIViewWndClassName"))


def answer_file_dialog(hwnd: int, path: Path) -> bool:
    """Answer a Windows file dialog with `path`: the full path put in its File name box and its
    own OK (Open, Place, Save) pressed by message, with no keys and no foreground taken. True
    once the dialog has closed."""
    user32 = ctypes.windll.user32
    if not (box := _file_name_box(hwnd)):
        return False
    user32.SendMessageW(box, WM_SETTEXT, 0, ctypes.c_wchar_p(str(path)))
    user32.PostMessageW(hwnd, 0x0111, 1, 0)  # WM_COMMAND IDOK
    for _ in range(30):
        time.sleep(0.1)
        if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
            return True
    return False


def _window_text(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(1024)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, 1024)
    return buffer.value


def _descendant(parent: int, class_name: str) -> int:
    """The first window of `class_name` inside `parent` (0 if none)."""
    found: list[int] = []

    def visit(hwnd: int, _: int) -> bool:
        if _class_name(hwnd) == class_name:
            found.append(hwnd)
            return False
        return True

    if parent:
        ctypes.windll.user32.EnumChildWindows(parent, win_input.WNDENUMPROC(visit), 0)
    return found[0] if found else 0


# Windows that appear beside a dialog without being anything it opened.
_NOT_POPUPS = frozenset({"tooltips_class32", "SysShadow", "PSDragFeedback"})  # PSDragFeedback: Photoshop's drag overlay (Image Size, 2026-11-11)


def is_popup(class_name: str) -> bool:
    """Whether a new window of this class is something the dialog opened (a list, a menu, a
    colour picker): tooltips and drop shadows are not."""
    return class_name not in _NOT_POPUPS


def _class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(128)
    ctypes.windll.user32.GetClassNameW(hwnd, buffer, 128)
    return buffer.value


def _visible_windows(pid: int) -> list[int]:
    user32 = ctypes.windll.user32
    found: list[int] = []

    def visit(hwnd: int, _: int) -> bool:
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(win_input.WNDENUMPROC(visit), 0)
    return found
