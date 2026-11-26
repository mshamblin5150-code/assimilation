"""Painting, fill and selection behaviours observed through exported pixels. No UI input."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import ps_pixels as px
from . import ps_tools as tools
from .photoshop import Identity, Photoshop, dialogs_off
from .scenarios import Spec


FILL_LAYER = "observed-truth-fill"
_SCRIPTED = (
    "The tool was applied by its scripted ActionManager/DOM event (work-path stroke for brush and "
    "eraser, the Fill event with a From point for the bucket), not by mouse input; pointer "
    "dynamics, smoothing and the options bar UI were not exercised."
)
_COLOUR = (
    "Pixel values are document values read from a PNG copy; colour management and display "
    "rendering are not observed."
)


@contextmanager
def _fixture(ps: Photoshop, name: str, width: int, height: int, used: Sequence[str]) -> Iterator[dict[str, Any]]:
    """A throwaway document with dialogs off and the user's tool state snapshotted and restored."""
    with dialogs_off(ps):
        ps.new_document(name, width, height)
        try:
            with tools.preserved_tool_state(ps, used) as state:
                state["fixture"] = px.document_facts(ps)
                yield state
        finally:
            ps.close_throwaway_document()


def _limitations(state: dict[str, Any], *extra: str) -> list[str]:
    fixture = state["fixture"]
    notes = [
        _SCRIPTED,
        _COLOUR,
        f"Fixture: {fixture['mode']}, {fixture['bits_per_channel']}, profile {fixture['colour_profile']}, "
        f"{fixture['resolution_ppi']} ppi.",
        *extra,
    ]
    if not tools.all_restored(state["restored"]):
        notes.append(f"The user's tool state did not read back identical after restore: {state['restored']}.")
    return notes


def _add_filled_layer(ps: Photoshop, name: str, rgb: Sequence[int]) -> None:
    ps.js(
        f"var d=app.activeDocument,l=d.artLayers.add();l.name={json.dumps(name)};d.selection.selectAll();"
        f"var c=new SolidColor();c.rgb.red={rgb[0]};c.rgb.green={rgb[1]};c.rgb.blue={rgb[2]};"
        'd.selection.fill(c);d.selection.deselect();"null";'
    )


def _select_rect(ps: Photoshop, box: Sequence[int]) -> None:
    left, top, right, bottom = box
    ps.js(
        f"app.activeDocument.selection.select([[{left},{top}],[{right},{top}],[{right},{bottom}],[{left},{bottom}]],"
        'SelectionType.REPLACE,0,false);"null";'
    )


def _history_index(ps: Photoshop) -> int:
    return ps.history()["active_index"]


def _revert_to(ps: Photoshop, index: int) -> None:
    ps.js(f"var d=app.activeDocument;d.activeHistoryState=d.historyStates[{index}];'null';")


def _eraser_brush_mode(ps: Photoshop) -> tuple[int, dict[str, str]]:
    """Find the ErsB value whose soft (hardness 0) dab is soft, i.e. Brush mode, by looking at pixels."""
    shapes = {}
    for mode in (0, 1, 2):
        mark = _history_index(ps)
        _add_filled_layer(ps, "observed-truth-probe", (0, 0, 0))
        tools.set_brush_options(ps, "eraser", size_px=21, hardness=0, opacity=100, flow=100, spacing=25, eraser_mode=mode)
        tools.stroke(ps, "eraser", [(30, 30)])
        erased = 255 - px.export_layer(ps, "observed-truth-probe")[:61, :61, 3]
        shapes[str(mode)] = px.dab_shape(erased)
        _revert_to(ps, mark)
    soft = [int(mode) for mode, shape in shapes.items() if shape == "soft"]
    if len(soft) != 1:
        raise RuntimeError(f"Could not identify the eraser's Brush mode from dab shapes: {shapes}")
    return soft[0], shapes


def eraser_opacity(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    size = 40
    with _fixture(ps, "eraser-opacity", 400, 300, ["eraser"]) as state:
        tools.set_colours(ps, foreground=(0, 0, 0), background=(0, 0, 255))
        brush_mode, mode_shapes = _eraser_brush_mode(ps)
        _add_filled_layer(ps, FILL_LAYER, (255, 0, 0))

        def erase(opacity: int, points: list[tuple[int, int]]) -> dict[str, Any]:
            options = tools.set_brush_options(
                ps, "eraser", size_px=size, hardness=100, opacity=opacity, flow=100, spacing=25, eraser_mode=brush_mode
            )
            tools.stroke(ps, "eraser", points)
            return options

        options = {}
        single = {100: (50, 50), 50: (150, 50), 25: (250, 50)}
        for opacity, point in single.items():
            options[str(opacity)] = erase(opacity, [point])
        double = {50: (150, 150), 25: (250, 150)}
        for opacity, point in double.items():
            erase(opacity, [point])
            erase(opacity, [point])
        erase(50, [(20, 250), (180, 250)])  # one stroke whose dabs overlap
        alpha = px.export_layer(ps, FILL_LAYER)[..., 3]

        background = ps.js("q(app.activeDocument.backgroundLayer.name);")
        ps.js("var d=app.activeDocument;d.activeLayer=d.backgroundLayer;'null';")
        for opacity, point in ((100, (300, 250)), (50, (370, 250))):
            erase(opacity, [point])
        background_rgba = px.export_layer(ps, background)
        history = ps.history()

    def box(x: int, y: int) -> list[int]:
        return [x - 2, y - 2, x + 3, y + 3]

    return {
        "operation": "observe_eraser_opacity",
        "parameters": {
            "behaviour_id": "eraser_opacity",
            "eraser": {"size_px": size, "hardness": 100, "flow": 100, "spacing": 25},
            "single_pass_opacities": sorted(single),
            "two_pass_opacities": sorted(double),
            "layer_fill_rgb": [255, 0, 0],
            "background_colour_rgb": [0, 0, 255],
        },
        "observed": {
            "fixture": state["fixture"],
            "eraser_mode_dab_shapes": mode_shapes,
            "eraser_brush_mode_value": brush_mode,
            "options_read_back": options,
            "single_pass_alpha_at_centre": {str(o): int(alpha[y, x]) for o, (x, y) in single.items()},
            "single_pass_centre_5x5": {str(o): px.region_stats(alpha, box(x, y)) for o, (x, y) in single.items()},
            "two_pass_alpha_at_centre": {str(o): int(alpha[y, x]) for o, (x, y) in double.items()},
            "one_stroke_overlapping_dabs_opacity_50_alpha_at_midpoint": int(alpha[250, 100]),
            "untouched_alpha": int(alpha[290, 390]),
            "background_layer_rgba_at_centre": {
                "100": [int(v) for v in background_rgba[250, 300]],
                "50": [int(v) for v in background_rgba[250, 370]],
            },
            "history_state_names": [s["name"] for s in history["states"]],
            "tool_state_restored": state["restored"],
        },
        "limitations": _limitations(
            state,
            "Eraser mode was identified by dab shape (soft dab at hardness 0), not by a documented ErsB mapping.",
            "Each pass is a separate one-anchor stroke; the overlap case is one two-anchor stroke.",
        ),
    }


def paint_bucket_unenclosed(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    # Black 4 px outlines on white. Outer boxes are [left, top, right, bottom).
    shapes = {
        "enclosed_ring": {"outer": [120, 20, 180, 80], "gap": None, "seed": (150, 50)},
        "c_shape_gap_on_right": {"outer": [20, 20, 80, 80], "gap": [76, 44, 80, 56], "seed": (50, 50)},
        "u_shape_open_to_canvas_bottom": {"outer": [110, 120, 190, 200], "gap": None, "seed": (150, 170)},
    }
    with _fixture(ps, "bucket-unenclosed", 200, 200, ["bucket"]) as state:
        tools.set_colours(ps, foreground=(0, 0, 0))
        for shape in shapes.values():
            left, top, right, bottom = shape["outer"]
            _select_rect(ps, shape["outer"])
            ps.js("app.activeDocument.selection.fill(app.foregroundColor);'null';")
            inner_bottom = bottom if bottom == 200 else bottom - 4
            _select_rect(ps, [left + 4, top + 4, right - 4, inner_bottom])
            ps.js("app.activeDocument.selection.fill(app.backgroundColor);'null';")
            if shape["gap"]:
                _select_rect(ps, shape["gap"])
                ps.js("app.activeDocument.selection.fill(app.backgroundColor);'null';")
        ps.js("app.activeDocument.selection.deselect();'null';")
        tools.set_colours(ps, foreground=(255, 0, 0))
        options = tools.set_bucket_options(ps, tolerance=0, anti_alias=False, contiguous=True, all_layers=False)
        before = px.export_composite(ps)
        mark = _history_index(ps)
        fills = {}
        for name, shape in shapes.items():
            tools.bucket_fill(ps, *shape["seed"], options)
            changed = px.changed_mask(before, px.export_composite(ps))
            fills[name] = {
                "pixels_changed": int(changed.sum()),
                "changed_bounds": px.nonzero_bounds(changed),
                "edges_touched": px.edges_touched(changed),
                "outside_probe_changed": bool(changed[195, 5]),
            }
            _revert_to(ps, mark)
    return {
        "operation": "observe_paint_bucket_unenclosed",
        "parameters": {
            "behaviour_id": "paint_bucket_unenclosed_area",
            "bucket": {"tolerance": 0, "anti_alias": False, "contiguous": True, "all_layers": False},
            "shapes": {n: {"outer": s["outer"], "gap": s["gap"], "seed": list(s["seed"])} for n, s in shapes.items()},
            "outline_px": 4,
            "fill_rgb": [255, 0, 0],
        },
        "observed": {
            "fixture": state["fixture"],
            "options_read_back": options,
            "fills": fills,
            "tool_state_restored": state["restored"],
        },
        "limitations": _limitations(
            state,
            "Shapes were drawn with aliased selection fills on the Background layer; each fill was undone "
            "by History before the next.",
            "BckS is taken to be 'All Layers' from its position in the options descriptor; the single-layer "
            "fixture does not exercise it.",
        ),
    }


def brush_hardness_falloff(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    size, centre, radii = 100, (150, 150), list(range(0, 101, 5))
    results, options = {}, {}
    with _fixture(ps, "brush-falloff", 300, 300, ["brush"]) as state:
        tools.set_colours(ps, foreground=(0, 0, 0))
        for hardness in (0, 50, 100):
            layer = f"observed-truth-hardness-{hardness}"
            ps.js(f"var l=app.activeDocument.artLayers.add();l.name={json.dumps(layer)};'null';")
            options[str(hardness)] = tools.set_brush_options(
                ps, "brush", size_px=size, hardness=hardness, opacity=100, flow=100, spacing=25
            )
            tools.stroke(ps, "brush", [centre])
            alpha = px.export_layer(ps, layer)[..., 3]
            results[str(hardness)] = {
                "alpha_by_radius": dict(zip((str(r) for r in radii), px.radial_profile(alpha, centre, radii))),
                "zero_radius_px": px.zero_radius(alpha, centre),
                "covered_bounds": px.nonzero_bounds(alpha),
            }
            ps.js("app.activeDocument.activeLayer.visible=false;'null';")
    return {
        "operation": "observe_brush_hardness_falloff",
        "parameters": {
            "behaviour_id": "brush_hardness_falloff_within_size",
            "brush": {"size_px": size, "opacity": 100, "flow": 100, "spacing": 25},
            "hardness": [0, 50, 100],
            "dab_centre_pixel": list(centre),
            "radii_px": radii,
        },
        "observed": {
            "fixture": state["fixture"],
            "nominal_radius_px": size // 2,
            "options_read_back": options,
            "profiles": results,
            "tool_state_restored": state["restored"],
        },
        "limitations": _limitations(
            state,
            "A dab is a one-anchor work-path stroke with simulated pressure off; tip dynamics were switched off.",
            "Profiles are the mean of the four axis samples at each radius from the dab's centre pixel.",
        ),
    }


def selection_offcanvas_roundtrip(ps: Photoshop, identity: Identity, out_dir: Path) -> dict[str, Any]:
    shapes = ("rectangle", "ellipse")
    box = [40, 40, 120, 100]
    offsets = {"partly_off": (120, 0), "fully_off": (300, 0)}
    cases = {}
    with _fixture(ps, "selection-offcanvas", 200, 200, []) as state:
        for shape in shapes:
            for label, (dx, dy) in offsets.items():
                _make_selection(ps, shape, box)
                start, start_report = px.export_selection_mask(ps)
                start_bounds = _selection_bounds(ps)
                _translate_selection(ps, dx, dy)
                moved, _ = px.export_selection_mask(ps)
                moved_bounds = _selection_bounds(ps)
                _translate_selection(ps, -dx, -dy)
                back, _ = px.export_selection_mask(ps)
                cases[f"{shape}_{label}"] = {
                    "start_bounds": start_bounds,
                    "moved_bounds": moved_bounds,
                    "moved_mask_bounds": px.nonzero_bounds(moved),
                    "returned_bounds": _selection_bounds(ps),
                    "start_mask_pixels": int((start > 0).sum()),
                    "returned_mask_pixels": int((back > 0).sum()),
                    "start_vs_returned": px.mask_difference(start, back),
                    "mask_export_history": start_report,
                }
    return {
        "operation": "observe_selection_offcanvas_roundtrip",
        "parameters": {
            "behaviour_id": "selection_moved_off_canvas_and_back",
            "canvas_px": [200, 200],
            "selection_box": box,
            "shapes": list(shapes),
            "offsets_px": {k: list(v) for k, v in offsets.items()},
        },
        "observed": {"fixture": state["fixture"], "cases": cases, "tool_state_restored": state["restored"]},
        "limitations": _limitations(
            state,
            "The selection boundary was moved with selection.translateBoundary, not by dragging.",
            "Masks are exported by filling the selection on a temporary layer; History is reverted after each export.",
        ),
    }


def _make_selection(ps: Photoshop, shape: str, box: Sequence[int]) -> None:
    if shape == "rectangle":
        _select_rect(ps, box)
        return
    left, top, right, bottom = box
    ps.js(
        "function cid(s){return charIDToTypeID(s);}"
        'var d=new ActionDescriptor(),r=new ActionReference();r.putProperty(cid("Chnl"),cid("fsel"));'
        'd.putReference(cid("null"),r);var e=new ActionDescriptor();'
        f'e.putUnitDouble(cid("Top "),cid("#Pxl"),{top});e.putUnitDouble(cid("Left"),cid("#Pxl"),{left});'
        f'e.putUnitDouble(cid("Btom"),cid("#Pxl"),{bottom});e.putUnitDouble(cid("Rght"),cid("#Pxl"),{right});'
        'd.putObject(cid("T   "),cid("Elps"),e);d.putBoolean(cid("AntA"),true);'
        'executeAction(cid("setd"),d,DialogModes.NO);"null";'
    )


def _translate_selection(ps: Photoshop, dx: int, dy: int) -> None:
    ps.js(f'app.activeDocument.selection.translateBoundary(UnitValue({dx},"px"),UnitValue({dy},"px"));"null";')


def _selection_bounds(ps: Photoshop) -> list[int] | None:
    return ps.js(
        "var b;try{b=app.activeDocument.selection.bounds;}catch(e){b=null;}"
        "b===null?'null':'['+Math.round(b[0].as('px'))+','+Math.round(b[1].as('px'))+','"
        "+Math.round(b[2].as('px'))+','+Math.round(b[3].as('px'))+']';"
    )


SCENARIOS: dict[str, Spec] = {
    "eraser_opacity": Spec(eraser_opacity, needs_input=False),
    "paint_bucket_unenclosed": Spec(paint_bucket_unenclosed, needs_input=False),
    "brush_hardness_falloff": Spec(brush_hardness_falloff, needs_input=False),
    "selection_offcanvas_roundtrip": Spec(selection_offcanvas_roundtrip, needs_input=False),
}
