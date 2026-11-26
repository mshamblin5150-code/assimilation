"""Illustrator's tools used on the fixture, each with the gesture its work needs."""

from __future__ import annotations

from scripts.adobe_observed_truth.illustrator_tools import gesture_for, tool_specs
from scripts.adobe_observed_truth.inventory import Item


def test_each_tool_gets_the_gesture_its_work_needs() -> None:
    assert gesture_for("Adobe Rectangle Shape Tool") == "drag"
    assert gesture_for("Adobe Rotate Tool") == "drag"
    assert gesture_for("Adobe Brush Tool") == "stroke"
    assert gesture_for("Adobe Width Tool") == "stroke"
    assert gesture_for("Adobe Shape Builder Tool") == "stroke"
    assert gesture_for("Adobe Symbol Sprayer Tool") == "stroke"
    assert gesture_for("Adobe Warp Tool") == "stroke"
    assert gesture_for("Adobe Pen Tool") == "polygon"
    assert gesture_for("Adobe Curvature Tool") == "polygon"
    assert gesture_for("Adobe Type Tool") == "type"
    assert gesture_for("Adobe Vertical Area Type Tool") == "type"
    assert gesture_for("Adobe Add Anchor Point Tool") == "click"
    assert gesture_for("Adobe Eyedropper Tool") == "click"
    assert gesture_for("Adobe Magic Wand Tool") == "click"
    # A cloud feature and print tiling are never used.
    assert gesture_for("CC Charts Tool") == "never" and gesture_for("Adobe Page Tool") == "never"


def test_a_tool_spec_selects_the_tool_by_name_uses_it_and_ends_what_it_started() -> None:
    tools = [Item("tool", "tool:Adobe Pen Tool", "Adobe Pen Tool", "Toolbar > Adobe Pen Tool", {"tool_id": "Adobe Pen Tool"}),
             Item("tool", "tool:CC Charts Tool", "CC Charts Tool", "Toolbar > CC Charts Tool", {"tool_id": "CC Charts Tool"})]

    [pen] = tool_specs(tools)

    assert (pen.item_id, pen.family, pen.safety) == ("tool:Adobe Pen Tool@use", "tool_use", "run")
    assert pen.needs_input
    assert pen.steps == (("new_fixture",), ("select_tool", "Adobe Pen Tool"), ("use_tool", "polygon", "escape"),
                         ("record", "dialogs", "document"), ("cancel_dialogs",), ("close_throwaway_document",))
