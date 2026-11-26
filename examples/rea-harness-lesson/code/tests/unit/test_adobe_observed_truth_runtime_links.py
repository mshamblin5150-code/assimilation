"""Upgrading a control's code link from a name match to an observation: REA hooks the mapped
functions in the running app while the harness drives controls; a function is observed for a
control when it fires while that control is driven, and never while the dialog sits idle."""

from __future__ import annotations

from scripts.adobe_observed_truth.function_index import FunctionIndex
from scripts.adobe_observed_truth.runtime_links import attribute, discoveries, hook_candidates, hook_script


def test_the_hook_script_hooks_each_function_at_its_offset_in_the_loaded_module() -> None:
    script = hook_script("Standard MultiPlugin.8bf", "0x180000000", ["0x1802263f0", "0x180226540"])

    assert '"Standard MultiPlugin.8bf"' in script
    assert '"0x1802263f0"' in script and '"0x180226540"' in script
    assert 'ptr("0x180000000")' in script  # offsets are taken from the image base Ghidra used
    assert hook_script("Standard MultiPlugin.8bf", "0x180000000", ["0x1802263f0"]) == hook_script(
        "Standard MultiPlugin.8bf", "0x180000000", ["0x1802263f0"]
    )  # the same request, the same script (REA records its digest)


def test_the_hook_script_waits_for_the_module_and_hooks_again_each_time_it_loads() -> None:
    """A filter plug-in loads when its filter runs and at a new address each time (Ripple:
    two runs, two bases, 2026-11-11), so hooks are installed on load, not only at attach."""
    script = hook_script("Standard MultiPlugin.8bf", "0x180000000", ["0x1802263f0"])

    assert "Process.findModuleByName(" in script  # asks without failing while it is not loaded
    assert "Process.getModuleByName(" not in script
    assert "kind: \"loaded\"" in script  # each new load is reported with its base


BASELINE = (1000, 2000)
ACTIONS = [
    {"t0": 3000, "t1": 3400, "kind": "slider", "label": "Amount"},
    {"t0": 3500, "t1": 3900, "kind": "slider", "label": "Amount"},
    {"t0": 5000, "t1": 5400, "kind": "dropdown", "label": "Size"},
]


def batch(t0: int, t1: int, **counts: int) -> dict:
    return {"kind": "hits", "t0": t0, "t1": t1, "counts": {f"0x{k[1:]}": v for k, v in counts.items()}}


def test_a_function_firing_only_while_one_control_is_driven_is_observed_for_that_control() -> None:
    batches = [
        batch(3000, 3250, f1802263f0=4),
        batch(3500, 3750, f1802263f0=2),
        batch(5000, 5250, f180226540=1),
    ]

    links = attribute(batches, BASELINE, ACTIONS)

    assert links["0x1802263f0"] == {"status": "observed", "controls": ["slider Amount"], "calls": 6}
    assert links["0x180226540"] == {"status": "observed", "controls": ["dropdown Size"], "calls": 1}


def test_a_function_firing_while_idle_or_for_several_controls_is_not_tied_to_one() -> None:
    batches = [
        batch(1200, 1450, f180214df0=3),  # idle dialog: background work, not a control
        batch(3000, 3250, f180214df0=1, f180221680=2),
        batch(5000, 5250, f180221680=2),
    ]

    links = attribute(batches, BASELINE, ACTIONS)

    assert links["0x180214df0"]["status"] == "fires while idle"
    assert links["0x180221680"] == {"status": "several controls", "controls": ["dropdown Size", "slider Amount"], "calls": 4}


def test_a_batch_straddling_the_end_of_the_baseline_belongs_to_the_action_it_runs_into() -> None:
    """Ripple's entry point fired as its dialog opened; the quarter-second batch began inside
    the baseline and was taken for idle work (2026-11-12)."""
    opening = [{"t0": 2100, "t1": 2600, "kind": "lifecycle", "label": "open dialog"}]

    links = attribute([batch(1900, 2150, f1802620b0=2)], BASELINE, opening)

    assert links["0x1802620b0"] == {"status": "observed", "controls": ["lifecycle open dialog"], "calls": 2}


def test_calls_outside_every_window_are_neither_a_control_nor_idle() -> None:
    links = attribute([batch(9000, 9250, f180233e70=5)], BASELINE, ACTIONS)

    assert links["0x180233e70"] == {"status": "unattributed", "controls": [], "calls": 5}


def test_discovery_gives_each_driven_control_the_functions_seen_only_for_it_by_binary() -> None:
    """Discovered functions carry their binary ("name!address"); a control gets one row per binary
    holding functions observed for it alone. Background and shared code give it nothing."""
    batches = [
        {"kind": "hits", "t0": 1200, "t1": 1450, "counts": {"Photoshop.exe!0x140001000": 9}},  # the idle message loop
        {"kind": "hits", "t0": 3000, "t1": 3250, "counts": {
            "Photoshop.exe!0x140001000": 3, "Photoshop.exe!0x140002000": 2, "Liquify.8bf!0x1800a0": 1,
            "Photoshop.exe!0x140003000": 1}},
        {"kind": "hits", "t0": 5000, "t1": 5250, "counts": {"Photoshop.exe!0x140003000": 1, "Photoshop.exe!0x140004000": 4}},
    ]

    rows = discoveries(batches, BASELINE, ACTIONS, dialog="Filter > Liquify", via="sampled", anchor="sha256:ab12")

    assert rows == [
        {"dialog": "Filter > Liquify", "label": "Amount", "kind": "slider", "binary": "Liquify.8bf",
         "functions": ["0x1800a0"], "calls": 1, "via": "sampled", "anchor": "sha256:ab12"},
        {"dialog": "Filter > Liquify", "label": "Amount", "kind": "slider", "binary": "Photoshop.exe",
         "functions": ["0x140002000"], "calls": 2, "via": "sampled", "anchor": "sha256:ab12"},
        {"dialog": "Filter > Liquify", "label": "Size", "kind": "dropdown", "binary": "Photoshop.exe",
         "functions": ["0x140004000"], "calls": 4, "via": "sampled", "anchor": "sha256:ab12"},
    ]


def test_a_sweep_tells_apart_same_named_controls_of_different_dialogs() -> None:
    """A whole-app sweep drives every dialog: each has its own Preview checkbox. Code running
    only for Levels' Preview is Levels' Preview's, not one shared "checkbox Preview"."""
    actions = [
        {"t0": 3000, "t1": 3400, "kind": "checkbox", "label": "Preview", "dialog": "Image > Adjustments > Levels"},
        {"t0": 5000, "t1": 5400, "kind": "checkbox", "label": "Preview", "dialog": "Image > Adjustments > Curves"},
    ]
    batches = [{"kind": "hits", "t0": 3000, "t1": 3250, "counts": {"Photoshop.exe!0x140001000": 2}},
               {"kind": "hits", "t0": 5000, "t1": 5250, "counts": {"Photoshop.exe!0x140002000": 1}}]

    rows = discoveries(batches, BASELINE, actions, dialog="sweep", via="sampled", anchor="sha256:s")

    assert [(r["dialog"], r["label"], r["functions"]) for r in rows] == [
        ("Image > Adjustments > Curves", "Preview", ["0x140002000"]),
        ("Image > Adjustments > Levels", "Preview", ["0x140001000"]),
    ]


def test_code_running_inside_a_control_action_is_the_controls_not_the_commands_around_it() -> None:
    """A sweep times each menu command and, inside it, each control the command's dialog has:
    the narrower window wins. Before and after the controls, the code is the command's."""
    actions = [
        {"t0": 2000, "t1": 9000, "kind": "menu_command", "label": "menu:1802"},
        {"t0": 4000, "t1": 4400, "kind": "checkbox", "label": "Preview", "dialog": "Image > Adjustments > Curves"},
    ]
    batches = [{"kind": "hits", "t0": 4000, "t1": 4250, "counts": {"m!0x1": 2}},
               {"kind": "hits", "t0": 2500, "t1": 2750, "counts": {"m!0x2": 1}}]

    links = attribute(batches, (0, 1000), actions)

    assert links["m!0x1"]["controls"] == ["Image > Adjustments > Curves: checkbox Preview"]
    assert links["m!0x2"]["controls"] == ["menu_command menu:1802"]


def test_a_long_sweep_has_many_idle_windows() -> None:
    """Hours of sweeping: Photoshop sits idle between specs and after each restart."""
    batches = [batch(1200, 1450, f1802263f0=1), batch(9000, 9250, f180226540=1), batch(3000, 3250, f180226540=2)]

    links = attribute(batches, [BASELINE, (9000, 9500)], ACTIONS)

    assert links["0x1802263f0"]["status"] == "fires while idle"
    assert links["0x180226540"]["status"] == "fires while idle"


def test_hooked_functions_are_discoveries_in_the_binary_they_were_hooked_in() -> None:
    """The hook script counts plain addresses in one module; their rows name that binary."""
    rows = discoveries([batch(5000, 5250, f140004000=2)], BASELINE, ACTIONS, dialog="Image > Adjustments > Curves",
                       via="runtime", anchor="ev_hooks", binary="Photoshop.exe")

    assert rows == [{"dialog": "Image > Adjustments > Curves", "label": "Size", "kind": "dropdown",
                     "binary": "Photoshop.exe", "functions": ["0x140004000"], "calls": 2,
                     "via": "runtime", "anchor": "ev_hooks"}]


# A dialog's decomp: A handles the slider and calls B and C; B calls D, D calls E. S is shared by
# the controls (their dispatcher) and registers F; I is the idle message loop and calls G.
CALLS = {"0x140001000": ["0x140002000", "0x140003000"], "0x140002000": ["0x140004000"],
         "0x140004000": ["0x140005000"], "0x140006000": ["0x140007000"], "0x140008000": ["0x140009000"]}
INDEX = FunctionIndex([(a, f"FUN_{a[2:]}", [(int(a, 16), int(a, 16) + 0xFF)])
                       for a in [f"0x14000{n}000" for n in range(1, 10)]])


def _pseudocode(address: str) -> str:
    return f"void FUN_{address[2:]}(void) {{ " + " ".join(f"FUN_{c[2:]}();" for c in CALLS.get(address, [])) + " }"


SAMPLED = {
    "Photoshop.exe!0x140001000": {"status": "observed", "controls": ["slider Amount"], "calls": 9},
    "Photoshop.exe!0x140003000": {"status": "observed", "controls": ["slider Amount"], "calls": 2},
    "Photoshop.exe!0x140006000": {"status": "several controls", "controls": ["dropdown Size", "slider Amount"], "calls": 5},
    "Photoshop.exe!0x140008000": {"status": "fires while idle", "controls": [], "calls": 40},
}


def test_sampling_misses_are_hooked_from_the_decomp_callees_of_what_it_caught() -> None:
    """A function quicker than the sampling interval is missed; it is called by one the sampler
    did catch, so the decomp names it. Callees of control code (observed for one control, or
    shared by several) are hooked, two calls deep, unless sampling already saw them; the idle
    loop's callees are everything and are left out."""
    assert hook_candidates(SAMPLED, "Photoshop.exe", INDEX, _pseudocode) == ["0x140002000", "0x140007000", "0x140004000"]


def test_hook_candidates_nearest_first_up_to_the_cap() -> None:
    assert hook_candidates(SAMPLED, "Photoshop.exe", INDEX, _pseudocode, depth=1) == ["0x140002000", "0x140007000"]
    assert hook_candidates(SAMPLED, "Photoshop.exe", INDEX, _pseudocode, cap=1) == ["0x140002000"]
