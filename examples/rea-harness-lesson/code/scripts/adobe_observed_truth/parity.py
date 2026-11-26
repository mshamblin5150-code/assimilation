"""The parity observation each harness result names: REA's observe_native_ui, Windows edition.

Whenever the runner connects to Photoshop (at start and after each relaunch) it observes that
exact process and window through the parity server's own tool handlers
(`rea_windows_ui/src/cli.js observe`). The observation's Evidence goes to an observations file
beside the captures (it carries a screenshot of Photoshop's window, so it stays out of the
repository); every result row then records the observation's Evidence ID, or REA's projected
error (remediation included) when it failed. `cli.js bundle` turns both into one linked bundle
for REA's import_evidence_bundle.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .photoshop import Identity
from .runner import RunResult

CLI = Path(__file__).parent / "rea_windows_ui" / "src" / "cli.js"


def observe(
    identity: Identity,
    observations: Path,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Observe Photoshop's main window; what each result row records as `parity`."""
    command = [
        "node",
        str(CLI),
        "observe",
        "--exe",
        identity.executable_path,
        "--pid",
        str(identity.pid),
        "--window",
        str(identity.hwnd),
        "--evidence",
        str(observations),
    ]
    try:
        done = run(command, capture_output=True, text=True, encoding="utf-8", timeout=240)
        if done.returncode == 0:
            return json.loads(done.stdout.strip().splitlines()[-1])
        reason = done.stderr.strip() or f"exit code {done.returncode}"
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError) as error:
        reason = f"{type(error).__name__}: {error}"
    return {
        "error": {
            "source": "harness",  # REA never saw this one: its observer could not run
            "message": f"The parity observer could not run: {reason}",
            "remediation": {
                "action": "Install Node.js, run npm install in scripts/adobe_observed_truth/rea_windows_ui, "
                "build helper/ReaWindowsUi (dotnet build -c Release), then restart the runner."
            },
        }
    }


def result_row(result: RunResult, parity: dict[str, Any] | None, *, at: str) -> dict[str, Any]:
    """One results.jsonl row: the result, the parity observation of its process, and when."""
    return {**asdict(result), "parity": parity, "at": at}
