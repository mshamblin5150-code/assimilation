from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from scripts.adobe_observed_truth.decompile_watch import Job, first_analysis, job_line, logged_line

START = datetime(2026, 11, 16, 1, 5)


def _job(**overrides) -> Job:
    fields = dict(
        binary="photoshop/Photoshop.exe",
        step="decompile-all",
        started=START,
        hours=15.2,
        cpu_min=2990.0,
        mem_gb=5.9,
        journalled=0,
        procedures=None,
        first_analysis_h=41.0,
    )
    return Job(**{**fields, **overrides})


def test_a_decompile_with_nothing_journalled_is_re_analysing_and_says_when_functions_should_start() -> None:
    # REA's decompile-all reimports the binary and reruns Ghidra's analysis before writing any
    # function: Photoshop.exe sat at 0 functions for 15 h on 2026-11-16, busy, not stuck.
    line = job_line(_job(), previous_cpu_min=2930.0, minutes_since=60)

    assert line == (
        "  photoshop/Photoshop.exe  decompile-all  15.2 h; ghidra cpu 2990 min (+60), 5.9 GB;"
        " re-analysing before decompiling (first analysis took 41 h: functions expected about 2026-11-17 18:05)"
    )


def test_a_decompile_writing_functions_reports_how_far_through_it_is() -> None:
    line = job_line(_job(journalled=48505, procedures=240107), previous_cpu_min=2935.0, minutes_since=60)

    assert line.endswith("; decompiling: 48,505 of 240,107 functions (20%)")


def test_little_cpu_over_a_long_interval_is_flagged_as_a_possible_stall() -> None:
    line = job_line(_job(), previous_cpu_min=2987.0, minutes_since=60)

    assert line.endswith("  STALL?")


def test_a_short_interval_is_too_short_to_call_a_stall() -> None:
    assert not job_line(_job(), previous_cpu_min=2989.0, minutes_since=2).endswith("STALL?")


def test_a_new_job_has_no_cpu_gain_yet() -> None:
    assert "(+n/a (new))" in job_line(_job(step="analyze"), previous_cpu_min=None, minutes_since=None)


def test_the_first_analysis_runs_from_its_stderr_being_created_to_its_result_being_written(tmp_path: Path) -> None:
    # Photoshop.exe 2026-11-16: analyze.err holds a warning written at the end, so its last-write
    # time is the end, not the start; the watcher reported "took -0 h".
    stderr, result = tmp_path / "analyze.err", tmp_path / "analyze.json"
    stderr.write_text("", encoding="utf-8")
    result.write_text(json.dumps({"normalized_result": {"procedure_count": 7}}), encoding="utf-8")
    created = stderr.stat().st_birthtime
    os.utime(result, (created + 7200, created + 7200))
    os.utime(stderr, (created + 7201, created + 7201))  # the late warning

    assert first_analysis(tmp_path) == (7, 2.0)


def test_a_failed_result_whose_pseudocode_is_all_on_disk_is_reported_as_done() -> None:
    line = "FAIL   468.4 min     62.5 MB illustrator/Support Files\\Contents\\Windows\\Illustrator.exe"

    assert logged_line("decompile-large.log", line, decompiled=True) == (
        "  logged: decompile-large.log : done, pseudocode all on disk (REA's result failed): " + line
    )
    assert logged_line("decompile-large.log", line, decompiled=False) == (
        "  logged: decompile-large.log : " + line
    )
