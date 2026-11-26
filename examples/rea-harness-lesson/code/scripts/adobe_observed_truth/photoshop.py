"""Running Photoshop over COM: identity, allowlisted state reads, throwaway documents, modals.

Reads name exact descriptor keys only. The application descriptor also carries the
licence serial, so it is never dumped wholesale.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import platform
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from .win_input import WNDENUMPROC

THROWAWAY_PREFIX = "observed-truth-"

# ExtendScript is ES3: no JSON object. q() quotes a string for the JSON we return.
_PRELUDE = r"""
function q(s){return '"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"')+'"';}
function appRef(){var r=new ActionReference();
 r.putEnumerated(charIDToTypeID("capp"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));return r;}
function appProperty(name){var r=new ActionReference();
 r.putProperty(stringIDToTypeID("property"),stringIDToTypeID(name));
 r.putEnumerated(charIDToTypeID("capp"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));
 return executeActionGet(r).getObjectValue(stringIDToTypeID(name));}
function historyJson(doc){var hs=doc.historyStates,items=[],active=-1;
 for(var i=0;i<hs.length;i++){items.push('{"name":'+q(hs[i].name)+',"snapshot":'+hs[i].snapshot+'}');
  if(hs[i]==doc.activeHistoryState)active=i;}
 return '{"states":['+items.join(',')+'],"active_index":'+active+'}';}
"""


@dataclass(frozen=True)
class Identity:
    version: str
    build: str
    executable_path: str
    executable_sha256: str
    pid: int
    hwnd: int


class Photoshop:
    def __init__(self, major_version: str = "27") -> None:
        import win32com.client

        # The ProgID binds to whichever installed version registered last.
        self.app = win32com.client.GetActiveObject("Photoshop.Application")
        version = str(self.app.Version)
        if version.split(".")[0] != major_version:
            raise RuntimeError(
                f"Bound Photoshop {version}, expected major version {major_version}."
            )

    def js(self, body: str) -> Any:
        return json.loads(self.app.DoJavaScript(_PRELUDE + body))

    def identity(self) -> Identity:
        facts = self.js(
            "var d=executeActionGet(appRef());"
            '"{\\"build\\":"+q(d.getString(stringIDToTypeID("buildNumber")))'
            '+",\\"path\\":"+q(d.getPath(stringIDToTypeID("executablePath")).fsName)+"}";'
        )
        # executablePath names the install folder on Windows.
        path = str(Path(facts["path"]) / "Photoshop.exe")
        pid, hwnd = _main_window(path)
        return Identity(
            version=str(self.app.Version),
            build=facts["build"],
            executable_path=path,
            executable_sha256=sha256_file(Path(path)),
            pid=pid,
            hwnd=hwnd,
        )

    def history_preferences(self) -> dict[str, Any]:
        return self.js(
            'var h=appProperty("historyPreferences");'
            '"{\\"maximumStates\\":"+h.getInteger(stringIDToTypeID("maximumStates"))'
            '+",\\"snapshotInitial\\":"+h.getBoolean(stringIDToTypeID("snapshotInitial"))'
            '+",\\"nonLinear\\":"+h.getBoolean(stringIDToTypeID("nonLinear"))+"}";'
        )

    def new_document(self, name: str, width_px: int = 64, height_px: int = 64) -> None:
        self.js(
            f'app.documents.add(UnitValue({width_px},"px"),UnitValue({height_px},"px"),72,'
            f'{json.dumps(THROWAWAY_PREFIX + name)},NewDocumentMode.RGB,DocumentFill.WHITE);"null";'
        )

    def select_all_and_fill(self, times: int) -> dict[str, Any]:
        """Select All, then `times` Fill operations, each one history state; returns the history."""
        return self.js(
            "var doc=app.activeDocument;doc.selection.selectAll();"
            f"for(var i=0;i<{times};i++){{var c=new SolidColor();c.rgb.red=i%256;"
            "c.rgb.green=0;c.rgb.blue=0;doc.selection.fill(c);}"
            "historyJson(doc);"
        )

    def menu_items(self, commands: list[int]) -> list[dict[str, Any]]:
        """Menu items with these command IDs, in menu order, with current name and state.

        Names are dynamic ("Undo" becomes "Undo Fill"), so items are matched by command ID.
        menuBarInfo carries no usable key bindings: every menuShortcut reads as no key.
        """
        return self.js(
            f"var wanted={json.dumps(commands)},found=[];"
            'var r=new ActionReference();r.putProperty(stringIDToTypeID("property"),stringIDToTypeID("menuBarInfo"));'
            'r.putEnumerated(charIDToTypeID("capp"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));'
            "function has(c){for(var i=0;i<wanted.length;i++)if(wanted[i]==c)return true;return false;}"
            "function walk(d){var k=stringIDToTypeID;"
            ' if(d.hasKey(k("command"))&&has(d.getInteger(k("command"))))'
            """  found.push('{"name":'+q(d.getString(k("name")))+',"title":'+q(d.getString(k("title")))"""
            """+',"command":'+d.getInteger(k("command"))"""
            """+',"visible":'+d.getBoolean(k("visible"))+',"enabled":'+d.getBoolean(k("enabled"))"""
            """+',"checked":'+d.getBoolean(k("checked"))+"}");"""
            ' if(d.hasKey(k("submenu"))){var l=d.getList(k("submenu"));'
            "  for(var i=0;i<l.count;i++)walk(l.getObjectValue(i));}}"
            'walk(executeActionGet(r).getObjectValue(stringIDToTypeID("menuBarInfo")));'
            '"["+found.join(",")+"]";'
        )

    def current_tool(self) -> str:
        return self.js(
            'q(typeIDToStringID(executeActionGet(appRef()).getEnumerationType(stringIDToTypeID("tool"))));'
        )

    def select_tool(self, tool: str) -> None:
        self.js(
            "var r=new ActionReference();"
            f"r.putClass(stringIDToTypeID({json.dumps(tool)}));"
            'var d=new ActionDescriptor();d.putReference(charIDToTypeID("null"),r);'
            'executeAction(charIDToTypeID("slct"),d,DialogModes.NO);"null";'
        )

    def selection_bounds(self) -> list[int] | None:
        """Active document selection as [left, top, right, bottom] pixels, or None."""
        return self.js(
            "var doc=app.activeDocument,b;"
            "try{b=doc.selection.bounds;}catch(e){b=null;}"
            'b?"["+[b[0].as("px"),b[1].as("px"),b[2].as("px"),b[3].as("px")].join(",")+"]":"null";'
        )

    def layer_bounds(self) -> list[int]:
        return self.js(
            "var b=app.activeDocument.activeLayer.bounds;"
            '"["+[b[0].as("px"),b[1].as("px"),b[2].as("px"),b[3].as("px")].join(",")+"]";'
        )

    def path_anchors(self) -> list[list[list[int]]]:
        """Anchor [x, y] pixels of every subpath of every path item in the active document."""
        return self.js(
            "var doc=app.activeDocument,out=[];"
            "for(var p=0;p<doc.pathItems.length;p++){var item=doc.pathItems[p];"
            " for(var s=0;s<item.subPathItems.length;s++){var pts=item.subPathItems[s].pathPoints,a=[];"
            "  for(var i=0;i<pts.length;i++)a.push('['+Math.round(pts[i].anchor[0])+','+Math.round(pts[i].anchor[1])+']');"
            "  out.push('['+a.join(',')+']');}}"
            '"["+out.join(",")+"]";'
        )

    def legacy_free_transform(self) -> bool:
        return self.js(
            'appProperty("generalPreferences").getBoolean(stringIDToTypeID("legacyFreeTransform"));'
        )

    def bring_to_front(self) -> None:
        self.js('app.bringToFront();"null";')

    def history(self) -> dict[str, Any]:
        return self.js("historyJson(app.activeDocument);")

    def close_throwaway_document(self) -> None:
        # Refuse to close anything this harness did not open.
        self.js(
            f"var doc=app.activeDocument;if(doc.name.indexOf({json.dumps(THROWAWAY_PREFIX)})!==0)"
            '{throw new Error("active document is not a harness document");}'
            'doc.close(SaveOptions.DONOTSAVECHANGES);"null";'
        )

    def open_documents(self) -> list[dict[str, Any]]:
        """Every open document's id and name (names stay local: they can be private)."""
        return self.js(
            "var out=[];for(var i=0;i<app.documents.length;i++){var d=app.documents[i];"
            """out.push('{"id":'+d.id+',"name":'+q(d.name)+'}');}"["+out.join(",")+"]";"""
        )

    def save_throwaway_to_sandbox(self, folder: Path) -> Path:
        """Give the active harness document a home in the sandbox, so file commands land there."""
        folder.mkdir(parents=True, exist_ok=True)
        name = self.js("q(app.activeDocument.name);")
        if not name.startswith(THROWAWAY_PREFIX):
            raise RuntimeError("active document is not a harness document")
        target = folder / f"{name}.psd"
        self.js(
            f"app.activeDocument.saveAs(new File({json.dumps(target.as_posix())}),"
            'new PhotoshopSaveOptions(),false,Extension.LOWERCASE);"null";'
        )
        return target

    def close_new_documents(self, before: list[int]) -> int:
        """Close, unsaved, every document opened since `before` was taken; return how many."""
        return self.js(
            f"var keep={json.dumps(before)},n=0;"
            "function kept(id){for(var j=0;j<keep.length;j++)if(keep[j]==id)return true;return false;}"
            "for(var i=app.documents.length-1;i>=0;i--){var d=app.documents[i];"
            "if(!kept(d.id)){d.close(SaveOptions.DONOTSAVECHANGES);n++;}}String(n);"
        )

    def run_menu_command(self, command: int) -> None:
        self.js(f'app.runMenuItem({int(command)});"null";')


@contextmanager
def exclusive(app: str = "photoshop", timeout_s: float = 900) -> Iterator[None]:
    """Hold one Adobe app for one scenario across processes; scripts act on the active document."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    mutex = kernel32.CreateMutexW(None, False, rf"Local\adobe-observed-truth-{app}")
    result = kernel32.WaitForSingleObject(mutex, int(timeout_s * 1000))
    if result not in (0, 0x80):  # WAIT_OBJECT_0, WAIT_ABANDONED
        kernel32.CloseHandle(mutex)
        raise TimeoutError(f"Another harness process still holds {app}.")
    try:
        yield
    finally:
        kernel32.ReleaseMutex(mutex)
        kernel32.CloseHandle(mutex)


@contextmanager
def dialogs_off(ps: Photoshop) -> Iterator[None]:
    """Make refused commands raise instead of opening a modal that blocks Photoshop."""
    previous = ps.js("var p=app.displayDialogs;app.displayDialogs=DialogModes.NO;q(String(p));")
    if previous not in ("DialogModes.NO", "DialogModes.ERROR", "DialogModes.ALL"):
        raise RuntimeError(f"Unexpected displayDialogs value {previous!r}")

    def restore() -> None:
        ps.js(f'app.displayDialogs={previous};"null";')

    try:
        yield
    except BaseException as failure:
        # Photoshop refuses the restore while a modal is open; the scenario's error matters more.
        try:
            restore()
        except Exception as restore_failure:  # noqa: BLE001 - any refusal; the original wins
            failure.add_note(f"displayDialogs was not restored to {previous}: {restore_failure}")
        raise
    restore()


PHOTOSHOP_DIALOG, STANDARD_DIALOG, FLOATING_DIALOG = "PSDialogBox", "#32770", "PSFloatC"
# Full-window filter dialogs (Adaptive Wide Angle, Filter Gallery...): modal, real buttons.
FILTER_DIALOG = "PSFilter_WindowClass"
MAIN_WINDOW = "Photoshop"


@dataclass(frozen=True)
class Control:
    hwnd: int
    class_name: str
    text: str
    checked: bool | None  # None unless the control is a check box or radio button
    enabled: bool = True  # a greyed-out button does nothing when pressed (Vanishing Point's OK)


@dataclass(frozen=True)
class Dialog:
    hwnd: int
    class_name: str
    controls: tuple[Control, ...]

    @property
    def text(self) -> str:
        return " | ".join(control.text for control in self.controls if control.text)


# Adobe's feedback survey, recognised by the SHA-256 of its question's exact text (as shown in
# Photoshop 2026, 2026-11-09), so the wording itself is never published.
SURVEY_SHA256 = "62fbb77fee17b851217bb0c4ca69a7285542620a94255f6a3c8f954a4542803f"


def _is_survey(dialog: Dialog) -> bool:
    return any(hashlib.sha256(control.text.encode()).hexdigest() == SURVEY_SHA256 for control in dialog.controls)


# Windows buttons, or the controls Photoshop draws itself in its modern dialogs (Duplicate,
# New Layer...): their OK and Cancel are not Windows buttons and cannot be clicked by message.
_DIALOG_CONTROLS = frozenset({"Button", "DroverLord - Window Class"})


def blocking(dialogs: list[Dialog]) -> list[Dialog]:
    """Dialogs that hold Photoshop modal: its own boxes, Adobe's survey, or dialogs with buttons.

    Adobe's feedback survey is a standard #32770 dialog; while it is open every scripted
    command fails as "not currently available". It blocks however its controls are drawn.
    Button-less #32770 popups such as the Generative Fill feature tour do not block.
    """
    return [
        dialog
        for dialog in dialogs
        if dialog.class_name in (PHOTOSHOP_DIALOG, FILTER_DIALOG)
        or _has_real_cancel(dialog)  # any window class: a Cancel button means modal
        or _is_input_dialog(dialog)  # self-drawn buttons, real fields (Picture Frame)
        or (
            # A visible floating window holds Photoshop modal even with no buttons (About).
            dialog.class_name == FLOATING_DIALOG
            or dialog.class_name == STANDARD_DIALOG
            and (
                _is_survey(dialog)
                or any(control.class_name in _DIALOG_CONTROLS for control in dialog.controls)
            )
        )
    ]


def _has_real_cancel(dialog: Dialog) -> bool:
    return any(
        control.class_name == "Button" and control.text.replace("&", "") == "Cancel"
        for control in dialog.controls
    )


def _is_input_dialog(dialog: Dialog) -> bool:
    """A window of its own class with real input fields; panel docks (OWL.*) hold fields too."""
    return not dialog.class_name.startswith("OWL.") and any(
        control.class_name == "Edit" for control in dialog.controls
    )


class Dismissal(NamedTuple):
    declined: list[Dialog]
    remaining: list[Dialog]  # still blocking: not a survey, or one it cannot safely click


def dismiss_surveys(dialogs: list[Dialog], click: Callable[[Control], None]) -> Dismissal:
    """Decline Adobe's feedback survey for good (the operator, 2026-11-09).

    Ticks "Never show again" and presses Cancel, only when they are standard buttons: a
    click message to anything else may do nothing. Submit is never pressed: it would send
    feedback tied to the Adobe ID.
    """
    declined, remaining = [], []
    for dialog in blocking(dialogs):
        controls = {control.text: control for control in dialog.controls}
        cancel = controls.get("Cancel")
        if not _is_survey(dialog) or cancel is None or cancel.class_name != "Button":
            remaining.append(dialog)
            continue
        never = controls.get("Never show again")
        # Unknown state: a click could untick it.
        if never is not None and never.class_name == "Button" and never.checked is False:
            click(never)
        click(cancel)
        declined.append(dialog)
    return Dismissal(declined, remaining)


def blocking_dialogs(pid: int) -> list[str]:
    """Text of each visible dialog holding the Photoshop process modal."""
    return [dialog.text for dialog in blocking(list_dialogs(pid))]


BM_GETCHECK, BM_CLICK, GWL_STYLE, BS_TYPEMASK = 0x00F0, 0x00F5, -16, 0xF
# BS_CHECKBOX, BS_AUTOCHECKBOX, BS_RADIOBUTTON, BS_3STATE, BS_AUTO3STATE, BS_AUTORADIOBUTTON
_CHECKABLE_STYLES = {2, 3, 4, 5, 6, 9}


def class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _text(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, 512)
    return buffer.value


def main_window_pids() -> list[int]:
    """Processes with a Photoshop main window, found without scripting (refused behind a modal)."""
    user32 = ctypes.windll.user32
    pids: list[int] = []

    def visit(hwnd: int, _: int) -> bool:
        # The main window's class, not its title: titles can name private files.
        if user32.IsWindowVisible(hwnd) and class_name(hwnd) == MAIN_WINDOW:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pids.append(pid.value)
        return True

    user32.EnumWindows(WNDENUMPROC(visit), 0)
    return sorted(set(pids))


def _check_state(hwnd: int) -> bool | None:
    """A checkbox's state, or None if its window does not answer within half a second
    (a plain SendMessage to a hung Photoshop never returns)."""
    result = ctypes.c_size_t()
    answered = ctypes.windll.user32.SendMessageTimeoutW(
        hwnd, BM_GETCHECK, 0, 0, 0x0002 | 0x0001, 500, ctypes.byref(result)  # ABORTIFHUNG|BLOCK
    )
    return bool(result.value) if answered else None


def list_dialogs(pid: int) -> list[Dialog]:
    """Every visible top-level window of the process except its main window, with visible
    controls; `blocking` decides which are dialogs (new classes keep appearing: Radial Blur)."""
    user32 = ctypes.windll.user32
    dialogs: list[Dialog] = []

    def control(hwnd: int) -> Control:
        kind = class_name(hwnd)
        style = user32.GetWindowLongW(hwnd, GWL_STYLE) & BS_TYPEMASK
        checkable = kind == "Button" and style in _CHECKABLE_STYLES
        checked = _check_state(hwnd) if checkable else None
        return Control(
            hwnd=hwnd,
            class_name=kind,
            text=_text(hwnd),
            checked=checked,
            enabled=bool(user32.IsWindowEnabled(hwnd)),
        )

    def visit(hwnd: int, _: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        kind = class_name(hwnd)
        if owner.value == pid and kind != MAIN_WINDOW and user32.IsWindowVisible(hwnd):
            children: list[int] = []

            def collect(child: int, _: int) -> bool:
                # Hidden controls must not make a passive popup look like a modal dialog.
                if user32.IsWindowVisible(child):
                    children.append(child)
                return True

            user32.EnumChildWindows(hwnd, WNDENUMPROC(collect), 0)
            dialogs.append(Dialog(hwnd, kind, tuple(control(child) for child in children)))
        return True

    user32.EnumWindows(WNDENUMPROC(visit), 0)
    return dialogs


def cancel_action(dialog: Dialog) -> tuple[str, Control | None]:
    """How to dismiss `dialog` as Cancel: press its real Cancel button if it has one.

    WM_CLOSE on a floating dialog (Image Size, PSFloatC) destroyed the window but left
    Photoshop's scripting stuck in its modal state (2026-11-09); a real button ends it.
    Self-drawn dialogs (Duplicate) have no such button and do cancel on WM_CLOSE.
    """
    for control in dialog.controls:
        if control.class_name == "Button" and control.text.replace("&", "") == "Cancel":
            if dialog.class_name == STANDARD_DIALOG:
                # Windows' own dialogs (Save As): a posted click on an inactive dialog can be
                # ignored, which hung Paths to Illustrator for 90 s; IDCANCEL is not.
                return "cancel_command", None
            return "click", control
    # No Cancel: a notice (Pattern Preview) that ignores WM_CLOSE; OK only acknowledges it.
    # A Yes/No box ignores WM_CLOSE too (Confirm Save As held Paths to Illustrator 90 s,
    # 2026-11-24); No leaves things as they were.
    # Never "More Info..." (a browser) or "Don't show again" (a preference).
    for wanted in ("OK", "No"):
        for control in dialog.controls:
            if control.class_name == "Button" and control.text.replace("&", "") == wanted:
                # A Windows message box (a range alert) can ignore a posted click while inactive.
                return ("button_command" if dialog.class_name == STANDARD_DIALOG else "click"), control
    if dialog.class_name not in (PHOTOSHOP_DIALOG, STANDARD_DIALOG):
        # About (PSFloatC), Picture Frame (CScriptPs): no real buttons, and WM_CLOSE is
        # ignored or strands the modal state; Escape sent to the dialog itself closes it.
        return "escape", None
    return "close", None


def accept_action(dialog: Dialog, *, never_press: tuple[str, ...]) -> tuple[str, Control | None]:
    """How to accept `dialog` with its default settings, so a command's effect can be seen:
    press its real OK button. A dialog offering any `never_press` button (Generate, Share...)
    is cancelled instead, as is one without a real OK."""
    texts = [control.text.replace("&", "") for control in dialog.controls]
    if any(word.lower() in text.lower() for text in texts for word in never_press):
        return cancel_action(dialog)
    for control, text in zip(dialog.controls, texts, strict=True):
        if control.class_name == "Button" and text == "OK" and control.enabled:
            return "click", control
    if any(control.class_name == "DroverLord - Window Class" for control in dialog.controls):
        return "enter", None  # self-drawn OK (Hue/Saturation, Levels): Enter is OK
    return cancel_action(dialog)


WM_CLOSE, WM_COMMAND, IDOK, IDCANCEL = 0x0010, 0x0111, 1, 2


def cancel(dialog: Dialog) -> None:
    answer(dialog, *cancel_action(dialog))


def answer(dialog: Dialog, action: str, control: Control | None) -> None:
    """Carry out a dismissal decided by `cancel_action` or `accept_action`."""
    if action == "click" and control is not None:
        click(control)
    elif action in ("cancel_command", "button_command"):
        command = IDCANCEL
        if action == "button_command":
            # The button's own command: a message box with only OK gives it 2, not IDOK
            # (Filter Gallery's range alert ignored IDOK for 16 minutes, 2026-11-24).
            command = ctypes.windll.user32.GetDlgCtrlID(control.hwnd) if control else IDOK
        if not ctypes.windll.user32.PostMessageW(dialog.hwnd, WM_COMMAND, command, 0):
            raise ctypes.WinError()
    elif action in ("escape", "enter"):
        from . import win_input
        from .input_plan import chord

        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(dialog.hwnd, ctypes.byref(pid))
        # focus, not a bare SetForegroundWindow: Windows refuses that from the background (File
        # Info's Enter, the Claude app in front, 2026-11-24).
        win_input.focus(dialog.hwnd, pid.value, settle_s=0.2)
        win_input.perform(chord(action), pid=pid.value)
    elif not ctypes.windll.user32.PostMessageW(dialog.hwnd, WM_CLOSE, 0, 0):
        raise ctypes.WinError()


def click(control: Control) -> None:
    """Press a dialog control by message: no simulated input, so the pointer is never moved."""
    if not ctypes.windll.user32.PostMessageW(control.hwnd, BM_CLICK, 0, 0):
        raise ctypes.WinError()


def environment() -> dict[str, str]:
    return {
        "id": f"windows-{platform.version()}",
        "platform": "win32",
        "architecture": "x86_64",
        "isolation": "none",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _main_window(executable_path: str) -> tuple[int, int]:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    found: list[tuple[int, int]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        # By window class, not title: with a document open the title is the document's name.
        if user32.IsWindowVisible(hwnd) and class_name(hwnd) == MAIN_WINDOW:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
            image = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            kernel32.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size))
            kernel32.CloseHandle(handle)
            if image.value.lower() == executable_path.lower():
                found.append((pid.value, hwnd))
        return True

    user32.EnumWindows(visit, 0)
    if len(found) != 1:
        raise RuntimeError(
            f"Expected one Photoshop main window for {executable_path}, found {found}"
        )
    return found[0]
