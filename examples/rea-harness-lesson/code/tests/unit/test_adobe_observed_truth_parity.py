from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.adobe_observed_truth.parity import observe, result_row
from scripts.adobe_observed_truth.photoshop import Identity
from scripts.adobe_observed_truth.runner import RunResult

IDENTITY = Identity("27.11", "20261101.r.1", r"C:\Apps\Photoshop.exe", "c" * 64, 900, 55)


def _answering(stdout: str, returncode: int = 0, stderr: str = ""):
    calls: list[list[str]] = []

    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    return run, calls


def test_the_parity_observation_of_photoshop_is_asked_for_its_exact_process_and_window() -> None:
    parity = {"evidence_id": "ev_" + "a" * 64, "pid": 900, "window_id": 55, "launch_time": 1762700000.25}
    run, calls = _answering(json.dumps(parity) + "\n")

    answer = observe(IDENTITY, Path("obs.jsonl"), run=run)

    assert answer == parity
    command = calls[0]
    assert [command[command.index(flag) + 1] for flag in ("--exe", "--pid", "--window", "--evidence")] == [
        r"C:\Apps\Photoshop.exe",
        "900",
        "55",
        "obs.jsonl",
    ]


def test_reas_error_for_a_failed_observation_is_kept_as_it_came() -> None:
    error = {"code": "capability_unavailable", "remediation": {"action": "Run the harness unelevated."}}
    run, _ = _answering(json.dumps({"error": error}) + "\n")

    assert observe(IDENTITY, Path("obs.jsonl"), run=run) == {"error": error}


def test_an_observer_that_could_not_run_is_recorded_as_the_harness_own_error() -> None:
    run, _ = _answering("", returncode=1, stderr="Cannot find module 'rea-agents'")

    answer = observe(IDENTITY, Path("obs.jsonl"), run=run)

    assert answer["error"]["source"] == "harness"
    assert "rea-agents" in answer["error"]["message"]


def test_each_result_row_names_the_parity_observation_of_its_photoshop_process() -> None:
    parity = {"evidence_id": "ev_" + "a" * 64}

    row = result_row(RunResult("menu:2993", "ok"), parity, at="2026-11-09T12:18:45")

    assert (row["item_id"], row["parity"], row["at"]) == ("menu:2993", parity, "2026-11-09T12:18:45")
