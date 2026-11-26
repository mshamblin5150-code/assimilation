"""Where a driven dialog control lives in the decompiled code: the learning the harness hands REA
beside each control it drove, so REA can open that binary at those functions."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.adobe_observed_truth.control_code import (
    build,
    data_labels,
    link_control,
    ui_labels,
    with_discovery,
    with_runtime,
)

RIPPLE = {
    "menu_path": "Filter > Distort > Ripple",
    "binary": "Standard MultiPlugin.8bf",
    "settings": [
        {"name": "&Amount", "code": "Amnt", "functions": ["0x180010", "0x180020"], "choices": []},
        {"name": "&Size", "code": "RplS", "functions": ["0x180030"], "choices": [
            {"name": "Small", "code": "Sml ", "functions": ["0x180040"]},
        ]},
    ],
}
PLUGINS = {RIPPLE["menu_path"]: RIPPLE}


def test_a_filter_control_is_the_code_reading_the_setting_its_label_names() -> None:
    link = link_control("Filter > Distort > Ripple", "Amount:", PLUGINS, strings={}, pending=set())

    assert link == {
        "status": "found",
        "binary": "Standard MultiPlugin.8bf",
        "via": "setting",
        "anchor": "Amnt",
        "functions": ["0x180010", "0x180020"],
    }


def test_a_label_naming_a_setting_with_more_words_finds_it_and_a_tie_reports_every_one() -> None:
    gallery = {
        "menu_path": "Filter > Artistic > Neon Glow",
        "binary": "Filter Gallery.8bf",
        "settings": [
            {"name": "Size", "code": "HlSz", "functions": ["0x2"], "choices": []},
            {"name": "Size", "code": "Sz  ", "functions": ["0x3"], "choices": []},
            {"name": "Glow Amount", "code": "GlwA", "functions": ["0x4"], "choices": []},
            {"name": "Method", "code": "BlrM", "functions": ["0x5"], "choices": []},
        ],
    }
    plugins = {gallery["menu_path"]: gallery}

    method = link_control("Filter > Artistic > Neon Glow", "Blur Method:", plugins, strings={}, pending=set())
    size = link_control("Filter > Artistic > Neon Glow", "Glow Size", plugins, strings={}, pending=set())

    assert (method["anchor"], method["functions"]) == ("BlrM", ["0x5"])
    assert (size["via"], size["anchor"], size["functions"]) == ("setting", "HlSz,Sz  ", ["0x2", "0x3"])


def test_a_label_that_names_nothing_is_not_linked() -> None:
    strings = {"Standard MultiPlugin.8bf": {"6": [("$$$/Example/Zoom/Menu/6", "0x9")]}}

    for label in ("6", "D", "10", "OK"):
        link = link_control("Filter > Distort > Ripple", label, PLUGINS, strings, pending=set())
        assert (label, link["status"]) == (label, "not_found")


LIQUIFY = {"menu_path": "Filter > Liquify", "binary": "Liquify.8bf", "settings": []}


def test_a_control_no_setting_names_is_found_by_its_interface_string() -> None:
    strings = {"Liquify.8bf": {"pin edges": [("$$$/Example/Controls/PinEdges", "0x1800a0")]}}

    link = link_control("Filter > Liquify", "Pin Edges", {"Filter > Liquify": LIQUIFY}, strings, pending=set())

    assert link == {
        "status": "found",
        "binary": "Liquify.8bf",
        "via": "ui_string",
        "anchor": "$$$/Example/Controls/PinEdges",
        "functions": ["0x1800a0"],
    }


def test_a_plugin_control_drawn_with_the_apps_own_string_is_found_in_the_app() -> None:
    # 2026-11-21: Liquify's Preview, Size, Density and Mask Options (and Filter Gallery's Zoom)
    # carry no string in the plug-in; the app draws them with its own interface strings.
    strings = {"Liquify.8bf": {}, "Photoshop.exe": {"mask options": [("$$$/Example/Liquify/MaskOptions", "0x1417")]}}

    link = link_control("Filter > Liquify", "Mask Options", {"Filter > Liquify": LIQUIFY}, strings, pending=set())

    assert link == {
        "status": "found",
        "binary": "Photoshop.exe",
        "via": "ui_string",
        "anchor": "$$$/Example/Liquify/MaskOptions",
        "functions": ["0x1417"],
    }


def test_a_control_whose_string_is_only_in_its_binarys_data_is_found_by_key_with_no_functions() -> None:
    # 2026-11-21: Liquify's View Options, Mesh Size and Show Mask are only in its layout data.
    strings = {"Liquify.8bf": {}, "Photoshop.exe": {}}
    data = {"Liquify.8bf": {"view options": ["$$$/Example/MainWindow/ViewGroup"]}}

    link = link_control("Filter > Liquify", "View Options", {"Filter > Liquify": LIQUIFY}, strings, pending=set(), data=data)

    assert link == {
        "status": "found",
        "binary": "Liquify.8bf",
        "via": "ui_string_data",
        "anchor": "$$$/Example/MainWindow/ViewGroup",
        "functions": [],
    }


def test_a_dropdown_label_read_with_its_arrow_as_a_trailing_v_is_found_by_its_name() -> None:
    # 2026-11-21: dropdowns were read as "RGB V", "Default V", "Pixels V": the V is the arrow.
    strings = {"Photoshop.exe": {"pixels": [("$$$/Example/Units/Pixels", "0x1420")]}}

    link = link_control("Image > Canvas Size", "Pixels V", PLUGINS, strings, pending=set())

    assert (link["status"], link["anchor"], link["functions"]) == ("found", "$$$/Example/Units/Pixels", ["0x1420"])


def test_a_dialog_no_plugin_adds_is_the_apps_own_and_waits_while_the_app_is_decompiled() -> None:
    link = link_control("Image > Adjustments > Curves", "Preset", PLUGINS, strings={}, pending={"Photoshop.exe"})

    assert (link["status"], link["binary"], link["functions"]) == ("waiting", "Photoshop.exe", [])


def test_interface_strings_are_indexed_by_label_with_the_functions_carrying_them() -> None:
    functions = [
        ("0x10", 'f("$$$/Example/Controls/PinEdges=Pin &Edges"); g("$$$/Example/Tip=Drag to warp the image.");'),
        ("0x20", 's = "$$$/Example/Controls/PinEdges=Pin &Edges";'),
        ("0x30", 'h("not an interface string");'),
    ]

    assert ui_labels(functions) == {
        "pin edges": [("$$$/Example/Controls/PinEdges", "0x10"), ("$$$/Example/Controls/PinEdges", "0x20")],
        "drag to warp the image": [("$$$/Example/Tip", "0x10")],
    }


def test_interface_strings_kept_in_a_binarys_data_are_indexed_by_label_without_the_scripting_dictionary() -> None:
    # 2026-11-21: Liquify keeps its panel text in a layout description in its data, never in a
    # function ("text: '$$$/Example/...=View Options'"). The app's scripting dictionary names settings
    # for scripts, not controls, so its keys are left out.
    data = (
        b"\x00text:\x00'$$$/Example/MainWindow/ViewGroup=View Options',\x00"
        b"label:'$$$/Example/ViewPane/MeshSize/Title=Mesh Size:');\x00"
        b"/quality [($$$/Example/Dictionary/Quality=Quality) /char]\x00"
    )

    assert data_labels(data, skip=("Example/Dictionary/",)) == {
        "view options": ["$$$/Example/MainWindow/ViewGroup"],
        "mesh size": ["$$$/Example/ViewPane/MeshSize/Title"],
    }


def _discovered(binary: str, functions: list[str], via: str = "sampled", anchor: str = "sha256:s1") -> dict:
    return {"dialog": "Filter > Liquify", "label": "gear menu", "kind": "button", "binary": binary,
            "functions": functions, "calls": 3, "via": via, "anchor": anchor}


def test_a_control_no_name_places_is_found_by_the_functions_seen_running_only_for_it() -> None:
    # 2026-11-22: 165 of 331 controls had no setting or string to match ("gear menu", eyedroppers).
    missing = link_control("Filter > Liquify", "gear menu", {"Filter > Liquify": LIQUIFY}, strings={}, pending=set())
    rows = [_discovered("Photoshop.exe", ["0x140002000"]), _discovered("Liquify.8bf", ["0x1800b0", "0x1800c0"])]

    assert with_discovery(missing, rows) == {
        "status": "found",
        "binary": "Liquify.8bf",  # the dialog's own binary first, then the app
        "via": "sampled",
        "anchor": "sha256:s1",
        "functions": ["0x1800b0", "0x1800c0"],
    }
    assert with_discovery(missing, rows[:1])["binary"] == "Photoshop.exe"
    assert with_discovery(missing, []) == missing


def test_what_sampling_and_the_hooks_found_in_one_binary_are_one_link_naming_both() -> None:
    missing = link_control("Filter > Liquify", "gear menu", {"Filter > Liquify": LIQUIFY}, strings={}, pending=set())
    rows = [_discovered("Liquify.8bf", ["0x1800c0", "0x1800b0"]),
            _discovered("Liquify.8bf", ["0x1800d0", "0x1800b0"], via="runtime", anchor="ev_hooks")]

    assert with_discovery(missing, rows) == {
        "status": "found",
        "binary": "Liquify.8bf",
        "via": "sampled+runtime",
        "anchor": "sha256:s1,ev_hooks",
        "functions": ["0x1800b0", "0x1800c0", "0x1800d0"],
    }


def test_a_control_found_by_name_keeps_its_link_whatever_was_discovered() -> None:
    named = link_control("Filter > Distort > Ripple", "Amount:", PLUGINS, strings={}, pending=set())

    assert with_discovery(named, [_discovered("Standard MultiPlugin.8bf", ["0x9"])]) == named


PILOT = [
    {"filter": "Filter > Distort > Ripple", "function": "0x180010", "phases": ["lifecycle open dialog", "script apply Amount 300"],
     "calls": 3, "fired_while_controls_driven": 0, "frida_evidence": "ev_frida"},
    {"filter": "Filter > Distort > Ripple", "function": "0x180020", "phases": [], "calls": 0,
     "fired_while_controls_driven": 0, "frida_evidence": "ev_frida"},
]


def test_a_control_whose_functions_ran_only_per_run_is_marked_filter_level() -> None:
    """The runtime-link pilot (2026-11-12): Ripple's mapped functions read and wrote its settings
    once per run and never fired while a control was driven. The control's code link says so."""
    record = {"dialog": "Filter > Distort > Ripple", "label": "Amount", "status": "found", "functions": ["0x180010", "0x180020"]}

    marked = with_runtime(record, PILOT)

    assert marked["runtime"]["level"] == "filter"
    assert [(f["function"], f["calls"], f["fired_while_controls_driven"]) for f in marked["runtime"]["functions"]] == [
        ("0x180010", 3, 0), ("0x180020", 0, 0),
    ]
    assert marked["runtime"]["functions"][0]["frida_evidence"] == "ev_frida"


def test_a_control_firing_while_driven_is_control_level_and_one_never_hooked_is_unmarked() -> None:
    live = [{**PILOT[0], "fired_while_controls_driven": 4}]
    record = {"dialog": "Filter > Distort > Ripple", "label": "Amount", "status": "found", "functions": ["0x180010"]}
    other = {"dialog": "Filter > Blur > Motion Blur", "label": "Angle", "status": "found", "functions": ["0x180010"]}

    assert with_runtime(record, live)["runtime"]["level"] == "control"
    assert "runtime" not in with_runtime(other, PILOT)  # never hooked: nothing observed either way


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_build_links_each_driven_control_once_from_the_corpus(tmp_path: Path) -> None:
    corpus, dataset = tmp_path / "corpus", tmp_path / "dataset"
    liquify = corpus / "photoshop" / "Liquify"
    (liquify / "pseudocode" / "functions").mkdir(parents=True)
    (liquify / "pseudocode" / "functions" / "0x1800a0.c").write_text('x("$$$/Example/Pin=Pin Edges");', encoding="utf-8")
    (liquify / "decompile-all.json").write_text("{}", encoding="utf-8")
    (liquify / "Liquify.8bf").write_bytes(b"MZ\x00'$$$/Example/Pin=Pin Edges'\x00")
    exe = corpus / "photoshop" / "exe"
    (exe / "pseudocode" / "functions").mkdir(parents=True)
    (exe / "decompile-all.json").write_text("{}", encoding="utf-8")
    (exe / "Photoshop.exe").write_bytes(b"MZ\x00")
    (corpus / "manifest.json").write_text(json.dumps([
        {"app": "photoshop", "relative": r"Required\Plug-ins\Filters\Liquify.8bf", "work_dir": str(liquify),
         "path": str(liquify / "Liquify.8bf")},
        {"app": "photoshop", "relative": "Photoshop.exe", "work_dir": str(exe), "path": str(exe / "Photoshop.exe")},
    ]), encoding="utf-8")
    dataset.mkdir()
    _jsonl(dataset / "plugin-parameters.jsonl", [RIPPLE, LIQUIFY])
    _jsonl(dataset / "control-actions.jsonl", [
        {"dialog": "Filter > Liquify", "label": "Pin Edges", "kind": "checkbox"},
        {"dialog": "Filter > Liquify", "label": "Pin Edges", "kind": "checkbox"},  # driven twice: one link
        {"dialog": "Image > Adjustments > Curves", "label": "Preset", "kind": "dropdown"},
        {"dialog": "Filter > Liquify", "label": {"chars": 40, "sha256": "ab"}, "kind": "button"},  # no label
        # Read as "gear menu:" from the dialog, logged as "gear menu" by the drive (2026-11-23: "Show Amount of:").
        {"dialog": "Filter > Liquify", "label": "gear menu:", "kind": "button"},
    ])
    # A discovered control whose label was not Photoshop's own is published as its length and hash
    # (build_maps, 2026-11-24): it can name no catalogued control, and is passed over.
    hashed = {**_discovered("Liquify.8bf", ["0x1800c0"]), "label": {"chars": 9, "sha256": "cd"}}
    _jsonl(dataset / "runtime-discovery.jsonl", [_discovered("Liquify.8bf", ["0x1800b0"]), hashed])

    summary = build(corpus, dataset, app="photoshop")

    rows = [json.loads(line) for line in (dataset / "control-code.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["dialog"], r["label"], r["status"], r["binary"], r["functions"]) for r in rows] == [
        ("Filter > Liquify", "Pin Edges", "found", r"Required\Plug-ins\Filters\Liquify.8bf", ["0x1800a0"]),
        ("Image > Adjustments > Curves", "Preset", "not_found", "Photoshop.exe", []),
        ("Filter > Liquify", "gear menu:", "found", r"Required\Plug-ins\Filters\Liquify.8bf", ["0x1800b0"]),
    ]
    assert summary["by_status"] == {"found": 2, "not_found": 1}
    assert summary["by_via"] == {"ui_string": 1, "sampled": 1}
