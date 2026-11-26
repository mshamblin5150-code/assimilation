"""The tool helpers' ExtendScript runs with Photoshop's Application as its global scope."""

from __future__ import annotations

import re

from scripts.adobe_observed_truth.ps_tools import _JS, bucket_fill, set_brush_options, stroke, wand_select


class _Recorder:
    """A Photoshop that records the scripts sent to it."""

    def __init__(self) -> None:
        self.scripts: list[str] = []

    def js(self, body: str) -> object:
        self.scripts.append(body)
        return {}

# Application properties a global function definition would overwrite.
APPLICATION_PROPERTIES = {"currentTool", "foregroundColor", "backgroundColor", "activeDocument", "documents",
                          "preferences", "displayDialogs", "name", "path", "version", "fonts", "build"}


def test_no_helper_is_named_after_an_application_property() -> None:
    # A helper named currentTool assigned a function to app.currentTool on every call, and
    # Photoshop answered each with a "Select is not currently available" alert (2026-11-25).
    defined = set(re.findall(r"function\s+(\w+)\s*\(", _JS))

    assert defined and not defined & APPLICATION_PROPERTIES


def test_the_pressure_switches_are_always_set_so_one_run_cannot_leak_into_the_next() -> None:
    # The opacity switch left on by one spike run made the next run's stroke fade too (2026-11-25).
    plain, pressed = _Recorder(), _Recorder()
    common = {"size_px": 21, "hardness": 100, "opacity": 100, "flow": 100, "spacing": 25}

    set_brush_options(plain, "brush", **common)
    set_brush_options(pressed, "brush", **common, pressure_size=True)

    assert 'o.putBoolean(sid("usePressureOverridesSize"),false)' in plain.scripts[0]
    assert 'o.putBoolean(sid("usePressureOverridesOpacity"),false)' in plain.scripts[0]
    assert 'o.putBoolean(sid("usePressureOverridesSize"),true)' in pressed.scripts[0]


def test_the_wand_and_the_bucket_click_the_pixel_asked_for() -> None:
    # Sent as x + 0.5, a click meant for column 128 took column 129: Photoshop reads the point as
    # the pixel itself (the wand spike, 2026-11-25).
    ps = _Recorder()

    wand_select(ps, 128, 20, tolerance=32, anti_alias=False, contiguous=True)
    bucket_fill(ps, 128, 20, {"tolerance": 32, "anti_alias": True, "contiguous": True, "all_layers": False})

    for script in ps.scripts:
        assert 'putUnitDouble(cid("Hrzn"),cid("#Pxl"),128)' in script and "+0.5" not in script
    assert 'putInteger(cid("Tlrn"),32)' in ps.scripts[0] and 'putBoolean(cid("Cntg"),true)' in ps.scripts[0]
    assert 'executeAction(cid("setd")' in ps.scripts[0]


def test_a_stroke_can_ask_photoshop_to_simulate_pen_pressure() -> None:
    plain, pressed = _Recorder(), _Recorder()

    stroke(plain, "brush", [(40, 150), (360, 150)])
    stroke(pressed, "brush", [(40, 150), (360, 150)], simulate_pressure=True)

    assert "strokePath(ToolType.BRUSH,false)" in plain.scripts[0]
    assert "strokePath(ToolType.BRUSH,true)" in pressed.scripts[0]


def test_dynamics_are_put_over_the_brush_options_by_their_json_type() -> None:
    ps = _Recorder()
    set_brush_options(ps, "brush", size_px=21, hardness=100, opacity=100, flow=100, spacing=25,
                      dynamics={"useScatter": True, "count": 3, "scatter": {"_unit": "percentUnit", "_value": 120},
                                "szVr": {"_obj": "brVr", "bVTy": 1, "jitter": {"_unit": "percentUnit", "_value": 50}}})
    script = ps.scripts[0]
    puts = script[script.index('o.putObject(sid("dualBrush")'):script.rindex("setToolOptions(")]
    assert "function kid(s)" in puts
    assert 'o.putBoolean(kid("useScatter"),true);' in puts
    assert 'o.putInteger(kid("count"),3);' in puts
    assert 'o.putUnitDouble(kid("scatter"),kid("percentUnit"),120.0);' in puts
    inner = re.search(r'var (o_0_\d+)=new ActionDescriptor\(\);', puts).group(1)
    assert f'{inner}.putInteger(kid("bVTy"),1);' in puts
    assert f'{inner}.putUnitDouble(kid("jitter"),kid("percentUnit"),50.0);' in puts
    assert f'o.putObject(kid("szVr"),kid("brVr"),{inner});' in puts


def test_descriptor_puts_a_string_as_a_string() -> None:
    from scripts.adobe_observed_truth.ps_tools import descriptor_puts_js

    assert 'o.putString(kid("name"),"observed-truth-pattern");' in descriptor_puts_js("o", {"name": "observed-truth-pattern"})
