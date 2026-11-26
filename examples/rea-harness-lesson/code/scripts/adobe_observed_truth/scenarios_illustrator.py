"""Observed Illustrator behaviours. Each scenario drives Illustrator 2026 and returns
observation_record arguments. Coordinates are milli-points (mpt), y up; zoom is ppm."""

from __future__ import annotations

import time
from pathlib import Path
from fractions import Fraction
from typing import Any

from . import win_input
from .illustrator import (
    DIRECT_SELECTION_TOOL,
    Identity,
    Illustrator,
    canvas_rect,
    device_pixels_per_point,
    document_to_screen,
    selected_anchor_indices,
)
from .input_plan import click
from .scenarios import Spec


def _canvas_check(identity: Identity, view: dict[str, Any]) -> tuple[dict[str, Any], Fraction]:
    """Locate the drawing area, calibrate pixels per point, and check the canvas height."""
    win_input.make_dpi_aware()
    canvas = canvas_rect(identity.hwnd)
    scale = device_pixels_per_point(
        view_bounds_mpt=tuple(view["bounds_mpt"]), zoom_ppm=view["zoom_ppm"], canvas=canvas
    )
    bounds = view["bounds_mpt"]
    predicted_height = (bounds[1] - bounds[3]) * view["zoom_ppm"] * scale / 1_000_000_000
    record = {
        "rect_px": list(canvas),
        # The exact calibration carries milli-point rounding noise; thousandths suffice.
        "device_pixels_per_point_milli": round(scale * 1000),
        # Width calibrates the scale; the height is an independent check of the canvas choice.
        "height_residual_px": round((canvas[3] - canvas[1]) - predicted_height),
    }
    return record, scale


def illustrator_readback_check(ai: Illustrator, identity: Identity, out_dir: Path) -> dict[str, Any]:
    document = ai.new_document("readback-check")
    try:
        created = ai.create_fixture_path(document)
        selection_after_create = ai.selection(document)
        geometry = ai.geometry(document)
        view = ai.view(document)
        canvas, _ = _canvas_check(identity, view)
        ai.select_anchors(document, [0, 2])
        selected_path = ai.path_item(document)
        selection_after_select = ai.selection(document)
    finally:
        ai.close_throwaway_document(document)
    return {
        "operation": "observe_illustrator_readback",
        "parameters": {
            "behaviour_id": "illustrator_adapter_readback",
            "fixture_relative_to_artboard_top_left_mpt": {
                "anchors": [[100_000, -200_000], [200_000, -100_000], [300_000, -200_000]],
                "smooth_anchor_1_handles": [[150_000, -100_000], [250_000, -100_000]],
            },
            "script_selected_anchor_indices": [0, 2],
        },
        "observed": {
            "document_name": document,
            "geometry": geometry,
            "view": view,
            "canvas": canvas,
            "fixture_as_created": created,
            "selection_after_create": selection_after_create,
            "after_script_selection": {
                "path": selected_path,
                "selected_anchor_indices": selected_anchor_indices(selected_path["points"]),
                "selection": selection_after_select,
            },
        },
        "limitations": [
            "All edits and selections were made by script; no UI input was used.",
            "The canvas rectangle comes from window topology; only its consistency with the "
            "view's reported bounds is checked, not where clicks land.",
        ],
    }


def illustrator_shift_click_anchors(
    ai: Illustrator, identity: Identity, out_dir: Path
) -> dict[str, Any]:
    # (label, fixture anchor index, held keys)
    steps = [
        ("click", 0, ()),
        ("shift-click", 2, ("shift",)),
        ("shift-click-again", 2, ("shift",)),
        ("ctrl-click", 1, ("ctrl",)),
    ]
    document = ai.new_document("shift-click-anchors")
    observed_steps = []
    try:
        fixture = ai.create_fixture_path(document)
        geometry = ai.geometry(document)
        artboard = geometry["artboard_rects_mpt"][geometry["active_artboard_index"]]
        center = ((artboard[0] + artboard[2]) // 2, (artboard[1] + artboard[3]) // 2)
        ai.set_view(document, center_mpt=center, zoom_ppm=1_000_000)
        ai.select_tool(DIRECT_SELECTION_TOOL)
        view = ai.view(document)
        win_input.focus(identity.hwnd, identity.pid)
        canvas, scale = _canvas_check(identity, view)
        for label, index, hold in steps:
            anchor = fixture["points"][index]["anchor"]
            target = document_to_screen(
                tuple(anchor),
                center_mpt=tuple(view["center_mpt"]),
                zoom_ppm=view["zoom_ppm"],
                canvas=tuple(canvas["rect_px"]),
                device_pixels_per_point=scale,
            )
            win_input.perform(click(target, hold=hold), pid=identity.pid)
            time.sleep(0.5)
            path = ai.path_item(document)
            observed_steps.append(
                {
                    "label": label,
                    "anchor_index": index,
                    "held_keys": list(hold),
                    "screen_point_px": list(target),
                    "selected_anchor_indices": selected_anchor_indices(path["points"]),
                    "point_selection_states": [point["selected"] for point in path["points"]],
                    "path_selected": path["selected"],
                    "selection": ai.selection(document),
                }
            )
    finally:
        ai.close_throwaway_document(document)
    return {
        "operation": "observe_illustrator_shift_click_anchors",
        "parameters": {
            "behaviour_id": "illustrator_direct_selection_anchor_modifiers",
            "tool": DIRECT_SELECTION_TOOL,
            "zoom_ppm": 1_000_000,
            "steps": [
                {"label": label, "anchor_index": index, "held_keys": list(hold)}
                for label, index, hold in steps
            ],
        },
        "observed": {
            "document_name": document,
            "fixture": fixture,
            "view": view,
            "canvas": canvas,
            "steps": observed_steps,
        },
        "limitations": [
            "Interpret later steps only if the first plain click selected exactly anchor 0; "
            "otherwise the document-to-screen mapping missed.",
            "Mapping assumes the view centre is drawn at the canvas window's centre and the "
            "drawing area is the largest OS_ViewContainer inside OWL.Document.",
            "Ctrl may switch Direct Selection to the last-used Selection tool while held; the "
            "active tool after the step is not read.",
            "Illustrator scripting cannot read the active tool, so the user's tool is not "
            "restored; Direct Selection stays active afterwards.",
        ],
    }


SCENARIOS: dict[str, Spec] = {
    "illustrator_readback_check": Spec(illustrator_readback_check, needs_input=False),
    "illustrator_shift_click_anchors": Spec(illustrator_shift_click_anchors, needs_input=True),
}
