"""Every dialog mapped in full: its real work run with OK pressed, under the sampler.

Pass A pressed OK only for filters and adjustments (image_effect); every other dialog had its
controls driven and was cancelled, so the code that does its work never ran (the operator, 2026-11-23:
"we need to know what code it pulls; that's how we know how Photoshop works"). work_specs()
gives each such dialog a run on the test chart with OK pressed at its defaults, and whatever it
made (a duplicate, a new document) closed after. AI and cloud dialogs never get OK: some send
the image to Adobe's servers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import cv2
import numpy as np

from . import test_images
from .action_settings import event_for
from .claim_map import CLOUD
from .families import _NOT_DRIVEN, NEVER_PRESS, ScenarioSpec, Step, image_scenario, scenarios_for
from .inventory import Item

# Firefly features under names the generic patterns miss.
_AI = re.compile(r"\b(Prompt to Edit|Rotate Object|Generate Image)\b", re.IGNORECASE)
# Held back from pass A for a reason a scratch chart already answers.
_SCRATCH_ANSWERS = frozenset({"opens a document the harness does not own"})
# Settings that outlive Photoshop are accepted unchanged (the operator, 2026-11-23); a preset a Define
# dialog adds is deleted after, counted first so only the harness's own goes.
_DEFINES = {
    "Edit > Define Pattern": "pattern",
    "Edit > Define Brush Preset": "brush",
    "Edit > Define Custom Shape": "shape",
}
# Commands whose dialogs ask for a file: answered with one the harness makes in the sandbox
# (input) or a name there to write (output). Never the person's folders.
FILE_ANSWERS: dict[str, tuple[str, str]] = {
    "File > Place Embedded": ("input", "chart.png"),
    "File > Place Linked": ("input", "chart.png"),
    "File > Import > Notes": ("input", "notes.pdf"),
    "File > Import > Video Frames to Layers": ("input", "clip.mp4"),
    "Layer > Video Layers > New Video Layer from File": ("input", "clip.mp4"),
    "File > Scripts > Browse": ("input", "harmless.jsx"),
    "File > Save As": ("output", "saved-as.psd"),
    "File > Save a Copy": ("output", "saved-copy.psd"),
    "File > Export > Paths to Illustrator": ("output", "paths.ai"),
}
# Dialogs whose work needs a button inside their window first (Choose…, Browse…, Save…): run by
# Photoshop's scripting into sandbox files instead (runner_photoshop.RECIPES, 2026-11-24).
RECIPES: dict[str, str] = {
    "File > Automate > PDF Presentation": "pdf_presentation",
    "File > Export > Save for Web": "save_for_web",
}
# Accepted on a scratch document saved in the sandbox: OK writes to the open document only.
ON_SCRATCH = frozenset({"File > File Info"})
# Names that event_for() would match to a different command's event: an adjustment or fill
# layer's last word is the image adjustment ("levels"), a style pane's is an effect class.
_OTHER_EVENT = re.compile(r"^Layer > (New Adjustment Layer|New Fill Layer|Layer Style|New) > ")
# Lists the harness cannot read (Photoshop draws its own menus), so it cannot prove the person's
# entries are left alone: Reset replaces the list, Delete removes whichever is chosen.
HELD = re.compile(r"^View > Pixel Aspect Ratio > (Custom|Delete|Reset)")


def make_input(name: str, path: Path) -> None:
    """Write the sandbox file `name` a file dialog is answered with: the chart, the chart as a
    PDF (Import Notes), a 12-frame clip of the chart drifting (video imports), or a script that
    only returns a string (Scripts > Browse runs what it is given)."""
    chart = test_images.chart().convert("RGB")
    if name == "chart.png":
        chart.save(path)
    elif name == "notes.pdf":
        chart.save(path, "PDF")
    elif name == "clip.mp4":
        frame = cv2.cvtColor(np.asarray(chart), cv2.COLOR_RGB2BGR)
        height, width = frame.shape[:2]
        video = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 12, (width, height))
        for shift in range(12):
            video.write(np.roll(frame, shift * 4, axis=1))
        video.release()
    elif name == "harmless.jsx":
        path.write_text('"the harness script ran";\n', encoding="utf-8")
    else:
        raise ValueError(f"no sandbox input {name!r}")


def _never_accepted(item: Item) -> bool:
    return bool(_NOT_DRIVEN.search(item.path) or CLOUD.search(item.path) or _AI.search(item.path)
                or HELD.search(item.path))


def work_settings_specs(items: Iterable[Item], with_dialogs: set[str], events: set[str]) -> list[ScenarioSpec]:
    """For each dialog given a work run on the chart (not a file or preset one) whose command
    has a scripting event: the event run with its dialog accepted at defaults, so Photoshop
    returns its settings and the setting sweep (sweeps.py) can run it once per choice, on/off
    and number of each."""
    by_work = {f"{i.id}@work": i for i in items}
    specs = []
    for spec in work_specs(list(by_work.values()), with_dialogs):
        item = by_work[spec.item_id]
        # Recipes and scratch dialogs are file work too: accepting Batch at its defaults could read
        # a folder of the person's and save over the originals (2026-11-24).
        if (item.path in FILE_ANSWERS or item.path in _DEFINES or item.path in RECIPES or item.path in ON_SCRATCH
                or _OTHER_EVENT.search(item.path)
                or not (event := event_for(item.path, events))):
            continue
        specs.append(ScenarioSpec(f"{item.id}@settings", "event_settings", "run", False, (
            ("open_test_image", "chart"),
            ("read_event_settings", event),
            ("record", "dialogs", "event_settings", "pixels"),
            ("cancel_dialogs",),
            ("close_throwaway_document",),
        ), None, NEVER_PRESS))
    return specs


def work_specs(items: Iterable[Item], with_dialogs: set[str]) -> list[ScenarioSpec]:
    """A run with OK pressed for each menu command in `with_dialogs` (ids of commands seen to
    open a dialog) whose work no other family runs."""
    specs = []
    for item in items:
        if item.kind != "menu_command" or _never_accepted(item):
            continue
        if recipe := RECIPES.get(item.path):  # needs no dialog: PDF Presentation was never seen opening one
            specs.append(_recipe_spec(item, recipe))
            continue
        if item.id not in with_dialogs:
            continue
        if image_scenario(item, "chart") is not None:
            continue  # its OK is pressed already
        if item.path in ON_SCRATCH:
            specs.append(_scratch_spec(item))
            continue
        preset, answer = _DEFINES.get(item.path), FILE_ANSWERS.get(item.path)
        probe = scenarios_for(item)
        if probe.safety != "run" and probe.reason not in _SCRATCH_ANSWERS and not (preset or answer):
            continue
        guard: tuple[Step, ...] = (("require_only_harness_documents",),) if answer else ()
        before: tuple[Step, ...] = (
            *((("count_presets", preset),) if preset else ()),
            *((("answer_file_dialogs", *answer),) if answer else ()),
        )
        after: tuple[Step, ...] = (("delete_added_presets", preset),) if preset else ()
        seen = ("sandbox_files",) if answer else ("pixels",)
        specs.append(ScenarioSpec(f"{item.id}@work", "dialog_work", "run", False, (
            *guard,
            ("open_test_image", "chart"),
            ("snapshot_documents",),
            *before,
            ("run_menu_command", item.facts["command"], "accept"),
            ("record", "dialogs", "history", "document", *seen),
            ("cancel_dialogs",),
            *after,
            ("close_new_documents",),
            ("close_throwaway_document",),
        ), None, NEVER_PRESS))
    return specs


def _recipe_spec(item: Item, recipe: str) -> ScenarioSpec:
    return ScenarioSpec(f"{item.id}@work", "dialog_work", "run", False, (
        ("require_only_harness_documents",),
        ("open_test_image", "chart"),
        ("snapshot_documents",),
        ("run_recipe", recipe),
        ("record", "dialogs", "history", "document", "recipe_files"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    ), None, NEVER_PRESS)


def _scratch_spec(item: Item) -> ScenarioSpec:
    return ScenarioSpec(f"{item.id}@work", "dialog_work", "run", False, (
        ("require_only_harness_documents",),
        ("new_throwaway_document",),
        ("save_throwaway_to_sandbox",),
        ("snapshot_documents",),
        ("run_menu_command", item.facts["command"], "accept"),
        ("record", "dialogs", "history", "document"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    ), None, NEVER_PRESS)


def dialog_ids(control_specs: Iterable[str], results: Iterable[str]) -> set[str]:
    """Menu commands known to open a dialog: the control catalogue's (control-families.jsonl
    lines) and every menu command a sweep saw open one (results.jsonl lines)."""
    ids = {json.loads(line)["item_id"].removesuffix("@controls") for line in control_specs if line.strip()}
    for line in results:
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a line cut short
        if row["item_id"].startswith("menu:") and "@" not in row["item_id"] and (row.get("observations") or {}).get("dialogs"):
            ids.add(row["item_id"])
    return ids


def main() -> None:
    """python -m scripts.adobe_observed_truth.dialog_work --dataset <dir> --results <sweep>/results.jsonl

    Write work-families.jsonl: every dialog's work run with OK pressed, then each one's
    settings read for the setting sweep. Run it with runner_photoshop --specs work-families.jsonl;
    then sweeps.py turns the settings read into one run per choice."""
    import argparse
    from dataclasses import asdict

    from .inventory import load_inventory

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    items = load_inventory(args.dataset / "inventory.jsonl")
    ids = dialog_ids((args.dataset / "control-families.jsonl").read_text(encoding="utf-8").splitlines(),
                     args.results.read_text(encoding="utf-8").splitlines())
    with (args.dataset / "terminology.jsonl").open(encoding="utf-8") as handle:
        events = {json.loads(line)["name"] for line in handle}
    specs = work_specs(items, ids) + work_settings_specs(items, ids, events)
    with (args.dataset / "work-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    held = sorted(i.path for i in items if i.id in ids and HELD.search(i.path))
    print(f"{len(specs)} specs in work-families.jsonl; held: {held}")


if __name__ == "__main__":
    main()
