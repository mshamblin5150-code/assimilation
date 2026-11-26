"""One fact sheet per feature: enough to rebuild it. Its settings (with the range Photoshop
accepts and what each value does to the chart), what it does in the document states that change
it, the code that ran only for it and the code behind its dialog's controls."""

from __future__ import annotations

from scripts.adobe_observed_truth.fact_sheets import build_sheets

GAUSSIAN = {"id": "menu:-515", "kind": "menu_command", "name": "Gaussian Blur", "path": "Filter > Blur > Gaussian Blur",
            "facts": {"command": -515}}
RADIUS = {"key": "radius", "type": "unit", "unit": "pixelsUnit", "default": 1.0}


def _pixels(changed: float) -> dict:
    return {"image": "chart", "changed_fraction": changed, "changed_box": [0, 0, 599, 399],
            "mean_delta": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 0.0}, "regions": {"hard_edges": 0.7},
            "after_sha256": "ab"}


def _swept(name: str, value, used, changed: float, status: str = "ok") -> dict:
    overrides = {} if value is None else {"radius": value}
    return {"item_id": f"sweep:gaussianBlur:{name}", "status": status,
            "observations": {"sweep": {"event": "gaussianBlur", "overrides": overrides,
                                       "used": [{**RADIUS, "default": used}], "error": None},
                             "pixels": _pixels(changed)}}


RESULTS = [
    {"item_id": "menu:-515@settings", "status": "ok",
     "observations": {"event_settings": {"event": "gaussianBlur", "settings": [RADIUS], "error": None},
                      "pixels": _pixels(0.30)}},
    {"item_id": "menu:-515@chart", "status": "ok", "observations": {"pixels": _pixels(0.30)}},
    _swept("default#1", None, 1.0, 0.30),
    _swept("radius=4.0", 4.0, 4.0, 0.52),
    _swept("radius=-1000000.0", -1e6, 0.1, 0.02),
    _swept("radius=1000000.0", 1e6, 1000.0, 0.99),
    {"item_id": "menu:-515@chart@smart_object", "status": "ok", "observations": {"pixels": _pixels(0.0)}},
    {"item_id": "menu:-515@chart@bits32", "status": "refused", "error": "not available", "observations": {}},
]
FEATURE_CODE = [
    {"item_id": "menu:-515", "variants": ["menu:-515@chart"], "binary": "Photoshop.exe", "functions": ["0x1", "0x2"]},
    {"item_id": "menu:-515", "variants": ["menu:-515@chart"], "binary": "Other.8bf", "functions": ["0x3"]},
]
CONTROL_CODE = [
    {"dialog": "Filter > Blur > Gaussian Blur", "label": "Radius", "status": "found", "binary": "Photoshop.exe",
     "via": "sampled", "anchor": "sha256:x", "functions": ["0x4", "0x5"]},
    {"dialog": "Filter > Blur > Box Blur", "label": "Radius", "status": "found", "binary": "Photoshop.exe",
     "via": "sampled", "anchor": "sha256:x", "functions": ["0x6"]},
]


def test_a_filters_sheet_holds_its_settings_ranges_effects_states_and_code() -> None:
    [sheet] = build_sheets([GAUSSIAN], RESULTS, FEATURE_CODE, CONTROL_CODE, plugin_parameters=[], terminology=[])

    assert (sheet["item_id"], sheet["name"], sheet["path"], sheet["event"]) == (
        "menu:-515", "Gaussian Blur", "Filter > Blur > Gaussian Blur", "gaussianBlur")
    assert sheet["on_chart"]["changed_fraction"] == 0.30
    [radius] = sheet["settings"]
    assert (radius["key"], radius["type"], radius["unit"], radius["default"]) == ("radius", "unit", "pixelsUnit", 1.0)
    # The far-out probes read back the bounds Photoshop clamps to.
    assert radius["range"] == {"min": 0.1, "max": 1000.0}
    assert [(t["value"], t["used"], t["changed_fraction"]) for t in radius["tried"]] == [
        (-1e6, 0.1, 0.02), (1.0, 1.0, 0.30), (4.0, 4.0, 0.52), (1e6, 1000.0, 0.99)]
    assert sheet["states"] == {"smart_object": {"status": "ok", "changed_fraction": 0.0},
                               "bits32": {"status": "refused", "changed_fraction": None}}
    assert sheet["code"] == {"Photoshop.exe": 2, "Other.8bf": 1}
    assert sheet["controls"] == [{"label": "Radius", "status": "found", "binary": "Photoshop.exe", "via": "sampled",
                                  "functions": 2}]


def test_a_far_value_read_back_unchanged_is_no_bound() -> None:
    # Wave's random seed took -1,000,000 and 1,000,000 as given: it has no clamp in that span.
    results = [RESULTS[0], _swept("radius=-1000000.0", -1e6, -1e6, 0.3), _swept("radius=1000000.0", 1e6, 1e6, 0.3)]

    [sheet] = build_sheets([GAUSSIAN], results, [], [], plugin_parameters=[], terminology=[])

    assert sheet["settings"][0]["range"] == {"min": None, "max": None, "accepts_far_values": True}


def test_a_setting_its_plug_in_declares_points_at_the_functions_that_compare_its_key_and_choices() -> None:
    wave = {"id": "menu:-543", "kind": "menu_command", "name": "Wave", "path": "Filter > Distort > Wave...",
            "facts": {"command": -543}}
    settings = [{"key": "waveType", "type": "choice", "choices": "waveType", "default": "waveSine"},
                {"key": "numberOfGenerators", "type": "integer", "default": 5}]
    results = [{"item_id": "menu:-543@settings", "status": "ok",
                "observations": {"event_settings": {"event": "wave", "settings": settings, "error": None}}}]
    plugin = {"binary": "Standard MultiPlugin.8bf", "item_id": "menu:-543", "event": "Wave", "settings": [
        {"code": "Wvtp", "name": "Wave Type", "type": "Wvtp", "functions": ["0x2", "0x1"],
         "choices": [{"code": "WvSn", "name": "Sine", "functions": ["0x1"]},
                     {"code": "WvSq", "name": "Square", "functions": ["0x3"]}]}]}
    terminology = [{"code": "Wvtp", "id": 1, "name": "waveType"}, {"code": "NmbG", "id": 2, "name": "numberOfGenerators"}]

    [sheet] = build_sheets([wave], results, [], [], plugin_parameters=[plugin], terminology=terminology)

    wave_type, generators = sheet["settings"]
    assert wave_type["code"] == [{"binary": "Standard MultiPlugin.8bf", "code": "Wvtp", "functions": ["0x1", "0x2"],
                                  "choices": [{"code": "WvSn", "functions": ["0x1"]},
                                              {"code": "WvSq", "functions": ["0x3"]}]}]
    assert generators["code"] == []  # declared by no plug-in: a built-in, or not found
    assert sheet["controls"] == []


def test_a_tools_sheet_is_its_use_on_the_chart_and_in_each_state_not_its_selection() -> None:
    dodge = {"id": "tool:dodgeTool", "kind": "tool", "name": "Dodge Tool", "facts": {"tool_id": "dodgeTool"}}
    results = [
        {"item_id": "tool:dodgeTool", "status": "ok", "observations": {}},  # selected only
        {"item_id": "tool:dodgeTool@use", "status": "ok", "observations": {"pixels": _pixels(0.04)}},
        {"item_id": "tool:dodgeTool@use@cmyk", "status": "ok", "observations": {"pixels": _pixels(0.05)}},
    ]

    [sheet] = build_sheets([dodge], results, [], [], plugin_parameters=[], terminology=[])

    assert (sheet["path"], sheet["event"], sheet["settings"]) == (None, None, [])
    assert sheet["on_chart"]["changed_fraction"] == 0.04
    assert sheet["states"] == {"cmyk": {"status": "ok", "changed_fraction": 0.05}}


def test_a_state_says_whether_the_feature_changed_anything_beyond_what_the_state_alone_did() -> None:
    dodge = {"id": "tool:dodgeTool", "kind": "tool", "name": "Dodge Tool", "facts": {"tool_id": "dodgeTool"}}

    def run(item_id: str, changed: float, after: str) -> dict:
        return {"item_id": item_id, "status": "ok", "observations": {"pixels": {**_pixels(changed), "after_sha256": after}}}

    results = [run("state:cmyk", 0.78, "c"), run("tool:dodgeTool@use@cmyk", 0.80, "d"),
               run("state:mask", 0.0, "m"), run("tool:dodgeTool@use@mask", 0.0, "m")]

    [sheet] = build_sheets([dodge], results, [], [], plugin_parameters=[], terminology=[])

    assert sheet["states"] == {
        "mask": {"status": "ok", "changed_fraction": 0.0, "state_alone": 0.0, "changed_beyond_state": False},
        "cmyk": {"status": "ok", "changed_fraction": 0.80, "state_alone": 0.78, "changed_beyond_state": True},
    }
