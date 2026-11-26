from __future__ import annotations

from scripts.adobe_observed_truth.families import (
    controls_scenario,
    event_settings_scenario,
    image_scenario,
    panel_menu_path,
    scenarios_for,
    session_blocker,
    workspace_scenario,
)
from scripts.adobe_observed_truth.inventory import Item


def menu(command: int, path: str) -> Item:
    return Item(
        "menu_command", f"menu:{command}", path.rsplit(" > ", 1)[-1], path, {"command": command}
    )


def test_a_menu_command_runs_on_the_test_chart_and_cancels_any_dialog() -> None:
    # 2026-11-23: on a blank document Photoshop takes its nothing-to-do branches (empty
    # histograms, nothing to analyse), so a sampled sweep would miss the code doing the work.
    spec = scenarios_for(menu(1180, "Filter > Blur > Gaussian Blur"))

    assert spec.family == "menu_command"
    assert spec.safety == "run"
    assert spec.needs_input is False
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("run_menu_command", 1180),
        ("record", "dialogs", "history", "document"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )


def test_nothing_is_excluded_for_good_except_signing_out() -> None:
    cases = {
        "File > Save As": ("needs_sandbox", "touches files or quits"),
        "Help > Photoshop Help": ("needs_sandbox", "opens a browser or account page"),
        "Edit > Generative Fill": ("needs_budget", "cloud or generative AI service"),
        "Edit > Purge > All": ("needs_sandbox", "affects the user's open documents"),
        "Window > Arrange > Tile All Vertically": (
            "needs_sandbox",
            "affects the user's open documents",
        ),
        "Edit > Define Pattern": ("needs_sandbox", "changes saved presets"),
        "Window > Workspace > New Workspace": ("needs_sandbox", "changes saved workspaces"),
        "Help > Sign Out": ("never", "signs out of Creative Cloud"),
    }

    for path, expected in cases.items():
        spec = scenarios_for(menu(1, path))
        assert (spec.safety, spec.reason, spec.steps) == (*expected, ()), path


def test_a_file_command_runs_inside_the_sandbox_and_cleans_up_after_itself() -> None:
    spec = scenarios_for(menu(1013, "File > Save As"), sandbox=True)

    assert (spec.family, spec.safety, spec.reason) == (
        "menu_command_sandboxed",
        "run",
        "touches files or quits",
    )
    assert spec.steps == (
        ("require_only_harness_documents",),
        ("new_throwaway_document",),
        ("save_throwaway_to_sandbox",),
        ("snapshot_documents",),
        ("run_menu_command", 1013),
        ("record", "dialogs", "history", "document", "sandbox_files"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    )


def test_exit_runs_on_scratch_work_only_and_relaunches_the_app_afterwards() -> None:
    steps = scenarios_for(menu(1960, "File > Exit"), sandbox=True).steps

    assert steps[0] == ("require_only_harness_documents",)
    assert steps[-2:] == (("wait_for_app_exit",), ("relaunch_app",))


def test_a_workspace_command_puts_the_previous_workspace_back() -> None:
    steps = scenarios_for(menu(3001, "Window > Workspace > Painting"), sandbox=True).steps

    assert steps.index(("snapshot_workspace",)) < steps.index(("run_menu_command", 3001))
    assert steps.index(("restore_workspace",)) > steps.index(("run_menu_command", 3001))


def test_a_command_that_opens_another_adobe_program_closes_its_window_afterwards() -> None:
    spec = scenarios_for(menu(1530, "File > Close and Go to Bridge"), sandbox=True)

    assert spec.reason == "opens another program"
    steps = spec.steps
    assert steps.index(("snapshot_windows",)) < steps.index(("run_menu_command", 1530))
    # Bridge takes seconds to start: wait for it before recording, or there is nothing to close.
    assert steps.index(("wait_for_new_program_window", 30)) < steps.index(("record", "new_windows"))
    assert ("close_new_program_windows",) in steps


def test_a_help_page_records_the_window_it_opened() -> None:
    steps = scenarios_for(menu(4001, "Help > Photoshop Help"), sandbox=True).steps

    assert ("snapshot_windows",) in steps
    assert ("record", "new_windows") in steps


FORBIDDEN = ("Generate", "Submit", "Share", "Upload", "Create link")


def test_a_cloud_feature_is_opened_recorded_and_cancelled_never_generated() -> None:
    spec = scenarios_for(menu(5001, "Edit > Generative Fill"), sandbox=True)

    assert (spec.family, spec.safety) == ("cloud_discovery", "run")
    assert spec.never_press == FORBIDDEN
    assert spec.steps == (
        ("require_only_harness_documents",),
        ("new_throwaway_document",),
        ("select_all",),
        ("run_menu_command", 5001),
        ("record", "dialogs", "panels"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )


def test_a_command_that_sends_content_to_adobe_is_never_run_even_from_the_file_menu() -> None:
    # 2026-11-09: File > Export > Send to Firefly Boards ran as a file export and started
    # "Uploading files to the cloud..." before the harness cancelled it.
    for path in (
        "File > Export > Send to Firefly Boards",
        "File > Share",
        "File > Publish to Adobe Portfolio",
        "File > Upload to Behance",
        "Edit > Share for Review",
    ):
        spec = scenarios_for(menu(5003, path), sandbox=True)

        assert spec.safety == "never", path

    assert scenarios_for(menu(2714, "Layer > Arrange > Send to Back")).safety == "run"


def test_no_spec_anywhere_presses_a_button_that_spends_credits_or_uploads() -> None:
    items = [
        menu(5001, "Edit > Generative Fill"),
        menu(5002, "Image > Generative Upscale"),
        Item(
            "shortcut",
            "shortcut:Alt+Ctrl+S",
            "Alt+Ctrl+S",
            "Keyboard Shortcuts > Share for review",
            {"keys": "Alt+Ctrl+S", "command": "Share for review", "set": "x"},
        ),
    ]

    for item in items:
        spec = scenarios_for(item, sandbox=True)
        pressed = [str(arg) for step in spec.steps if step[0] == "press" for arg in step[1:]]
        assert not any(word.lower() in p.lower() for p in pressed for word in FORBIDDEN), item.id
        assert spec.safety == "never" or spec.never_press == FORBIDDEN, item.id


def test_session_precondition_refuses_when_any_non_harness_document_is_open() -> None:
    assert session_blocker(["observed-truth-a", "observed-truth-b"]) is None
    assert session_blocker(["observed-truth-a", "holiday.psd"]) == (
        "1 document not opened by the harness is open; close it or run later"
    )


def test_filter_render_clouds_is_a_filter_not_a_cloud_service() -> None:
    assert scenarios_for(menu(1501, "Filter > Render > Clouds")).safety == "run"


def test_a_view_toggle_is_run_again_to_put_it_back() -> None:
    steps = scenarios_for(menu(1253, "View > Rulers")).steps

    # A clean-up step, so it still runs if the spec fails or is interrupted after the toggle.
    assert steps.index(("toggle_back", 1253)) > steps.index(("run_menu_command", 1253))
    assert steps.count(("run_menu_command", 1253)) == 1


def test_submenus_are_covered_by_their_items() -> None:
    submenu = Item("submenu", "submenu:Edit", "Edit", "Edit", {"command": 0})

    assert scenarios_for(submenu).safety == "covered_by_items"


def test_a_panel_is_shown_recorded_and_put_back_as_it_was() -> None:
    panel = Item("panel", "panel:panelid.static.layers", "Layers", "Window > Layers", {})

    spec = scenarios_for(panel)

    assert (spec.family, spec.safety) == ("panel_open", "run")
    assert spec.steps == (
        ("snapshot_panels",),
        ("show_panel", "panelid.static.layers"),
        ("record", "panels"),
        ("restore_panels",),
    )


def test_file_new_is_allowed_because_the_harness_only_creates_throwaway_documents() -> None:
    assert scenarios_for(menu(10, "File > New")).safety == "run"


def test_a_shortcut_is_pressed_on_a_throwaway_document_unless_its_command_is_unsafe() -> None:
    liquify = Item(
        "shortcut",
        "shortcut:Shift+Ctrl+X",
        "Shift+Ctrl+X",
        "Keyboard Shortcuts > Liquify",
        {"keys": "Shift+Ctrl+X", "command": "Liquify", "set": "Default Keyboard Shortcuts"},
    )
    share = Item(
        "shortcut",
        "shortcut:Alt+Ctrl+S",
        "Alt+Ctrl+S",
        "Keyboard Shortcuts > Share for review",
        {"keys": "Alt+Ctrl+S", "command": "Share for review", "set": "Default Keyboard Shortcuts"},
    )

    spec = scenarios_for(liquify)
    assert (spec.family, spec.safety, spec.needs_input) == ("shortcut", "run", True)
    assert ("press", "Shift+Ctrl+X") in spec.steps
    assert scenarios_for(share).safety == "never"


def test_a_tool_is_selected_by_its_shortcut_letter_and_checked_by_script() -> None:
    brush = Item(
        "tool",
        "tool:paintbrushTool",
        "Brush Tool",
        "Toolbar > Brush Tool",
        {"tool_id": "paintbrushTool", "shortcut": "B", "in_toolbar": True},
    )

    spec = scenarios_for(brush)
    assert (spec.family, spec.needs_input) == ("tool_shortcut", True)
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("press", "B"),
        ("record", "current_tool"),
        ("close_throwaway_document",),
    )


def test_a_preference_needs_no_run_its_factory_value_is_already_observed() -> None:
    history = Item(
        "preference",
        "pref:historyPreferences.maximumStates",
        "maximumStates",
        "Preferences > historyPreferences",
        {"value": 50},
    )

    spec = scenarios_for(history)
    assert (spec.family, spec.safety, spec.reason) == (
        "preference_default",
        "observed",
        "factory value read from the inventory",
    )


def test_a_filter_runs_on_a_test_image_accepting_its_defaults_and_records_the_pixels() -> None:
    spec = image_scenario(menu(1180, "Filter > Blur > Gaussian Blur"), "chart")

    assert spec is not None
    assert (spec.item_id, spec.family, spec.safety) == ("menu:1180@chart", "image_effect", "run")
    assert spec.never_press == FORBIDDEN
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("run_menu_command", 1180, "accept"),
        ("record", "dialogs", "history", "pixels"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )


def test_an_adjustment_also_gets_an_image_probe() -> None:
    assert image_scenario(menu(2001, "Image > Adjustments > Invert"), "icon") is not None


def test_only_filters_and_adjustments_get_image_probes() -> None:
    assert image_scenario(menu(10, "File > New"), "chart") is None


def test_neural_filters_never_get_an_image_probe_since_some_send_the_image_to_adobe() -> None:
    assert image_scenario(menu(3002, "Filter > Neural Filters"), "chart") is None


def test_a_built_in_command_is_run_by_its_event_with_its_dialog_and_its_settings_recorded() -> None:
    spec = event_settings_scenario(menu(1180, "Filter > Blur > Gaussian Blur"), "gaussianBlur")

    assert spec is not None
    assert (spec.item_id, spec.family, spec.safety, spec.never_press) == (
        "menu:1180@settings",
        "event_settings",
        "run",
        FORBIDDEN,
    )
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("read_event_settings", "gaussianBlur"),
        ("record", "dialogs", "event_settings", "pixels"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )


def test_only_commands_that_get_image_probes_get_settings_probes() -> None:
    assert event_settings_scenario(menu(3002, "Filter > Neural Filters"), "neuralGallery") is None


def test_vanishing_point_draws_a_plane_on_the_chart_then_accepts_and_records_it() -> None:
    spec = workspace_scenario(menu(-493, "Filter > Vanishing Point"))

    assert spec is not None
    assert (spec.item_id, spec.family, spec.needs_input) == ("menu:-493@plane", "workspace_plane", True)
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("run_menu_command", -493, "plane"),
        ("record", "dialogs", "history", "pixels", "workspace"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )


def test_other_filters_get_no_workspace_probe_yet() -> None:
    assert workspace_scenario(menu(1180, "Filter > Blur > Gaussian Blur")) is None


MENU = {
    "Window > Layers",
    "Window > Options",
    "Type > Panels > Character Panel",
    "Plugins > Plugins Panel",
    "Filter > Parametric Filters",
}


def test_a_panel_is_opened_by_its_window_menu_item() -> None:
    assert panel_menu_path("panelid.static.layers", "Layers", MENU) == "Window > Layers"


def test_type_panels_are_opened_from_the_type_menu() -> None:
    assert panel_menu_path("panelid.static.textcharacter", "Character", MENU) == (
        "Type > Panels > Character Panel"
    )


def test_plugin_and_filter_panels_are_opened_from_their_own_menus() -> None:
    plugins = "panelid.dynamic.uxp/com.adobe.pluginspanel/pluginsPanel"
    parametric = "panelid.dynamic.uxp/com.adobe.photoshop-material-filters/substanceFilterPanel"
    assert panel_menu_path(plugins, "Plugins", MENU) == "Plugins > Plugins Panel"
    assert panel_menu_path(parametric, "Parametric Filters", MENU) == "Filter > Parametric Filters"


def test_the_options_bar_is_named_after_the_current_tool_but_is_window_options() -> None:
    assert panel_menu_path("panelid.static.options", "Marquee Options", MENU) == "Window > Options"


def test_a_panel_no_menu_opens_has_no_path() -> None:
    assert panel_menu_path("panelid.static.patchmatchfillpreview", "Preview", MENU) is None


def test_cloud_sharing_panels_are_held_back_like_other_cloud_features() -> None:
    share = Item("panel", "panel:x/sharesheet/review", "Share for Review", "Window > Share for Review", {})

    assert scenarios_for(share).safety == "needs_budget"

def test_a_catalogued_dialog_is_opened_on_the_chart_and_every_control_driven_then_cancelled() -> None:
    spec = controls_scenario(menu(1170, "Filter > Blur > Motion Blur"))

    assert spec is not None
    assert (spec.item_id, spec.family, spec.safety, spec.needs_input) == (
        "menu:1170@controls",
        "dialog_controls",
        "run",
        True,
    )
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("drive_dialog_controls", 1170, "Filter > Blur > Motion Blur"),
        ("record", "dialogs", "controls"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )


def test_a_dialog_whose_command_is_held_back_or_never_run_gets_no_control_spec() -> None:
    held_back = [menu(1, "File > Save a Copy"), menu(2, "File > Export > Send to Firefly Boards")]

    assert [controls_scenario(item) for item in held_back] == [None, None]
    assert controls_scenario(menu(3, "Filter > Blur > Motion Blur")).item_id == "menu:3@controls"


def test_ai_features_and_file_browsers_are_opened_elsewhere_but_their_controls_never_driven() -> None:
    paths = [
        "Edit > Generate Image",
        "Filter > Neural Filters",
        "Filter > AI Denoise",
        "Edit > Sky Replacement",
        "Edit > Reflection Removal",
        "Select > Subject",
        "Layer > Mask All Objects",
        "Layer > Video Layers > New Video Layer from File",
        "Filter > Camera Raw Filter",  # generative remove, AI denoise
        "Select > Select and Mask",  # Select Subject can run in the cloud
    ]

    assert [controls_scenario(menu(n, p)) for n, p in enumerate(paths)] == [None] * len(paths)
    assert controls_scenario(menu(99, "Filter > Blur > Gaussian Blur")).item_id == "menu:99@controls"


def test_a_file_dialog_is_driven_only_in_the_sandbox_on_a_scratch_document_saved_there() -> None:
    file_info = menu(1300, "File > File Info")

    spec = controls_scenario(file_info, sandbox=True)

    assert (controls_scenario(file_info), spec.item_id, spec.family) == (None, "menu:1300@controls", "dialog_controls_sandboxed")
    assert spec.steps == (
        ("require_only_harness_documents",),
        ("new_throwaway_document",),
        ("save_throwaway_to_sandbox",),
        ("snapshot_documents",),
        ("drive_dialog_controls", 1300, "File > File Info", "sandbox"),
        ("record", "dialogs", "controls", "sandbox_files"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    )


def test_quitting_sending_and_ai_dialogs_are_not_driven_even_in_the_sandbox() -> None:
    paths = ["File > Exit", "File > Export > Send to Firefly Boards", "Edit > Generate Image", "Help > Photoshop Help"]

    assert [controls_scenario(menu(n, p), sandbox=True) for n, p in enumerate(paths)] == [None] * 4
    assert controls_scenario(menu(9, "File > Place Linked"), sandbox=True).family == "dialog_controls_sandboxed"
