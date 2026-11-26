"""The brush probe: scripted dabs and strokes with one brush setting changed at a time, measured
from the painted layer's transparency, so the brush engine can be rebuilt from numbers (the
hardness falloff, where dabs land for each spacing, how flow builds up under opacity)."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.brush_probe import CENTRE, ROW, brush_specs, measure, published_rows


def test_each_brush_setting_is_probed_alone_from_a_plain_round_brush() -> None:
    specs = {s.item_id: s for s in brush_specs()}

    dab = specs["brush:dab:size=21:hardness=50"]
    assert dab.family == "brush_probe" and dab.safety == "run" and not dab.needs_input
    assert dab.steps == (
        ("brush_canvas",),
        ("brush_stroke", {"size_px": 21, "hardness": 50, "opacity": 100, "flow": 100, "spacing": 25}, [list(CENTRE)]),
        ("record", "brush"),
        ("brush_restore",),
        ("close_throwaway_document",),
    )
    stroke = specs["brush:stroke:size=21:hardness=0:spacing=150"]
    assert stroke.steps[1][2] == [[40, ROW], [360, ROW]]
    # The falloff at every hardness, across sizes; spacing for a hard and a soft tip; flow and
    # opacity each alone; the smallest tips, where anti-aliasing decides the dab.
    assert {f"brush:dab:size={s}:hardness={h}" for s in (9, 21, 99) for h in (0, 10, 25, 50, 75, 90, 100)} <= set(specs)
    assert {f"brush:stroke:size=21:hardness={h}:spacing={p}" for h in (0, 100)
            for p in (1, 10, 25, 50, 100, 150, 200, 400)} <= set(specs)
    assert {f"brush:stroke:size=21:flow={f}" for f in (5, 10, 25, 50)} <= set(specs)
    assert {f"brush:stroke:size=21:opacity={o}" for o in (10, 25, 50)} <= set(specs)
    assert {f"brush:dab:size={s}:hardness=100" for s in (1, 2, 3, 5)} <= set(specs)


def test_simulated_pen_pressure_is_probed_on_size_and_opacity_each_and_together() -> None:
    specs = {s.item_id: s for s in brush_specs()}

    sized = specs["brush:pressure:size=99:controls=size"]
    assert sized.steps[1] == ("brush_stroke", {"size_px": 99, "hardness": 100, "opacity": 100, "flow": 100,
                                               "spacing": 25, "pressure": "size"}, [[40, ROW], [360, ROW]])
    assert {"brush:pressure:size=21:controls=size", "brush:pressure:size=21:controls=opacity",
            "brush:pressure:size=21:controls=both", "brush:pressure:size=21:hardness=0:controls=opacity"} <= set(specs)


def test_a_stroke_keeps_its_painted_width_at_every_column() -> None:
    alpha = np.zeros((300, 400), dtype=np.uint8)
    alpha[ROW - 2:ROW + 3, 100:200] = 255  # 5 rows wide over x 100..199
    alpha[ROW, 200:300] = 255  # 1 row wide over x 200..299

    found = measure(alpha, [(40, ROW), (360, ROW)], size=21)

    assert found["widths"][150] == 5 and found["widths"][250] == 1 and found["widths"][50] == 0


def test_a_dab_is_measured_as_its_falloff_from_the_centre() -> None:
    alpha = np.zeros((300, 400), dtype=np.uint8)
    y, x = np.ogrid[:300, :400]
    distance = np.hypot(x - CENTRE[0], y - CENTRE[1])
    alpha[...] = np.clip(255 - distance * 25, 0, 255).astype(np.uint8)  # a cone 10 px across

    found = measure(alpha, [CENTRE], size=21)

    assert found["radial"][:4] == [255, 230, 205, 180]
    assert found["zero_radius"] == 11
    assert "centreline" not in found


def test_a_stroke_is_measured_along_its_centre_line_and_across_it() -> None:
    alpha = np.zeros((300, 400), dtype=np.uint8)
    for centre in (100, 130, 160):  # three dabs 30 px apart, soft enough to dip between them
        for dx in range(-12, 13):
            alpha[ROW - 3:ROW + 4, centre + dx] = np.maximum(alpha[ROW - 3:ROW + 4, centre + dx], 200 - abs(dx) * 10)

    found = measure(alpha, [(100, ROW), (160, ROW)], size=21)

    assert found["dab_centres"] == [100, 130, 160]
    assert found["centreline"][100] == 200 and len(found["centreline"]) == 400
    assert found["cross_section"][ROW] == 200 and found["cross_section"][ROW + 4] == 0
    assert found["plateau"] == round(float(np.mean(alpha[ROW, 120:141])))  # the middle third


def test_the_dataset_gets_each_probes_latest_numbers_and_nothing_else() -> None:
    brush = {"options": {"size_px": 21}, "radial": [255, 0], "zero_radius": 1, "bounds": [0, 0, 1, 1]}
    results = [
        {"item_id": "brush:dab:size=21:hardness=50", "status": "refused", "error": "x", "observations": {}},
        {"item_id": "brush:dab:size=21:hardness=50", "status": "ok", "observations": {"brush": brush, "dialogs": []},
         "at": "2026-11-25T11:00:00"},
        {"item_id": "menu:1801", "status": "ok", "observations": {}},
    ]

    assert published_rows(results) == [{"item_id": "brush:dab:size=21:hardness=50", **brush}]
