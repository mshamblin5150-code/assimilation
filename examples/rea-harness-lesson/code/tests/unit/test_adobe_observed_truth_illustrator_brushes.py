"""The art and pattern brush probe's own art, paths and scripts."""

from __future__ import annotations

from scripts.adobe_observed_truth.illustrator_brushes import ARROW, KINDS, PATHS, apply_js, brush_specs, document_js, path_length


def test_the_arrow_is_drawn_filled_without_a_stroke_and_selected() -> None:
    script = document_js()
    assert "a.filled=true;a.stroked=false;" in script and "a.selected=true" in script
    assert script.count("],[") == len(ARROW) - 1


def test_every_test_path_is_brushed_expanded_and_the_document_closed() -> None:
    script = apply_js("Art Brush 1")
    assert all(f'"{name}"' in script for name in PATHS)
    assert "app.executeMenuCommand('expandStyle')" in script and "d.close(SaveOptions.DONOTSAVECHANGES)" in script


def test_each_brush_kind_has_a_spec_that_needs_input_and_the_paths_have_lengths() -> None:
    specs = brush_specs()
    assert {f"brush:{k}:defaults" for k in KINDS} <= {s.item_id for s in specs} and all(s.needs_input for s in specs)
    assert path_length("line") == 240 and path_length("corner") == 220


def test_scatter_brushes_and_the_tile_rounding_and_closed_square_paths_are_probed() -> None:
    assert "scatter" in KINDS and {"line_300", "line_330", "square"} <= set(PATHS)
    assert path_length("line_300") == 300 and path_length("line_330") == 330 and path_length("square") == 480
    assert "p.closed=true;" in apply_js("Scatter Brush 1")


def test_pattern_brush_option_specs_set_one_option_each_through_the_dialog() -> None:
    specs = {s.item_id: s for s in brush_specs()}
    assert {"brush:pattern:scale=50", "brush:pattern:spacing=25", "brush:pattern:fit=add_space", "brush:pattern:fit=approximate",
            "brush:pattern:flip_along"} <= set(specs)
    define = next(step for step in specs["brush:pattern:scale=50"].steps if step[0] == "define_brush")
    assert define == ("define_brush", "pattern", {"scale": 50})
