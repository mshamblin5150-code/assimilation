"""Illustrator's menu commands as sweep specs: each run on a scratch document by its command name,
except those that would leave the app, write files, touch the licence or the cloud, open another
program or change the person's workspace (never), or open a file dialog (held for a work pass)."""

from __future__ import annotations

import json

from scripts.adobe_observed_truth.families import ScenarioSpec
from scripts.adobe_observed_truth.illustrator_families import control_specs, menu_specs, safety_of


def test_each_command_that_opened_a_dialog_gets_its_controls_driven_the_about_box_does_not() -> None:
    steps = (("new_fixture",), ("run_menu_command", "transformrotate"), ("record", "dialogs", "document"),
             ("cancel_dialogs",), ("close_throwaway_document",))
    specs = [ScenarioSpec("menu:transformrotate", "menu_command", "run", False, steps),
             ScenarioSpec("menu:about", "menu_command", "run", False, steps),
             ScenarioSpec("menu:group", "menu_command", "run", False, steps)]
    results = [json.dumps({"item_id": "menu:transformrotate", "status": "ok",
                           "observations": {"dialogs": [{"class": "#32770"}]}}),
               json.dumps({"item_id": "menu:about", "status": "ok",
                           "observations": {"dialogs": [{"class": "com.adobe.AdobeSplashKit.TextWindowClass"}]}}),
               json.dumps({"item_id": "menu:group", "status": "ok", "observations": {"dialogs": []}})]

    [rotate] = control_specs(results, specs)

    assert (rotate.item_id, rotate.family, rotate.needs_input) == ("menu:transformrotate@controls", "dialog_controls", True)
    assert rotate.steps == (("new_fixture",), ("drive_dialog_controls", "transformrotate", True),
                            ("record", "dialogs", "controls"), ("cancel_dialogs",), ("close_throwaway_document",))
    # A survey looks: the dialog read and its dropdowns opened, no control walked or driven
    # (dialog_dropdowns.survey_dialog); the dialogs worth it are driven later.
    [survey] = control_specs(results, specs, drive=False)
    assert (survey.item_id, survey.family) == ("menu:transformrotate@survey", "dialog_survey")
    assert survey.steps[1] == ("survey_dialog", "transformrotate")
    assert survey.steps[2] == ("record", "dialogs", "survey")
from scripts.adobe_observed_truth.inventory import Item


def test_commands_that_leave_write_license_reach_out_or_change_the_workspace_never_run() -> None:
    never = ["quit", "hideApp", "hideOthers", "minimizeWindow", "save", "saveas", "saveacopy", "saveasTemplate",
             "export", "exportForScreens", "Save for Office", "Adobe AI Save For Web", "Adobe Save a Version",
             "Package Menu Item", "Print", "Adobe Actions Batch", "Activate...", "Deactivate...", "Updates...",
             "Registration...", "Adobe Art Style Plugin Other libraries menu item", "Adobe Illustrator Kuler Panel",
             "Generate Modal File Menu ", "EditOriginal Menu Item", "Adobe Bridge Browse", "Adobe AI Device center",
             "helpcontent", "Welcome screen menu item", "Adobe Reset Workspace", "Adobe New Workspace",
             "AISlice Feedback Menu", "close", "closeAll"]

    assert {name: safety_of(name) for name in never} == {name: "never" for name in never}


def test_commands_that_open_a_file_dialog_are_held_for_the_work_pass() -> None:
    assert {n: safety_of(n) for n in ("open", "newFromTemplate", "AI Place", "ai_browse_for_script")} == {
        n: "file_dialog" for n in ("open", "newFromTemplate", "AI Place", "ai_browse_for_script")}


def test_everything_else_runs_on_a_scratch_document_with_its_dialogs_cancelled() -> None:
    assert {n: safety_of(n) for n in ("group", "Live Pathfinder Add", "transformrotate", "preference", "about")} == {
        n: "run" for n in ("group", "Live Pathfinder Add", "transformrotate", "preference", "about")}
    items = [Item("menu_command", "menu:group", "group", "Menu command group", {"command_name": "group"}),
             Item("menu_command", "menu:quit", "quit", "Menu command quit", {"command_name": "quit"}),
             Item("tool", "tool:x", "x", "Toolbar > x", {})]

    specs = {s.item_id: s for s in menu_specs(items)}

    assert set(specs) == {"menu:group", "menu:quit"}
    group = specs["menu:group"]
    assert (group.family, group.safety, group.needs_input) == ("menu_command", "run", False)
    assert group.steps == (("new_fixture",), ("run_menu_command", "group"), ("record", "dialogs", "document"),
                           ("cancel_dialogs",), ("close_throwaway_document",))
    assert {"Generate", "Share", "Submit", "Upload", "Create link"} <= set(group.never_press)
    assert specs["menu:quit"].safety == "never" and specs["menu:quit"].steps == ()
