"""What an Illustrator command did to the document, from vector snapshots taken before and after:
the Illustrator counterpart of the Photoshop pixel change."""

from __future__ import annotations

from scripts.adobe_observed_truth.vector_change import vector_change


def _path(bounds, points=4, fill="rgb(255,0,0)", stroke_mpt=1000) -> dict:
    return {"type": "PathItem", "bounds": bounds, "points": points, "closed": True, "filled": True,
            "stroked": True, "fill": fill, "stroke": "rgb(0,0,0)", "stroke_mpt": stroke_mpt, "opacity": 100}


def test_nothing_done_is_no_change() -> None:
    snap = {"items": [_path([0, 0, 10, 10])], "document": {"artboards": 1, "layers": 1}}

    assert vector_change(snap, snap) == {"changed": False, "added": {}, "removed": {}, "fields": {}, "document": {},
                                         "items_before": 1, "items_after": 1}


def test_a_moved_or_recoloured_path_is_a_field_change_not_a_removal_and_an_addition() -> None:
    before = {"items": [_path([0, 0, 10, 10]), _path([20, 0, 30, 10])], "document": {"artboards": 1}}
    after = {"items": [_path([5, 0, 15, 10]), _path([20, 0, 30, 10], fill="rgb(0,0,255)")], "document": {"artboards": 1}}

    change = vector_change(before, after)

    assert change["changed"] and change["added"] == {} and change["removed"] == {}
    assert change["fields"] == {"bounds": 1, "fill": 1}


def test_grouping_and_new_items_count_by_type_and_document_facts_show_before_and_after() -> None:
    before = {"items": [_path([0, 0, 10, 10]), _path([20, 0, 30, 10])], "document": {"artboards": 1, "layers": 1}}
    group = {"type": "GroupItem", "bounds": [0, 0, 30, 10], "children": 2}
    after = {"items": [group, _path([0, 0, 10, 10]), _path([20, 0, 30, 10]), _path([0, 0, 30, 10], points=8)],
             "document": {"artboards": 2, "layers": 1}}

    change = vector_change(before, after)

    assert change["added"] == {"GroupItem": 1, "PathItem": 1}
    assert change["removed"] == {}
    assert change["document"] == {"artboards": [1, 2]}
    assert (change["items_before"], change["items_after"]) == (2, 4)
