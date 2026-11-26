"""The adjustment probe's event scripts and specs."""

from __future__ import annotations

from scripts.adobe_observed_truth.adjust_probe import CASES, adjust_js, adjust_specs


def test_each_adjustment_runs_by_its_own_event_without_a_dialog() -> None:
    for kind, _name, params in CASES:
        script = adjust_js(kind, params)
        assert "executeAction(" in script and "DialogModes.NO" in script, kind


def test_curve_points_and_levels_inputs_reach_the_descriptor() -> None:
    assert "q.putDouble(charIDToTypeID('Hrzn'),128.0)" in adjust_js("curves", {"points": [(0, 0), (128, 160), (255, 255)]})
    assert "i.putInteger(50)" in adjust_js("levels", {"black": 50, "white": 255, "gamma": 1.0})
    assert len(adjust_specs()) == len(CASES)
