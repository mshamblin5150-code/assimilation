from __future__ import annotations

import json
from pathlib import Path

from scripts.adobe_observed_truth.rea_corpus import decompile_queue, is_decompiled, is_skipped, resume_flag


def _work_dir(tmp_path: Path, procedures: int, journalled: int, summary: str) -> Path:
    """A binary's work folder: the analysis found `procedures`; the journal recorded
    `journalled` of them; decompile-all ended as `summary` ("ok", "failed" or "running")."""
    (tmp_path / "pseudocode").mkdir()
    (tmp_path / "analyze.json").write_text(
        json.dumps({"normalized_result": {"procedure_count": procedures}}), encoding="utf-8"
    )
    lines = [{"kind": "header", "version": 1}]
    lines += [{"kind": "function", "address": hex(n), "status": "written"} for n in range(journalled)]
    (tmp_path / "pseudocode" / "decompile-journal.jsonl").write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8"
    )
    if summary == "ok":
        (tmp_path / "decompile-all.json").write_text("{}", encoding="utf-8")
    elif summary == "failed":
        (tmp_path / "decompile-all.failed.json").write_text(
            json.dumps({"code": "UNKNOWN", "message": "Invalid string length"}), encoding="utf-8"
        )
    return tmp_path


def test_a_binary_whose_decompile_returned_is_decompiled(tmp_path: Path) -> None:
    assert is_decompiled(_work_dir(tmp_path, procedures=3, journalled=3, summary="ok"))


def test_a_failed_summary_still_counts_when_the_journal_covers_every_procedure(tmp_path: Path) -> None:
    # Illustrator.exe 2026-11-13: all 240,107 procedures journalled, then REA could not build
    # its result ("Invalid string length"). The pseudocode on disk is complete.
    assert is_decompiled(_work_dir(tmp_path, procedures=3, journalled=3, summary="failed"))


def test_a_failed_summary_with_procedures_missing_from_the_journal_is_not_decompiled(tmp_path: Path) -> None:
    assert not is_decompiled(_work_dir(tmp_path, procedures=3, journalled=2, summary="failed"))


def test_a_decompile_still_running_is_not_decompiled(tmp_path: Path) -> None:
    assert not is_decompiled(_work_dir(tmp_path, procedures=3, journalled=3, summary="running"))


def test_a_binary_never_analysed_is_not_decompiled(tmp_path: Path) -> None:
    assert not is_decompiled(tmp_path)


def test_an_interrupted_export_is_resumed_even_before_reas_index_is_written(tmp_path: Path) -> None:
    # 2026-11-18: both adobe_c2pa.dll and LUTEngine.dll were interrupted with a journal but no
    # decompile-index.json; the retry ran without --resume and REA refused ("Output directory
    # already exists") within seconds.
    pseudocode = _work_dir(tmp_path, procedures=3, journalled=1, summary="failed") / "pseudocode"

    assert resume_flag(pseudocode) == ["--resume"]


def test_a_first_export_is_not_resumed(tmp_path: Path) -> None:
    assert resume_flag(tmp_path / "pseudocode") == []


def test_the_queue_skips_binaries_whose_pseudocode_is_all_on_disk_and_runs_smallest_first(tmp_path: Path) -> None:
    def entry(name: str, size: int, procedures: int, journalled: int, summary: str) -> dict:
        work_dir = tmp_path / name
        work_dir.mkdir()
        _work_dir(work_dir, procedures=procedures, journalled=journalled, summary=summary)
        return {"adobe": True, "relative": name, "bytes": size, "work_dir": str(work_dir)}

    entries = [
        entry("Photoshop.exe", 300, procedures=5, journalled=0, summary="failed"),
        entry("Illustrator.exe", 200, procedures=3, journalled=3, summary="failed"),  # complete
        entry("LUTEngine.dll", 30, procedures=4, journalled=1, summary="failed"),
        entry("Brushes.8bi", 10, procedures=2, journalled=2, summary="ok"),
    ]

    assert [e["relative"] for e in decompile_queue(entries, max_bytes=None)] == ["LUTEngine.dll", "Photoshop.exe"]


def test_skipped_binaries_are_never_queued_or_waited_on(tmp_path: Path) -> None:
    # 2026-11-18: both adobe_c2pa.dll copies decompiled about 19 functions an hour (a third of
    # them hitting the 5-minute cap) and held Photoshop.exe out of the memory budget. Skipped.
    work_dir = tmp_path / "c2pa"
    work_dir.mkdir()
    _work_dir(work_dir, procedures=4, journalled=1, summary="failed")
    c2pa = {"adobe": True, "relative": "Support Files\\Contents\\Windows\\adobe_c2pa.dll", "bytes": 30, "work_dir": str(work_dir)}

    assert is_skipped(c2pa)
    assert not is_skipped({**c2pa, "relative": "Photoshop.exe"})
    assert decompile_queue([c2pa], max_bytes=None) == []
