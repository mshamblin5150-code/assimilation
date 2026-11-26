"""One sheet per swept live effect: whether its defaults repeat, and per setting what each value left
and whether it differs from the defaults."""

from __future__ import annotations

from scripts.adobe_observed_truth.illustrator_effects import Effect, effect_sheets

_EFFECT = Effect("Adobe Example", "Live Example", "rect", {"size": ("R", 10), "count": ("I", 4)},
                 {"size": [0, 20], "count": [1]})


def _row(label: str, points: int, area: float, status: str = "ok") -> dict:
    return {"item_id": f"effect:Adobe Example@{label}", "status": status,
            "observations": {"effect": {"error": "", "items": 1, "points": points, "area": area, "bounds": [0, 1, 1, 0]}}}


def test_a_sheet_says_which_values_changed_the_result_and_whether_the_defaults_repeat() -> None:
    rows = [_row("defaults", 8, 100), _row("defaults-again", 8, 100), _row("size=0", 4, 50), _row("size=20", 8, 100),
            _row("size=1000000", 8, 900), _row("count=1", 8, 100)]

    [sheet] = effect_sheets([_EFFECT], rows)

    assert sheet["effect"] == "Adobe Example" and sheet["menu"] == "Live Example"
    assert sheet["repeatable"] is True
    size = sheet["settings"]["size"]
    assert (size["type"], size["default"]) == ("R", 10)
    assert [(v["value"], v["changed"]) for v in size["values"]] == [(0, True), (20, False), (1000000, True)]
    assert sheet["settings"]["count"]["acts"] is False and size["acts"] is True


def test_a_random_effect_is_not_repeatable_and_its_changes_are_not_claimed() -> None:
    rows = [_row("defaults", 8, 100), _row("defaults-again", 9, 101), _row("size=0", 4, 50)]

    [sheet] = effect_sheets([_EFFECT], rows)

    assert sheet["repeatable"] is False
    assert sheet["settings"]["size"]["values"][0]["changed"] is None  # unknowable: the defaults vary run to run
