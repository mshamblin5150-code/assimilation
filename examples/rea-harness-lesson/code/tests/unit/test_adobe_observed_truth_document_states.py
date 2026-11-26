"""Commands Photoshop refuses on the flat chart (Smart Objects with no smart object, Type with no
text layer, Merge Down with one layer) are tried again in document states built from the chart."""

from __future__ import annotations

import json

from scripts.adobe_observed_truth.document_states import (
    FEATURE_STATES,
    STATES,
    plan_feature_states,
    plan_states,
    retry_in_states,
    state_baselines,
)
from scripts.adobe_observed_truth.families import ScenarioSpec

CHART_RUN = (("open_test_image", "chart"), ("run_menu_command", 3101), ("record", "dialogs", "history", "document"),
             ("cancel_dialogs",), ("close_throwaway_document",))


def _spec(item_id: str, family: str = "menu_command", steps=CHART_RUN) -> ScenarioSpec:
    return ScenarioSpec(item_id, family, "run", False, steps)


def _result(item_id: str, status: str, error: str | None = None) -> str:
    return json.dumps({"item_id": item_id, "status": status, "error": error})


def test_a_command_refused_on_the_flat_chart_is_tried_once_in_every_document_state() -> None:
    specs = [_spec("menu:3101"), _spec("menu:3102"), _spec("menu:3103")]
    results = [
        _result("menu:3101", "refused", 'The command "Edit Contents" is not currently available'),
        _result("menu:3102", "ok"),
        _result("menu:3103", "failed", "TimeoutError: ..."),  # a fault, not Photoshop declining
    ]

    retries = retry_in_states(results, specs)

    assert [s.item_id for s in retries] == [f"menu:3101@{state}" for state in STATES]
    smart = next(s for s in retries if s.item_id == "menu:3101@smart_object")
    assert smart.family == "state_retry" and smart.safety == "run"
    assert smart.steps == (("open_test_image", "chart"), ("build_state", "smart_object"), *CHART_RUN[1:])


def test_ai_and_cloud_tools_are_never_tried_in_any_state() -> None:
    # Neural Filters, generative Remove and Prompt to Edit were refused on the flat chart; a state
    # could let them run, and they are never used (caught before pass B ran, 2026-11-24).
    ai = ["tool:neuralGalleryTool", "tool:removeBrushTool", "tool:promptToEditTextMarkupTool"]
    specs = [_spec(i, "tool_select") for i in ai]
    results = [_result(i, "refused", "not currently available") for i in ai]

    assert retry_in_states(results, specs) == []
    assert plan_states([_result(i, "ok") for i in ai], specs) == []


def test_the_latest_result_counts_and_specs_without_the_chart_are_not_retried() -> None:
    panel = _spec("panel:layers", "panel_open", (("snapshot_panels",), ("show_panel", "layers")))
    specs = [_spec("menu:3101"), panel]
    results = [
        _result("menu:3101", "refused", "not currently available"),
        _result("menu:3101", "ok"),  # ran on a later try
        _result("panel:layers", "refused", "not currently available"),
    ]

    assert retry_in_states(results, specs) == []


def test_the_states_cover_what_photoshop_commands_need_on_the_canvas() -> None:
    layer_kinds = {"smart_object", "text", "shape", "path", "mask", "adjustment", "group", "layered",
                   "background", "clipping", "layer_style", "artboard", "video"}
    selections_and_channels = {"selection", "alpha_channel", "quick_mask"}
    image_modes = {"bits16", "bits32", "cmyk", "lab", "grayscale", "indexed", "bitmap"}
    documents = {"second_document"}
    assert layer_kinds | selections_and_channels | image_modes | documents == set(STATES)
    assert all(script.rstrip().endswith('"null";') for script in STATES.values())  # js() reads JSON back


def test_every_chart_spec_runs_in_every_state_after_the_refusals_are_retried() -> None:
    """Commands that run on the flat chart take other paths on other layers (a filter on a smart
    object is a smart filter): the whole matrix runs, refusals first. Tools are used on the
    canvas in their own pass, so selecting one is not repeated here."""
    tool = _spec("tool:paintbrushTool", "tool_shortcut", (("open_test_image", "chart"), ("press", "B")))
    specs = [_spec("menu:3101"), _spec("menu:3102"), tool]
    results = [_result("menu:3101", "ok"), _result("menu:3102", "refused", "not currently available")]

    planned = plan_states(results, specs)

    ids = [s.item_id for s in planned]
    assert ids == [f"menu:3102@{s}" for s in STATES] + [f"menu:3101@{s}" for s in STATES]


def test_each_state_is_also_built_alone_so_a_features_own_effect_can_be_told_from_the_states() -> None:
    # Measured against the chart, a tool used in CMYK showed 78% changed: mostly the conversion.
    baselines = state_baselines()

    assert [s.item_id for s in baselines] == [f"state:{state}" for state in STATES]
    assert baselines[0].steps == (("open_test_image", "chart"), ("build_state", next(iter(STATES))),
                                  ("record", "history", "pixels"), ("close_throwaway_document",))


def test_the_trimmed_pass_runs_each_filter_adjustment_and_fill_once_in_the_states_that_change_it() -> None:
    """Rebuilding a feature needs the states that change what it does (a filter on a smart object
    is a smart filter; 16- and 32-bit and CMYK take other pixel paths; a selection or mask limits
    it), not all 24. Only the feature's own command runs, once per state; its per-choice and
    control variants ran on the chart. Refusals were already retried in every state, and the
    previous-filter repeat, AI and cloud filters are left out."""
    paths = {"menu:1": "Filter > Blur > Gaussian Blur...", "menu:2": "Image > Adjustments > Levels...",
             "menu:3": "Edit > Fill...", "menu:4": "Layer > New Fill Layer > Solid Color...",
             "menu:5": "Image > Image Size...", "menu:6": "Filter > Last Filter", "menu:7": "Filter > Neural Filters...",
             "menu:8": "Filter > Noise > Add Noise..."}
    applied = (("open_test_image", "chart"), ("run_menu_command", 1, "accept"), ("record", "dialogs", "history", "pixels"),
               ("cancel_dialogs",), ("close_throwaway_document",))
    specs = [_spec(i) for i in paths] + [_spec("menu:1@controls", "dialog_controls"),
                                         _spec("menu:1@chart", "image_effect", applied),
                                         _spec("menu:1@icon", "image_effect", applied)]
    results = [_result(i, "ok") for i in paths if i != "menu:8"] + [_result("menu:8", "refused", "not available")]

    planned = plan_feature_states(results, specs, paths)

    assert FEATURE_STATES == ("smart_object", "selection", "mask", "bits16", "bits32", "cmyk")
    # A command with a dialog is applied with its defaults (its chart effect), not opened and cancelled.
    assert [s.item_id for s in planned] == [f"{i}@{state}" for i in ("menu:1@chart", "menu:2", "menu:3", "menu:4")
                                            for state in FEATURE_STATES]
    assert planned[0].steps == (applied[0], ("build_state", "smart_object"), *applied[1:])
