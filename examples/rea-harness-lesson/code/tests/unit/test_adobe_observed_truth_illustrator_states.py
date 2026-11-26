"""Illustrator document states built on the fixture, and the declined commands retried in each."""

from __future__ import annotations

import json

from scripts.adobe_observed_truth.families import ScenarioSpec
from scripts.adobe_observed_truth.illustrator_states import STATES, retry_in_states

STEPS = (("new_fixture",), ("run_menu_command", "Live DropShadow2"), ("record", "dialogs", "document"),
         ("cancel_dialogs",), ("close_throwaway_document",))


def _result(item_id: str, status: str) -> str:
    return json.dumps({"item_id": item_id, "status": status})


def test_the_states_cover_the_kinds_of_art_selections_and_documents_commands_need() -> None:
    art = {"raster", "clipping", "compound", "symbol", "text_on_path", "area_text", "gradient", "pattern",
           "opacity", "blend", "live_paint"}
    document = {"two_artboards", "two_layers", "locked_hidden", "cmyk"}
    selection = {"nothing_selected", "one_path", "text_only"}
    assert art | document | selection == set(STATES)
    assert all(script.rstrip().endswith("return q('ok');") for script in STATES.values())


def test_a_command_illustrator_declined_is_tried_again_in_every_state_and_nothing_else_is() -> None:
    specs = [ScenarioSpec("menu:Live DropShadow2", "menu_command", "run", False, STEPS),
             ScenarioSpec("menu:group", "menu_command", "run", False, STEPS)]
    results = [_result("menu:Live DropShadow2", "refused"), _result("menu:group", "ok")]

    retries = retry_in_states(results, specs)

    # The symbol and text-on-path states crashed Illustrator under three different commands each
    # (2026-11-25).
    assert [s.item_id for s in retries] == [f"menu:Live DropShadow2@{state}" for state in STATES
                                            if state not in ("symbol", "text_on_path")]
    # Window and panel commands do not act on the art, so no state can change their answer, and
    # retrying them crashed Illustrator (arrangeicon, bringAllToFront; 2026-11-25).
    windows = [ScenarioSpec("menu:arrangeicon", "menu_command", "run", False, STEPS)]
    assert retry_in_states([_result("menu:arrangeicon", "refused")], windows) == []
    # Photoshop's filters, run through Illustrator's adapter, need a raster image; retried in every
    # state they crashed Illustrator every 10 to 25 runs (2026-11-25).
    adapter = [ScenarioSpec("menu:PSAdapter_plugin_NTSC", "menu_command", "run", False, STEPS),
               ScenarioSpec("menu:Live PSAdapter_plugin_USMk", "menu_command", "run", False, STEPS)]
    in_raster = retry_in_states([_result(s.item_id, "refused") for s in adapter], adapter)
    assert [s.item_id for s in in_raster] == ["menu:PSAdapter_plugin_NTSC@raster", "menu:Live PSAdapter_plugin_USMk@raster"]
    raster = next(s for s in retries if s.item_id.endswith("@raster"))
    assert raster.family == "state_retry"
    assert raster.steps == (("new_fixture",), ("build_state", "raster"), *STEPS[1:])
