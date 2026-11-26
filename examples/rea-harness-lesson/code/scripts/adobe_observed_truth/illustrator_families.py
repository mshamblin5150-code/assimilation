"""Illustrator's menu commands as sweep specs (runner_illustrator).

Each command runs by its internal name (app.executeMenuCommand) on a scratch document of test
art (new_fixture), with its dialogs answered by Cancel, then the document is closed. Never run:
commands that would leave or hide the app, save, export, print or package, touch the licence or
the cloud, open another program, or change the person's workspace; anything named "Feedback" is
kept out too. Commands that open a file dialog are held for a work pass, as in Photoshop.
"""

from __future__ import annotations

import json
import re

from .families import NEVER_PRESS, ScenarioSpec
from .inventory import Item

_NEVER_NAMES = frozenset({
    "quit", "hideApp", "hideOthers", "minimizeWindow", "close", "closeAll",
    "save", "saveas", "saveacopy", "saveasTemplate", "export", "exportForScreens", "Save for Office",
    "Adobe AI Save For Web", "Adobe Save a Version", "Package Menu Item", "Print", "Adobe Actions Batch",
    "Activate...", "Deactivate...", "Updates...", "Registration...", "Adobe Illustrator Kuler Panel",
    "EditOriginal Menu Item", "Adobe Bridge Browse", "Adobe AI Device center",
    "helpcontent", "helpcontent2", "Welcome screen menu item",
    "Adobe Default Workspace", "Adobe Reset Workspace", "Adobe New Workspace", "Adobe Manage Workspace",
})
_NEVER_PATTERN = re.compile(r"Other libraries|Generate|Feedback", re.IGNORECASE)
_FILE_DIALOG = frozenset({"open", "newFromTemplate", "AI Place", "ai_browse_for_script"})


def safety_of(name: str) -> str:
    """run, never, or file_dialog (held for the work pass)."""
    if name in _NEVER_NAMES or _NEVER_PATTERN.search(name):
        return "never"
    if name in _FILE_DIALOG:
        return "file_dialog"
    return "run"


def menu_specs(items: list[Item]) -> list[ScenarioSpec]:
    """One spec per menu command; never and file-dialog commands are recorded with no steps."""
    specs = []
    for item in items:
        if item.kind != "menu_command":
            continue
        name = item.facts.get("command_name", item.name)
        safety = safety_of(name)
        if safety != "run":
            specs.append(ScenarioSpec(item.id, "menu_command", "never", reason=safety))
            continue
        steps = (("new_fixture",), ("run_menu_command", name), ("record", "dialogs", "document"),
                 ("cancel_dialogs",), ("close_throwaway_document",))
        specs.append(ScenarioSpec(item.id, "menu_command", "run", False, steps, None, NEVER_PRESS))
    return specs


_NOT_DIALOGS = ("com.adobe.AdobeSplashKit",)  # the About box: nothing to drive


def control_specs(results: list[str], specs: list[ScenarioSpec], *, drive: bool = True) -> list[ScenarioSpec]:
    """For each command whose latest run (results.jsonl lines) opened a dialog, a spec that runs it
    again and drives every control of that dialog (runner_illustrator drive_dialog_controls), or
    with `drive` False surveys it: the dialog read and its dropdowns opened, nothing driven
    (survey_dialog; about 4 minutes a dialog driven, so only the ones worth it are driven later)."""
    latest: dict[str, dict] = {}
    for line in results:
        if line.strip():
            row = json.loads(line)
            latest[row["item_id"]] = row
    out = []
    for spec in specs:
        dialogs = ((latest.get(spec.item_id) or {}).get("observations") or {}).get("dialogs") or []
        if not any(not str(d.get("class", "")).startswith(_NOT_DIALOGS) for d in dialogs):
            continue
        command = spec.steps[1][1]
        act, kind = (("drive_dialog_controls", command, True), "controls") if drive else (("survey_dialog", command), "survey")
        steps = (("new_fixture",), act, ("record", "dialogs", kind), ("cancel_dialogs",), ("close_throwaway_document",))
        suffix, family = ("controls", "dialog_controls") if drive else ("survey", "dialog_survey")
        out.append(ScenarioSpec(f"{spec.item_id}@{suffix}", family, "run", True, steps, None, NEVER_PRESS))
    return out


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_families --dataset <dir>: write menu-families.jsonl."""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    from .inventory import load_inventory

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--controls", type=Path, help="a sweep's results.jsonl: write control-families.jsonl instead")
    parser.add_argument("--survey", action="store_true", help="with --controls: survey the dialogs, drive none")
    args = parser.parse_args()
    specs = menu_specs(load_inventory(args.dataset / "inventory.jsonl"))
    if args.controls:
        driven = control_specs(args.controls.read_text(encoding="utf-8").splitlines(), [s for s in specs if s.steps],
                               drive=not args.survey)
        name = "survey-families.jsonl" if args.survey else "control-families.jsonl"
        with (args.dataset / name).open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in driven)
        print(f"{len(driven)} dialog specs written to {name}")
        return
    with (args.dataset / "menu-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    runs = sum(1 for s in specs if s.safety == "run")
    print(f"{len(specs)} menu specs, {runs} to run")


if __name__ == "__main__":
    main()
