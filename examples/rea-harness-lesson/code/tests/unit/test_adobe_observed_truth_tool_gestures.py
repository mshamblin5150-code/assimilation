"""Every Photoshop tool used on the canvas, not just selected: stroked, dragged, clicked, drawn
as a path or typed into, on the chart and in every document state, then committed."""

from __future__ import annotations

from scripts.adobe_observed_truth.document_states import STATES
from scripts.adobe_observed_truth.input_plan import (
    KeyDown,
    MouseDown,
    MouseMove,
    MouseUp,
)
from scripts.adobe_observed_truth.inventory import Item
from scripts.adobe_observed_truth.tool_gestures import (
    gesture_events,
    gesture_for,
    tool_use_specs,
)


def _tool(name: str, tool_id: str, shortcut: str | None = None) -> Item:
    return Item("tool", f"tool:{tool_id}", name, f"Toolbar > {name}", {"tool_id": tool_id, "shortcut": shortcut})


def test_tools_get_the_gesture_their_work_needs() -> None:
    expect = {
        ("Brush Tool", "paintbrushTool"): "stroke",
        ("Color Replacement Tool", "colorReplacementBrushTool"): "stroke",
        ("Clone Stamp Tool", "cloneStampTool"): "source_stroke",
        ("Healing Brush Tool", "magicStampTool"): "source_stroke",
        ("Spot Healing Brush Tool", "spotHealingBrushTool"): "stroke",
        ("Magic Eraser Tool", "magicEraserTool"): "click",
        ("Background Eraser Tool", "backgroundEraserTool"): "stroke",
        ("Rectangular Marquee Tool", "marqueeRectTool"): "drag",
        ("Polygonal Lasso Tool", "polySelTool"): "polygon",
        ("Pen Tool", "penTool"): "polygon",
        ("Horizontal Type Tool", "typeCreateOrEditTool"): "type",
        ("Crop Tool", "cropTool"): "drag",
        ("Blur Tool", "blurTool"): "stroke",
        ("Blur Gallery", "BlurGalleryTool"): "workspace",  # its own workspace, driven there
        ("Sample in image to set black point", "blackPointTool"): "workspace",  # a Levels/Curves eyedropper
        ("Quick Selection Tool", "selectionLabSmartBrushTool"): "workspace",  # Select and Mask's
        ("Sampling Brush Tool", "neuralGalleryBrushTool"): "never",  # Neural Filters: AI, some on Adobe's servers
        ("Remove Tool", "removeTool"): "never",  # generative
        ("Rotate Object", "3DObjectRotateTool"): "never",
    }

    assert {key: gesture_for(*key) for key in expect} == expect


def to_screen(x: float, y: float) -> tuple[int, int]:
    return round(x) + 1000, round(y) + 500


def test_a_stroke_is_one_press_moving_through_the_chart_then_a_release() -> None:
    events = gesture_events("stroke", to_screen)

    assert events.count(MouseDown()) == 1 and events.count(MouseUp()) == 1
    moves = [e for e in events if isinstance(e, MouseMove)]
    assert len(moves) > 20 and all(1000 <= m.x <= 1600 and 500 <= m.y <= 900 for m in moves)


def test_a_source_stroke_alt_clicks_its_source_first() -> None:
    events = gesture_events("source_stroke", to_screen)

    assert events[:4] == [KeyDown("alt"), MouseMove(1150, 650), MouseDown(), MouseUp()]
    assert events.count(MouseDown()) == 2


def test_a_polygon_clicks_its_corners_and_closes_on_the_first() -> None:
    events = gesture_events("polygon", to_screen)

    assert events.count(MouseDown()) == 5
    presses = [events[i - 1] for i, e in enumerate(events) if e == MouseDown()]
    assert presses[0] == presses[-1]


def test_type_clicks_then_types_its_text() -> None:
    events = gesture_events("type", to_screen)

    assert events[:3] == [MouseMove(1060, 830), MouseDown(), MouseUp()]
    typed = "".join(e.key for e in events if isinstance(e, KeyDown))
    assert "observed" in typed.lower()


def test_each_tool_on_the_canvas_runs_on_the_chart_and_in_every_state_then_is_committed() -> None:
    crop = _tool("Crop Tool", "cropTool", "C")
    lens = _tool("Blur Gallery", "BlurGalleryTool")

    specs = tool_use_specs([crop, lens])

    assert [s.item_id for s in specs] == ["tool:cropTool@use"] + [f"tool:cropTool@use@{s}" for s in STATES]
    flat, smart = specs[0], specs[1 + list(STATES).index("smart_object")]
    assert flat.family == "tool_use" and flat.needs_input
    assert flat.steps == (
        ("open_test_image", "chart"),
        ("select_tool_by_script", "cropTool"),  # the tool itself: C selects whichever crop tool was last used
        ("use_tool", "drag", "enter"),
        ("record", "dialogs", "history", "pixels", "current_tool"),
        ("cancel_dialogs",),
        ("close_throwaway_document",),
    )
    assert smart.steps[:3] == (("open_test_image", "chart"), ("build_state", "smart_object"), ("select_tool_by_script", "cropTool"))
