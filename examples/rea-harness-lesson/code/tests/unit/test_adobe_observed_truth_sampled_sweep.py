"""A whole-app sweep with the interface thread sampled throughout: every spec and every control
action timed, idle windows between, the sampler following Photoshop across restarts."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from scripts.adobe_observed_truth.control_drivers import Control
from scripts.adobe_observed_truth.sampled_sweep import (
    SampledSweep,
    build_maps,
    read_sweep,
    watched_binaries,
)


class Clock:
    def __init__(self) -> None:
        self.now = 1000

    def __call__(self) -> int:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += int(seconds * 1000)


def _sweep(tmp_path, pids, clock, started, **options):
    def start(pid: int, stop: threading.Event, out) -> None:
        started.append(pid)
        out.write_text(json.dumps({"kind": "hits", "t0": 0, "t1": 1, "counts": {f"Photoshop.exe!0x{pid}": 1}}) + "\n",
                       encoding="utf-8")
        stop.wait(5)

    return SampledSweep(tmp_path, start, pids=lambda: pids, clock=clock, sleep=clock.sleep, idle_s=5, **options)


def test_each_spec_and_each_control_inside_it_get_a_time_window(tmp_path) -> None:
    clock, started, dialog = Clock(), [], {"now": None}
    sweep = _sweep(tmp_path, [41], clock, started, dialog_of=lambda: dialog["now"])
    with sweep.spec("menu:1802", "menu_command"):
        clock.now += 100
        dialog["now"] = "Image > Adjustments > Curves"
        sweep.control_acted(Control("checkbox", (1, 2, 3, 4), "Preview"), clock.now, clock.now + 50)
        sweep.control_acted(Control("slider", (5, 6, 7, 8)), clock.now + 60, clock.now + 90)
        clock.now += 200
    sweep.close()

    _, idle, actions = read_sweep(tmp_path)
    assert idle == [[1000, 6000]]  # the sampler's first idle window, before any spec
    assert actions == [
        {"t0": 6000, "t1": 6300, "kind": "menu_command", "label": "menu:1802"},
        {"t0": 6100, "t1": 6150, "kind": "checkbox", "label": "Preview", "dialog": "Image > Adjustments > Curves"},
        {"t0": 6160, "t1": 6190, "kind": "slider", "label": "[5, 6, 7, 8]", "dialog": "Image > Adjustments > Curves"},
    ]


def test_the_sampler_follows_photoshop_across_a_restart_with_a_new_idle_window(tmp_path) -> None:
    clock, started, pids = Clock(), [], [41]
    sweep = _sweep(tmp_path, pids, clock, started)
    with sweep.spec("menu:1", "menu_command"):
        pass
    pids[0] = 52  # the runner restarted a hung Photoshop
    with sweep.spec("menu:2", "menu_command"):
        pass
    sweep.close()

    batches, idle, actions = read_sweep(tmp_path)
    assert started == [41, 52]
    assert len(idle) == 2 and [a["label"] for a in actions] == ["menu:1", "menu:2"]
    assert {fn for b in batches for fn in b["counts"]} == {"Photoshop.exe!0x41", "Photoshop.exe!0x52"}


def test_an_idle_window_is_kept_every_so_many_specs(tmp_path) -> None:
    clock, started = Clock(), []
    sweep = _sweep(tmp_path, [41], clock, started, idle_every=2)
    for n in range(5):
        with sweep.spec(f"menu:{n}", "menu_command"):
            clock.now += 10
    sweep.close()

    _, idle, _ = read_sweep(tmp_path)
    assert len(idle) == 3  # at the start, after the 2nd spec and after the 4th


def test_the_sampler_watches_every_decompiled_binary_of_the_app(tmp_path) -> None:
    """Filter dialogs run in their plug-ins: a sweep watches every binary with pseudocode."""
    corpus = tmp_path / "corpus"
    done, pending = corpus / "photoshop" / "Photoshop.exe", corpus / "photoshop" / "Plug-ins__Liquify.8bf"
    for work in (done, pending):
        (work / "pseudocode").mkdir(parents=True)
    (done / "decompile-all.json").write_text("{}", encoding="utf-8")
    journal = {"address": "0x140001000", "name": "FUN_140001000", "status": "written",
               "body": {"ranges": [{"start": "0x140001000", "end": "0x1400010ff"}]}}
    (done / "pseudocode" / "decompile-journal.jsonl").write_text(json.dumps(journal) + "\n", encoding="utf-8")
    (corpus / "manifest.json").write_text(json.dumps([
        {"app": "photoshop", "path": r"C:\Program Files\Adobe\Photoshop.exe", "relative": "Photoshop.exe", "work_dir": str(done)},
        {"app": "photoshop", "path": r"C:\Program Files\Adobe\Plug-ins\Liquify.8bf", "relative": r"Plug-ins\Liquify.8bf", "work_dir": str(pending)},
        {"app": "illustrator", "path": r"C:\x\Illustrator.exe", "relative": "Illustrator.exe", "work_dir": str(done)},
    ]), encoding="utf-8")

    watch, indexes = watched_binaries(corpus, "photoshop")

    assert watch == {"Photoshop.exe": Path(r"C:\Program Files\Adobe\Photoshop.exe")}
    assert indexes["Photoshop.exe"].containing(0x140001080) == "0x140001000"


def _jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_code_seen_only_on_a_background_thread_reaches_the_sweep(tmp_path) -> None:
    # UXP's engine thread, where every menu command enters Photoshop, held 1,312 functions the
    # UI thread's samples never showed (2026-11-24).
    import threading

    from scripts.adobe_observed_truth.sampled_sweep import read_sweep
    from scripts.adobe_observed_truth.stack_sampler import sample_process

    out = tmp_path / "batches-41.jsonl"
    ran: dict[str, int] = {}

    def ui_sampler(pid, tid, watch, indexes, path, stop, **kw):
        ran["ui"] = tid
        _jsonl(path, [{"kind": "hits", "t0": 0, "t1": 250, "counts": {"Photoshop.exe!0x140000100": 3}}])
        return {"samples": 1}

    def busiest(pid, ui, watch, indexes, path, stop, **kw):
        ran["background_skips"] = ui
        _jsonl(path, [{"kind": "hits", "t0": 0, "t1": 250, "counts": {"Photoshop.exe!0x140007000": 2}}])

    sample_process(41, 9, {}, {}, out, threading.Event(), sample_fn=ui_sampler, busiest_fn=busiest)

    batches, _, _ = read_sweep(_with_timeline(tmp_path))
    seen = {fn for b in batches for fn in b["counts"]}
    assert seen == {"Photoshop.exe!0x140000100", "Photoshop.exe!0x140007000"}
    assert ran == {"ui": 9, "background_skips": 9}


def _with_timeline(folder):
    _jsonl(folder / "timeline.jsonl", [{"idle": [0, 900]}])
    return folder


def _control_sweep(tmp_path, dialog: str, label: str):
    sweep, dataset = tmp_path / "sweep", tmp_path / "dataset"
    sweep.mkdir(), dataset.mkdir()
    _jsonl(sweep / "timeline.jsonl", [
        {"idle": [0, 900]},
        {"t0": 1000, "t1": 4900, "kind": "dialog_controls", "label": "menu:3090@controls"},
        {"t0": 3000, "t1": 3400, "kind": "dropdown", "label": label, "dialog": dialog},
    ])
    _jsonl(sweep / "batches-41.jsonl", [
        {"kind": "hits", "t0": 100, "t1": 350, "counts": {"Photoshop.exe!0x140000100": 9}},
        {"kind": "hits", "t0": 3000, "t1": 3250, "counts": {"Photoshop.exe!0x140003000": 2}},
    ])
    return sweep, dataset


def _discovered(dataset):
    path = dataset / "runtime-discovery.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_a_mapped_control_label_is_published_only_if_it_is_one_of_photoshops_own(tmp_path) -> None:
    # The timeline's control labels are raw OCR: a file dialog's walk read the operator's own file
    # names (a case study .docx, a PDF) into them (2026-11-24). Unknown text becomes its length and hash.
    sweep, dataset = _control_sweep(tmp_path, "Image > Adjustments > Curves", "Module 4 Case Study.docx")

    build_maps(sweep, dataset, known={"preview"})

    (row,) = _discovered(dataset)
    assert row["label"] == {"chars": 24, "sha256": hashlib.sha256(b"Module 4 Case Study.docx").hexdigest()}


def test_a_dialog_last_recorded_as_a_windows_file_dialog_gets_no_control_rows(tmp_path) -> None:
    # File dialogs get no control pass now; the walks before that change are not mapped.
    sweep, dataset = _control_sweep(tmp_path, "File > Place Linked", "All Formats (*.*)")
    _jsonl(sweep / "control-actions.jsonl", [
        {"item_id": "menu:3090@controls", "dialog": "File > Place Linked", "kind": "dropdown"},
        {"item_id": "menu:3090@controls", "dialog": "File > Place Linked", "kind": "file_dialog",
         "skipped": "a Windows file dialog: left to the work pass"},
    ])
    _jsonl(dataset / "runtime-discovery.jsonl", [
        {"dialog": "File > Place Linked", "label": "x", "kind": "dropdown", "binary": "Photoshop.exe",
         "functions": ["0x1"], "calls": 1, "via": "sampled", "anchor": "sha256:old"},
    ])

    build_maps(sweep, dataset, known={"all formats (*.*)"})

    assert _discovered(dataset) == []


def test_a_sweep_maps_each_spec_and_each_control_to_the_code_that_ran_only_for_it(tmp_path) -> None:
    sweep, dataset = tmp_path / "sweep", tmp_path / "dataset"
    sweep.mkdir(), dataset.mkdir()
    _jsonl(sweep / "timeline.jsonl", [
        {"idle": [0, 900]},
        {"t0": 1000, "t1": 1900, "kind": "menu_command", "label": "menu:2993"},
        {"t0": 2000, "t1": 4900, "kind": "menu_command", "label": "menu:1802"},
        {"t0": 3000, "t1": 3400, "kind": "checkbox", "label": "Preview", "dialog": "Image > Adjustments > Curves"},
    ])
    _jsonl(sweep / "batches-41.jsonl", [
        {"kind": "hits", "t0": 100, "t1": 350, "counts": {"Photoshop.exe!0x140000100": 9}},
        {"kind": "hits", "t0": 1000, "t1": 1250, "counts": {"Photoshop.exe!0x140001000": 4, "Photoshop.exe!0x140000100": 1}},
        {"kind": "hits", "t0": 2250, "t1": 2500, "counts": {"Photoshop.exe!0x140002000": 3}},
        {"kind": "hits", "t0": 3000, "t1": 3250, "counts": {"Photoshop.exe!0x140003000": 2}},
    ])
    # Earlier rows: Curves hooked through REA (kept); a sampled gear menu this sweep did not drive
    # again (kept: a short rerun touching one control dropped all 28 earlier Curves rows, 2026-11-24);
    # and a sampled Preview this sweep drove again, which it replaces.
    _jsonl(dataset / "runtime-discovery.jsonl", [
        {"dialog": "Image > Adjustments > Curves", "label": "gear menu", "kind": "flyout_menu", "binary": "Photoshop.exe",
         "functions": ["0x140009000"], "calls": 1, "via": "runtime", "anchor": "ev_hooks"},
        {"dialog": "Image > Adjustments > Curves", "label": "gear menu", "kind": "flyout_menu", "binary": "Photoshop.exe",
         "functions": ["0x140008000"], "calls": 1, "via": "sampled", "anchor": "sha256:old"},
        {"dialog": "Image > Adjustments > Curves", "label": "Preview", "kind": "checkbox", "binary": "Photoshop.exe",
         "functions": ["0x140007000"], "calls": 1, "via": "sampled", "anchor": "sha256:old"},
    ])

    summary = build_maps(sweep, dataset, known={"preview"})

    features = [json.loads(l) for l in (dataset / "feature-code.jsonl").read_text(encoding="utf-8").splitlines()]
    # A control acted on inside a command's window is part of that feature too.
    assert [(f["item_id"], f["variants"], f["binary"], f["functions"]) for f in features] == [
        ("menu:1802", ["menu:1802"], "Photoshop.exe", ["0x140002000", "0x140003000"]),
        ("menu:2993", ["menu:2993"], "Photoshop.exe", ["0x140001000"]),
    ]
    found = [json.loads(l) for l in (dataset / "runtime-discovery.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["label"], r["via"], r["functions"]) for r in found] == [
        ("gear menu", "runtime", ["0x140009000"]),
        ("gear menu", "sampled", ["0x140008000"]),
        ("Preview", "sampled", ["0x140003000"]),
    ]
    assert found[2]["anchor"].startswith("sha256:") and found[2]["anchor"] == features[0]["anchor"]
    assert summary == {"specs": 2, "features_with_code": 2, "controls": 1, "controls_with_code": 1, "functions_observed": 3}


def test_a_features_code_is_what_ran_only_for_it_in_any_of_its_variants(tmp_path) -> None:
    """A filter applied on the chart and again on a mask runs the same code: counted per spec,
    that code was in two specs and belonged to neither, so the more states a feature ran in, the
    less code it kept (pass B and C, 2026-11-25). Code shared with another feature still counts
    for neither."""
    sweep, dataset = tmp_path / "sweep", tmp_path / "dataset"
    sweep.mkdir(), dataset.mkdir()
    _jsonl(sweep / "timeline.jsonl", [
        {"idle": [0, 900]},
        {"t0": 1000, "t1": 1900, "kind": "image_effect", "label": "menu:1802@chart"},
        {"t0": 2000, "t1": 2900, "kind": "state_retry", "label": "menu:1802@chart@mask"},
        {"t0": 3000, "t1": 3900, "kind": "dialog_controls", "label": "menu:1802@controls"},
        {"t0": 3100, "t1": 3400, "kind": "slider", "label": "Amount", "dialog": "Filter > Noise > Add Noise"},
        {"t0": 4000, "t1": 4900, "kind": "menu_command", "label": "menu:2993"},
    ])
    _jsonl(sweep / "batches-41.jsonl", [
        {"kind": "hits", "t0": 1000, "t1": 1250, "counts": {"Photoshop.exe!0x1": 1, "Photoshop.exe!0x9": 1}},
        {"kind": "hits", "t0": 2000, "t1": 2250, "counts": {"Photoshop.exe!0x1": 1, "Photoshop.exe!0x2": 1}},
        {"kind": "hits", "t0": 3100, "t1": 3350, "counts": {"Photoshop.exe!0x2": 1, "Photoshop.exe!0x3": 1}},
        {"kind": "hits", "t0": 4000, "t1": 4250, "counts": {"Photoshop.exe!0x9": 1}},
    ])

    build_maps(sweep, dataset, known={"amount"})

    features = [json.loads(l) for l in (dataset / "feature-code.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(f["item_id"], f["variants"], f["functions"]) for f in features] == [
        ("menu:1802", ["menu:1802@chart", "menu:1802@chart@mask", "menu:1802@controls"], ["0x1", "0x2", "0x3"]),
    ]
    assert [(r["label"], r["functions"]) for r in _discovered(dataset)] == [("Amount", ["0x3"])]
