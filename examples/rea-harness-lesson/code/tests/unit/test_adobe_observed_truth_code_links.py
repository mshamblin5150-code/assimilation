from __future__ import annotations

from pathlib import Path

from scripts.adobe_observed_truth.code_links import Link, is_current, link, scan_binary, scan_record

ANCHORS = {
    "tool:paintbrushTool": ["paintbrushTool"],
    "pref:historyPreferences.maximumStates": ["maximumStates"],
    "panel:panelid.static.layers": ["panelid.static.layers"],
}


def test_items_are_found_waiting_or_not_found_depending_on_what_has_been_decompiled() -> None:
    found_by_binary = {
        "photoshop/Brushes.8bi": {"paintbrushTool"},
        "photoshop/Layers.dll": set(),
    }

    links = link(ANCHORS, found_by_binary, pending=["photoshop/Photoshop.exe"])

    assert links == {
        "tool:paintbrushTool": Link("found", ("photoshop/Brushes.8bi",)),
        "pref:historyPreferences.maximumStates": Link("waiting", ()),
        "panel:panelid.static.layers": Link("waiting", ()),
    }


def test_once_nothing_is_pending_an_item_with_no_hit_is_not_found() -> None:
    found_by_binary = {"photoshop/Photoshop.exe": {"maximumStates", "paintbrushTool"}}

    links = link(ANCHORS, found_by_binary, pending=[])

    assert links["panel:panelid.static.layers"] == Link("not_found", ())
    assert links["tool:paintbrushTool"] == Link("found", ("photoshop/Photoshop.exe",))


def test_an_item_without_anchors_has_no_code_link_to_wait_for() -> None:
    assert link({"menu:101": []}, {}, pending=["photoshop/Photoshop.exe"]) == {
        "menu:101": Link("no_anchor", ())
    }


def test_a_name_given_as_the_value_of_a_localised_string_is_found(tmp_path: Path) -> None:
    # Photoshop.exe 2026-11-21: every static panel id appears only as the default value of a
    # localised key=value string, so 25 panels read as not found.
    (tmp_path / "functions").mkdir()
    (tmp_path / "functions" / "0x140a46590.c").write_text(
        'FUN_141bc7ee0(&DAT_14d8dee68,"$$$/Example/History=panelid.static.history",-1);\n'
        'FUN_1400(&DAT_1,"maximumStates");\n'
        'FUN_1401(&DAT_2,"see panelid.static.layers");\n',
        encoding="utf-8",
    )

    found = scan_binary(tmp_path, {"panelid.static.history", "maximumStates", "panelid.static.layers"})

    assert found == {"panelid.static.history", "maximumStates"}


def test_a_binary_is_rescanned_when_the_names_or_the_matcher_change() -> None:
    # 2026-11-21: the key=value matcher changed what counts as found, but the scan state keyed
    # only on the names searched, so every binary kept its old result until the state was deleted.
    wanted = {"maximumStates", "paintbrushTool"}
    record = scan_record(wanted, found={"maximumStates"})

    assert is_current(record, wanted)
    assert not is_current(record, wanted | {"panelid.static.layers"})
    assert not is_current({**record, "matcher": "an earlier matcher"}, wanted)
    assert not is_current({"anchors": sorted(wanted), "found": ["maximumStates"]}, wanted)
