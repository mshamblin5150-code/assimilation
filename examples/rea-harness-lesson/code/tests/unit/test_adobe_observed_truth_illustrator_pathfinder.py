"""The Pathfinder probe's geometry and script."""

from __future__ import annotations

import math

from scripts.adobe_observed_truth.illustrator_pathfinder import COMMANDS, D, R, crossings, lens_area, pathfinder_js, pathfinder_specs


def test_the_lens_and_crossings_are_the_exact_circle_geometry() -> None:
    assert abs(lens_area() - 2236.48) < 0.01
    for x, y in crossings():
        assert abs(math.hypot(x - 100, y - 100) - R) < 1e-9 and abs(math.hypot(x - 100 - D, y - 100) - R) < 1e-9


def test_every_command_value_has_a_spec_and_the_script_closes_its_document() -> None:
    assert len(pathfinder_specs()) == len(COMMANDS)
    assert "I Command 5 " in pathfinder_js(5) and "doc.close(SaveOptions.DONOTSAVECHANGES)" in pathfinder_js(5)
