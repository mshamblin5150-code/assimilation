"""Observed behaviours. Each scenario drives Photoshop and returns observation_record arguments."""

from __future__ import annotations

import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable

from . import win_input
from .input_plan import chord
from .capture import capture_window
from .photoshop import Identity, Photoshop


Scenario = Callable[[Photoshop, Identity, Path], dict[str, Any]]


@dataclass(frozen=True)
class Spec:
    run: Scenario
    needs_input: bool  # keyboard or mouse input: impossible while the workstation is locked


def history_depth(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    preferences = ps.history_preferences()
    fills = preferences["maximumStates"] + 10
    ps.new_document("history-depth")
    try:
        history = ps.select_all_and_fill(fills)
    finally:
        ps.close_throwaway_document()
    retained = [state for state in history["states"] if not state["snapshot"]]
    return {
        "operation": "observe_history_depth",
        "parameters": {
            "behaviour_id": "history_default_depth",
            "operations": {"select_all": 1, "fill": fills},
        },
        "observed": {
            "history_preferences": preferences,
            "history_states_retained": len(retained),
            "snapshots_retained": len(history["states"]) - len(retained),
            "oldest_retained_state": retained[0]["name"],
            "newest_retained_state": retained[-1]["name"],
        },
        "limitations": [
            "Effective limit under this user's current preferences; the factory default is not observed.",
            "History operations were issued by script, not by UI input.",
        ],
    }


def redo_shortcuts(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    steps = [("ctrl+z", "undo-1"), ("ctrl+z", "undo-2"), ("ctrl+y", "ctrl-y"), ("shift+ctrl+z", "shift-ctrl-z")]
    ps.new_document("redo-shortcuts")
    observed_steps = []
    artifacts = []
    try:
        start = ps.select_all_and_fill(3)
        ps.bring_to_front()
        win_input.focus(identity.hwnd, identity.pid)
        for shortcut, label in steps:
            win_input.perform(chord(shortcut), pid=identity.pid)
            time.sleep(0.6)
            history = ps.history()
            capture = Path("captures") / f"redo-shortcuts-{label}.png"
            sha256 = capture_window(identity.hwnd, out_dir / capture)
            artifacts.append(capture.as_posix())
            active = history["states"][history["active_index"]]
            observed_steps.append(
                {
                    "shortcut": shortcut,
                    "active_index": history["active_index"],
                    "active_state": active["name"],
                    "proof_colors_checked": ps.menu_items([PROOF_COLORS_COMMAND])[0]["checked"],
                    "capture": {"path": capture.as_posix(), "sha256": sha256},
                }
            )
    finally:
        ps.close_throwaway_document()
    return {
        "operation": "observe_redo_shortcuts",
        "parameters": {
            "behaviour_id": "undo_redo_shortcut_mapping",
            "shortcuts": [shortcut for shortcut, _ in steps],
        },
        "observed": {
            "start_active_index": start["active_index"],
            "start_states": [state["name"] for state in start["states"]],
            "steps": observed_steps,
        },
        "limitations": [
            "The 'Use Legacy Undo Shortcuts' setting is not readable by scripting; "
            "its effect is visible only in the Ctrl+Z steps.",
            "Captures show the whole Photoshop window; view-only effects such as Proof Colors "
            "are visible only there.",
        ],
        "artifact_paths": sorted(artifacts),
    }


# Edit and View menu command IDs read from menuBarInfo on Photoshop 27.11: Undo, Redo,
# Toggle Last State, Step Backward, Step Forward, Proof Colors.
PROOF_COLORS_COMMAND = 1105
UNDO_MENU_COMMANDS = [101, 132, 133, 1961, 1962, PROOF_COLORS_COMMAND]


def undo_menu_layout(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    before = ps.menu_items(UNDO_MENU_COMMANDS)
    ps.new_document("undo-menu-layout")
    try:
        ps.select_all_and_fill(2)
        after_edit = ps.menu_items(UNDO_MENU_COMMANDS)
        stepped = ps.js(
            "var doc=app.activeDocument,hs=doc.historyStates;"
            "doc.activeHistoryState=hs[hs.length-2];historyJson(doc);"
        )
        after_step_back = ps.menu_items(UNDO_MENU_COMMANDS)
    finally:
        ps.close_throwaway_document()
    return {
        "operation": "observe_undo_menu_layout",
        "parameters": {
            "behaviour_id": "undo_redo_shortcut_mapping",
            "menu_commands": UNDO_MENU_COMMANDS,
            "steps": ["no_document", "after_select_all_and_two_fills", "after_one_step_back"],
        },
        "observed": {
            "no_document": before,
            "after_edit": after_edit,
            "after_step_back": after_step_back,
            "active_state_after_step_back": stepped["states"][stepped["active_index"]]["name"],
        },
        "limitations": [
            "Which undo mode is active is inferred from the menu layout (Toggle Last State "
            "visible vs Step Forward/Backward visible); no key was pressed.",
            "menuBarInfo reports no key bindings, so this does not show what Ctrl+Y does.",
            "The step back was made by setting the active history state by script.",
        ],
    }


SCENARIOS: dict[str, Spec] = {
    "history_depth": Spec(history_depth, needs_input=False),
    "undo_menu_layout": Spec(undo_menu_layout, needs_input=False),
    "redo_shortcuts": Spec(redo_shortcuts, needs_input=True),
}
