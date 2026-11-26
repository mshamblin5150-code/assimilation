"""Draft one probe scenario per inventory item, as data: what to do, what to record, how to undo.

Specs are not run here. Each says whether it is safe to run unattended. Nothing is excluded for
good except signing out: commands that would touch the user's files or open documents, saved
presets or workspaces wait for a sandboxed family (`needs_sandbox`), cloud and generative AI
features wait for a credit budget from the user (`needs_budget`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .claim_map import CLOUD
from .inventory import Item, load_inventory

Step = tuple[object, ...]
Safety = Literal[
    "run", "observed", "needs_sandbox", "needs_budget", "never", "covered_by_items", "no_family_yet"
]


@dataclass(frozen=True)
class ScenarioSpec:
    item_id: str
    family: str
    safety: Safety
    needs_input: bool = False
    steps: tuple[Step, ...] = ()
    reason: str | None = None
    never_press: tuple[str, ...] = ()  # buttons the runner must refuse to press


_NEVER = (
    (re.compile(r"\bSign Out\b", re.IGNORECASE), "signs out of Creative Cloud"),
    # Running these at all sends content to Adobe: "discover only" cannot open them safely
    # (Send to Firefly Boards started uploading on 2026-11-09 before it could be cancelled).
    (
        re.compile(r"\b(Send to(?! Back\b)|Share|Publish|Upload)\b", re.IGNORECASE),
        "sends content to Adobe",
    ),
)
_SANDBOX_PATHS = (
    # First: Bridge sits in the File menu but its side effect is another program (Creative Cloud).
    (re.compile(r"\bBridge\b"), "opens another program"),
    (re.compile(r"^File > (?!New$)"), "touches files or quits"),
    (re.compile(r"> Presets > .*(Export|Import|Migrate)"), "touches files or quits"),
    (re.compile(r"^(Help|Plugins)( > |$)"), "opens a browser or account page"),
    (re.compile(r"^Edit > Remote Connections"), "opens a network service"),
    (re.compile(r"^Window > Workspace > "), "changes saved workspaces"),
    (re.compile(r"^Edit > Define "), "changes saved presets"),
    (re.compile(r"^Edit > Purge\b|^Window > Arrange\b"), "affects the user's open documents"),
    (re.compile(r"^Image > Duplicate"), "opens a document the harness does not own"),
)
# Commands reached by shortcut are judged by name, since a shortcut file names no menu path.
_SANDBOX_COMMANDS = (
    (re.compile(r"\bBridge\b"), "opens another program"),
    (
        re.compile(
            r"^(save|open|close|exit|quit|print|export|place|revert|browse)\b", re.IGNORECASE
        ),
        "touches files or quits",
    ),
    (re.compile(r"^define\b", re.IGNORECASE), "changes saved presets"),
    (re.compile(r"^purge\b", re.IGNORECASE), "affects the user's open documents"),
)
# The test chart, not a blank page: on a blank document Photoshop takes its nothing-to-do
# branches (empty histograms, nothing to analyse), and a sampled sweep would miss the code that
# does the work. The chart is drawn by code and opened as harness scratch work.
_SCRATCH_RUN: tuple[Step, ...] = (("open_test_image", "chart"),)
_SCRATCH_END: tuple[Step, ...] = (
    ("record", "dialogs", "history", "document"),
    ("cancel_dialogs",),
    ("close_throwaway_document",),
)


def scenarios_for(item: Item, *, sandbox: bool = False) -> ScenarioSpec:
    """The probe for item; with sandbox, held-back commands get guarded steps instead."""
    if item.kind == "preference":
        return ScenarioSpec(
            item.id,
            "preference_default",
            "observed",
            reason="factory value read from the inventory",
        )
    if item.kind == "submenu":
        return ScenarioSpec(
            item.id, "submenu", "covered_by_items", reason="a container of commands"
        )
    if item.kind == "panel":
        if CLOUD.search(item.name) or "Invite to Edit" in item.name:  # Share for Review...
            return ScenarioSpec(
                item.id, "panel_open", "needs_budget", reason="cloud or generative AI service"
            )
        # Panel flyout menus are not reachable yet: Photoshop exposes no UI Automation tree.
        panel_steps: tuple[Step, ...] = (
            ("snapshot_panels",),
            ("show_panel", item.id.removeprefix("panel:")),
            ("record", "panels"),
            ("restore_panels",),
        )
        return ScenarioSpec(item.id, "panel_open", "run", False, panel_steps)
    if item.kind == "tool":
        shortcut = item.facts.get("shortcut")
        select: Step = (
            ("press", shortcut) if shortcut else ("select_tool_by_script", item.facts["tool_id"])
        )
        steps = (*_SCRATCH_RUN, select, ("record", "current_tool"), ("close_throwaway_document",))
        return ScenarioSpec(item.id, "tool_shortcut", "run", bool(shortcut), steps)
    if item.kind == "shortcut":
        press: Step = ("press", item.facts["keys"])
        if held := _held_back(str(item.facts["command"]), _SANDBOX_COMMANDS):
            if sandbox and held[0] == "needs_budget":
                return _cloud_discovery(item.id, press, True)
            if sandbox and held[0] == "needs_sandbox":
                return ScenarioSpec(
                    item.id,
                    "shortcut_sandboxed",
                    "run",
                    True,
                    _guarded(press, held[1], str(item.facts["command"])),
                    held[1],
                )
            return ScenarioSpec(item.id, "shortcut", held[0], True, reason=held[1])
        return ScenarioSpec(item.id, "shortcut", "run", True, (*_SCRATCH_RUN, press, *_SCRATCH_END))
    if item.kind == "menu_command":
        run: Step = ("run_menu_command", item.facts["command"])
        if held := _held_back(item.path, _SANDBOX_PATHS):
            if sandbox and held[0] == "needs_budget":
                return _cloud_discovery(item.id, run, False)
            if sandbox and held[0] == "needs_sandbox":
                return ScenarioSpec(
                    item.id,
                    "menu_command_sandboxed",
                    "run",
                    False,
                    _guarded(run, held[1], item.path),
                    held[1],
                )
            return ScenarioSpec(item.id, "menu_command", held[0], reason=held[1])
        # View commands are mostly persisted toggles (Rulers, Extras, Snap): run again to restore.
        again: tuple[Step, ...] = (
            (("toggle_back", item.facts["command"]),) if item.path.startswith("View > ") else ()
        )
        return ScenarioSpec(
            item.id,
            "menu_command",
            "run",
            False,
            (*_SCRATCH_RUN, run, *_SCRATCH_END[:1], *again, *_SCRATCH_END[1:]),
        )
    return ScenarioSpec(
        item.id, item.kind, "no_family_yet", reason=f"no scenario family for {item.kind} yet"
    )


_IMAGE_EFFECTS = re.compile(r"^(Filter|Image > Adjustments) > ")
# Some Neural Filters process the image on Adobe's servers: not with OK pressed for us.
_NO_IMAGE_PROBE = re.compile(r"\bNeural Filters\b")
TEST_IMAGES = ("chart", "icon")


def image_scenario(item: Item, image: str) -> ScenarioSpec | None:
    """A filter or adjustment run on a test image with its default settings accepted, so its
    effect shows in the pixels; None for every other item."""
    if item.kind != "menu_command" or not _IMAGE_EFFECTS.match(item.path):
        return None
    if _NO_IMAGE_PROBE.search(item.path) or scenarios_for(item).safety != "run":
        return None
    steps: tuple[Step, ...] = (
        ("open_test_image", image),
        ("run_menu_command", item.facts["command"], "accept"),
        ("record", "dialogs", "history", "pixels"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(f"{item.id}@{image}", "image_effect", "run", False, steps, None, NEVER_PRESS)


def event_settings_scenario(item: Item, event: str) -> ScenarioSpec | None:
    """A filter or adjustment run by its scripting event with its dialog shown and accepted at
    defaults: Photoshop returns the settings used. Only items that get image probes."""
    if image_scenario(item, "chart") is None:
        return None
    steps: tuple[Step, ...] = (
        ("open_test_image", "chart"),
        ("read_event_settings", event),
        ("record", "dialogs", "event_settings", "pixels"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(f"{item.id}@settings", "event_settings", "run", False, steps, None, NEVER_PRESS)


# Opening these is discovery; driving their controls is not: a ticked Neural Filter or a typed
# prompt runs AI (on Adobe's servers for some), and a file browser's buttons open real files.
_NOT_DRIVEN = re.compile(
    r"\b(Generat\w*|Neural Filters|AI Denoise|Sky Replacement|Reflection Removal|Remove Background|"
    r"Select > Subject|Mask All Objects|from File|"
    r"Camera Raw|Select and Mask)\b",  # generative remove and AI denoise; cloud Select Subject
    re.IGNORECASE,
)


def controls_scenario(item: Item, *, sandbox: bool = False) -> ScenarioSpec | None:
    """A catalogued dialog opened over the chart (so filters are available) and every control
    in it driven or read (control_pass), then cancelled; None for a command held back. With
    `sandbox`, a dialog held back only because it touches files (File Info, Place Linked, the
    file browsers) is driven over a scratch document saved in the sandbox, its new documents
    closed after; quitting, sending and AI commands never are."""
    if item.kind != "menu_command" or _NOT_DRIVEN.search(item.path) or CLOUD.search(item.path):
        return None
    probe_spec = scenarios_for(item)
    if probe_spec.safety != "run":
        if not (sandbox and probe_spec.reason == "touches files or quits") or _QUITS.search(item.path):
            return None
        steps: tuple[Step, ...] = (
            ("require_only_harness_documents",),
            ("new_throwaway_document",),
            ("save_throwaway_to_sandbox",),
            ("snapshot_documents",),
            ("drive_dialog_controls", item.facts["command"], item.path, "sandbox"),
            ("record", "dialogs", "controls", "sandbox_files"),
            ("cancel_dialogs",),
            ("close_new_documents",),
            ("close_throwaway_document",),
        )
        return ScenarioSpec(f"{item.id}@controls", "dialog_controls_sandboxed", "run", True, steps, None, NEVER_PRESS)
    steps: tuple[Step, ...] = (
        ("open_test_image", "chart"),
        ("drive_dialog_controls", item.facts["command"], item.path),
        ("record", "dialogs", "controls"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(f"{item.id}@controls", "dialog_controls", "run", True, steps, None, NEVER_PRESS)


def panel_menu_path(panel_id: str, name: str, menu_paths: set[str]) -> str | None:
    """The menu item that shows a panel: Window > name, else Type > Panels > name Panel,
    Plugins > name Panel or Filter > name; the options bar (named after the current tool,
    "Marquee Options") is Window > Options. None if no menu item shows it."""
    if panel_id.endswith(".options"):
        candidates = ["Window > Options"]
    else:
        candidates = [
            f"Window > {name}",
            f"Type > Panels > {name} Panel",
            f"Plugins > {name} Panel",
            f"Filter > {name}",
        ]
    return next((path for path in candidates if path in menu_paths), None)


def workspace_scenario(item: Item) -> ScenarioSpec | None:
    """Vanishing Point on the chart: its OK stays greyed out until a plane exists, so the
    harness finds the chart in the workspace and clicks a plane before accepting."""
    if item.kind != "menu_command" or item.path != "Filter > Vanishing Point":
        return None
    steps: tuple[Step, ...] = (
        ("open_test_image", "chart"),
        ("run_menu_command", item.facts["command"], "plane"),
        ("record", "dialogs", "history", "pixels", "workspace"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )
    return ScenarioSpec(f"{item.id}@plane", "workspace_plane", "run", True, steps, None, NEVER_PRESS)


THROWAWAY_PREFIX = "observed-truth-"


def session_blocker(open_documents: list[str]) -> str | None:
    """Why a sandboxed session must not start, if it must not; names no user document."""
    foreign = [name for name in open_documents if not name.startswith(THROWAWAY_PREFIX)]
    if not foreign:
        return None
    noun = "document" if len(foreign) == 1 else "documents"
    verb = "is" if len(foreign) == 1 else "are"
    return f"{len(foreign)} {noun} not opened by the harness {verb} open; close it or run later"


# Buttons that spend generative credits or send content to Adobe.
NEVER_PRESS = ("Generate", "Submit", "Share", "Upload", "Create link")


def _cloud_discovery(item_id: str, act: Step, needs_input: bool) -> ScenarioSpec:
    """Open the feature, record what it offers, cancel: no credits spent, nothing uploaded."""
    steps: tuple[Step, ...] = (
        ("require_only_harness_documents",),
        ("new_throwaway_document",),
        ("select_all",),  # generative features act on a selection
        act,
        ("record", "dialogs", "panels"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )
    reason = "cloud or generative AI service: discover only"
    return ScenarioSpec(item_id, "cloud_discovery", "run", needs_input, steps, reason, NEVER_PRESS)


_QUITS = re.compile(r"\b(Exit|Quit)$", re.IGNORECASE)


def _guarded(act: Step, reason: str, label: str) -> tuple[Step, ...]:
    """Steps that keep a held-back command inside scratch work and undo what it leaves."""
    before: list[Step] = [("require_only_harness_documents",), ("new_throwaway_document",)]
    after: list[Step] = []
    record: Step = ("record", "dialogs", "history", "document", "sandbox_files")
    if reason == "touches files or quits":
        before.append(("save_throwaway_to_sandbox",))
    if reason == "changes saved workspaces":
        before.append(("snapshot_workspace",))
        after.append(("restore_workspace",))
    if reason in ("opens a browser or account page", "opens another program"):
        before.append(("snapshot_windows",))
        record = ("record", "new_windows")
    waits: tuple[Step, ...] = ()
    if reason == "opens another program":
        waits = (("wait_for_new_program_window", 30),)  # Bridge takes seconds to appear
        after.append(("close_new_program_windows",))
    if _QUITS.search(label):
        # Nothing to clean up in a closed app: the only scratch document goes with it.
        return (*before, act, ("wait_for_app_exit",), ("relaunch_app",))
    cleanup: list[Step] = [("cancel_dialogs",), ("close_new_documents",), *after]
    return (
        *before,
        ("snapshot_documents",),
        act,
        *waits,
        record,
        *cleanup,
        ("close_throwaway_document",),
    )


def _held_back(
    text: str, sandbox: tuple[tuple[re.Pattern[str], str], ...]
) -> tuple[Safety, str] | None:
    for pattern, reason in _NEVER:
        if pattern.search(text):
            return "never", reason
    for pattern, reason in sandbox:
        if pattern.search(text):
            return "needs_sandbox", reason
    if CLOUD.search(text):
        return "needs_budget", "cloud or generative AI service"
    return None


def main() -> None:
    """python -m scripts.adobe_observed_truth.families --dataset <dir holding inventory.jsonl>"""
    import argparse
    import json
    from collections import Counter
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    items = load_inventory(args.dataset / "inventory.jsonl")
    specs = [scenarios_for(item, sandbox=True) for item in items]
    specs += [
        spec for image in TEST_IMAGES for item in items if (spec := image_scenario(item, image))
    ]
    specs += [spec for item in items if (spec := workspace_scenario(item))]
    terminology = args.dataset / "terminology.jsonl"
    if terminology.exists():  # built-in settings, read by running each command's event
        from .action_settings import event_for

        with terminology.open(encoding="utf-8") as handle:
            names = {json.loads(line)["name"] for line in handle}
        specs += [
            spec
            for item in items
            if item.kind == "menu_command"
            and (event := event_for(item.path, names))
            and (spec := event_settings_scenario(item, event))
        ]
    with (args.dataset / "scenario-families.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as out:
        for spec in specs:
            out.write(json.dumps(asdict(spec), sort_keys=True) + "\n")
    summary = {
        "specs": len(specs),
        "by_family_and_safety": dict(Counter(f"{s.family}:{s.safety}" for s in specs)),
        "held_back_reasons": dict(
            Counter(s.reason for s in specs if s.safety not in ("run", "observed"))
        ),
        "needs_input": sum(s.needs_input for s in specs if s.safety == "run"),
    }
    (args.dataset / "scenario-families-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
