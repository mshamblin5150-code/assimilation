"""Every dialog mapped in full: its real work run with OK pressed, under the sampler (the operator,
2026-11-23). Pass A pressed OK only for filters and adjustments; 109 other dialogs were driven
and cancelled, so the code that does their work never ran."""

from __future__ import annotations

from pathlib import Path

import cv2
from PIL import Image

from scripts.adobe_observed_truth.dialog_work import FILE_ANSWERS, make_input, work_settings_specs, work_specs
from scripts.adobe_observed_truth.inventory import Item


def _command(path: str, command: int) -> Item:
    return Item("menu_command", f"menu:{command}", path.rsplit(" > ", 1)[-1], path, {"command": command})


def test_a_dialog_on_the_chart_is_run_with_ok_pressed_and_what_it_made_closed() -> None:
    (spec,) = work_specs([_command("Image > Image Size", 1500)], with_dialogs={"menu:1500"})

    assert (spec.item_id, spec.family, spec.safety) == ("menu:1500@work", "dialog_work", "run")
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("snapshot_documents",),
        ("run_menu_command", 1500, "accept"),
        ("record", "dialogs", "history", "document", "pixels"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    )
    assert "Generate" in spec.never_press


def test_commands_without_a_dialog_and_filters_already_accepted_get_no_work_run() -> None:
    items = [
        _command("Image > Image Size", 1500),
        _command("Layer > Flatten Image", 1600),  # no dialog: pass A already ran its work
        _command("Filter > Blur > Gaussian Blur", 1700),  # image_effect presses OK already
        _command("Image > Adjustments > Levels", 1701),
    ]

    specs = work_specs(items, with_dialogs={"menu:1500", "menu:1700", "menu:1701"})

    assert [s.item_id for s in specs] == ["menu:1500@work"]


def test_ai_cloud_and_sending_dialogs_are_never_run_with_ok() -> None:
    items = [
        _command("Edit > Sky Replacement", 1),
        _command("Image > Generative Upscale", 2),
        _command("Select > Subject", 3),
        _command("File > Share", 4),
        _command("Layer > Mask All Objects", 5),
        _command("Edit > Prompt to Edit", 6),
        _command("Edit > Rotate Object", 7),
    ]

    assert work_specs(items, with_dialogs={f"menu:{i}" for i in range(1, 8)}) == []


def test_a_define_dialog_is_accepted_then_the_preset_it_added_is_deleted() -> None:
    (spec,) = work_specs([_command("Edit > Define Pattern", 1800)], with_dialogs={"menu:1800"})

    assert ("count_presets", "pattern") in spec.steps
    assert spec.steps.index(("count_presets", "pattern")) < spec.steps.index(("run_menu_command", 1800, "accept"))
    assert spec.steps.index(("delete_added_presets", "pattern")) < spec.steps.index(("close_throwaway_document",))


def test_a_file_dialog_is_answered_with_a_file_the_harness_made_in_the_sandbox() -> None:
    (place,) = work_specs([_command("File > Place Embedded", 1900)], with_dialogs={"menu:1900"})
    (save,) = work_specs([_command("File > Save As", 32)], with_dialogs={"menu:32"})

    assert place.steps[:2] == (("require_only_harness_documents",), ("open_test_image", "chart"))
    assert ("answer_file_dialogs", "input", "chart.png") in place.steps
    assert ("answer_file_dialogs", "output", "saved-as.psd") in save.steps
    for spec in (place, save):
        answer = next(s for s in spec.steps if s[0] == "answer_file_dialogs")
        assert spec.steps.index(answer) < spec.steps.index(next(s for s in spec.steps if s[0] == "run_menu_command"))
        assert ("record", "dialogs", "history", "document", "sandbox_files") in spec.steps


def test_every_input_a_file_dialog_is_answered_with_is_a_real_file_of_its_kind(tmp_path: Path) -> None:
    inputs = {name for mode, name in FILE_ANSWERS.values() if mode == "input"}

    for name in inputs:
        make_input(name, tmp_path / name)

    with Image.open(tmp_path / "chart.png") as chart:
        assert chart.size[0] > 100
    assert (tmp_path / "notes.pdf").read_bytes().startswith(b"%PDF")
    clip = cv2.VideoCapture(str(tmp_path / "clip.mp4"))
    assert clip.isOpened() and int(clip.get(cv2.CAP_PROP_FRAME_COUNT)) >= 10
    clip.release()
    assert (tmp_path / "harmless.jsx").read_text(encoding="utf-8").strip().endswith(";")


def test_a_file_command_with_no_sandbox_answer_yet_gets_no_work_run() -> None:
    assert work_specs([_command("File > Automate > Contact Sheet II", 2000)], with_dialogs={"menu:2000"}) == []


def test_a_dialog_whose_work_needs_its_own_buttons_is_run_by_a_sandbox_recipe_instead() -> None:
    # PDF Presentation and Save for Web need a button inside their window first (Browse…, Save…);
    # Photoshop's scripting does the same work into sandbox files (2026-11-24).
    items = [_command("File > Automate > PDF Presentation", 1696), _command("File > Export > Save for Web", 1695)]

    specs = work_specs(items, with_dialogs={"menu:1696", "menu:1695"})

    assert [(s.item_id, s.steps[0], s.steps[3]) for s in specs] == [
        ("menu:1696@work", ("require_only_harness_documents",), ("run_recipe", "pdf_presentation")),
        ("menu:1695@work", ("require_only_harness_documents",), ("run_recipe", "save_for_web")),
    ]
    assert all(("record", "dialogs", "history", "document", "recipe_files") in s.steps for s in specs)


def test_batch_gets_no_work_run_its_scripting_opens_a_window_that_cannot_be_read() -> None:
    # app.batch opened the Batch window instead of running (2026-11-24), and its lists are drawn
    # by Photoshop, so what OK would run cannot be checked first: held for a window recipe.
    assert work_specs([_command("File > Automate > Batch", 1180)], with_dialogs={"menu:1180"}) == []


def test_a_recipe_runs_whether_or_not_its_dialog_was_ever_seen_opening() -> None:
    # PDF Presentation was never seen opening a dialog (no control spec), yet its recipe needs none.
    (spec,) = work_specs([_command("File > Automate > PDF Presentation", 1696)], with_dialogs=set())

    assert ("run_recipe", "pdf_presentation") in spec.steps


def test_a_recipe_or_scratch_dialog_never_has_its_settings_read_by_accepting_its_defaults() -> None:
    # A settings read accepts the dialog at its defaults: Batch's default source can be a folder
    # of the person's and its destination can save over the originals (caught 2026-11-24, unrun).
    items = [_command("File > Automate > Batch", 1180), _command("File > Export > Save for Web", 1695),
             _command("File > File Info", 1137)]

    specs = work_settings_specs(items, {"menu:1180", "menu:1695", "menu:1137"}, {"batch", "export", "fileInfo"})

    assert specs == []


def test_file_info_is_accepted_on_a_scratch_document_saved_in_the_sandbox() -> None:
    # OK writes its metadata to the open document: a scratch one, closed unsaved after.
    (spec,) = work_specs([_command("File > File Info", 1137)], with_dialogs={"menu:1137"})

    assert spec.steps[:4] == (("require_only_harness_documents",), ("new_throwaway_document",),
                              ("save_throwaway_to_sandbox",), ("snapshot_documents",))
    assert ("run_menu_command", 1137, "accept") in spec.steps and spec.steps[-1] == ("close_throwaway_document",)


def test_a_dialog_with_a_scripting_event_has_its_settings_read_so_each_can_be_swept() -> None:
    # The setting sweep (sweeps.py) varies each setting it reads: every choice, both on/off, numbers.
    items = [_command("Image > Canvas Size", 1100), _command("Edit > Fill", 1101), _command("File > Save As", 32)]

    specs = work_settings_specs(items, with_dialogs={"menu:1100", "menu:1101", "menu:32"},
                                events={"canvasSize", "fill", "saveAs"})

    assert [s.item_id for s in specs] == ["menu:1100@settings", "menu:1101@settings"]
    assert ("read_event_settings", "canvasSize") in specs[0].steps
    assert specs[0].family == "event_settings"


def test_a_dialog_whose_name_matches_another_commands_event_has_no_settings_read() -> None:
    # "levels" is Image > Adjustments > Levels, not the adjustment layer; "dropShadow" names an effect.
    items = [_command("Layer > New Adjustment Layer > Levels", 1), _command("Layer > New Fill Layer > Gradient", 2),
             _command("Layer > Layer Style > Drop Shadow", 3), _command("Layer > New > Layer", 4)]

    specs = work_settings_specs(items, with_dialogs={"menu:1", "menu:2", "menu:3", "menu:4"},
                                events={"levels", "gradient", "dropShadow", "layer"})

    assert specs == []


def test_settings_lists_that_cannot_be_checked_for_the_persons_entries_are_held() -> None:
    # Reset Pixel Aspect Ratios replaces the list: the person's own ratios would go too.
    items = [_command(f"View > Pixel Aspect Ratio > {name}", n) for n, name in
             ((1202, "Custom Pixel Aspect Ratio"), (1203, "Delete Pixel Aspect Ratio"), (1204, "Reset Pixel Aspect Ratios"))]

    assert work_specs(items, with_dialogs={"menu:1202", "menu:1203", "menu:1204"}) == []
