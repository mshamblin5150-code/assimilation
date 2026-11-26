"""Work through the probe specs while the person is away, and give the machine back when they return.

Three parts, each testable alone: plan_queue (what to run next), execute (one spec's steps,
with clean-up that always runs), and run_session (the idle-gated loop that writes each result
as it finishes, so an interrupted night resumes where it stopped).
"""

from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from .families import ScenarioSpec, Step
from .idle import Interrupted

QUITS_APP = ("relaunch_app",)
# Steps that undo what a spec did; they run even after a failure or an interruption.
CLEANUP_STEPS = frozenset(
    {
        "cancel_dialogs",
        "close_new_documents",
        "restore_workspace",
        "restore_panels",
        "close_throwaway_document",
        "toggle_back",
        "close_new_program_windows",
        "relaunch_app",
        "brush_restore",  # the person's brush options and colours, written back
        "restore_tool_state",  # the same, for the tool a save_tool_state step kept
        "delete_own_tip",  # the harness's own brush tip preset, deleted by name
        "delete_own_pattern",  # the harness's own pattern, deleted by name
        "restore_brush_panel",  # the Brush Settings panel back on its first page, closed if the run opened it
        "restore_pencil_fidelity",  # the person's Pencil Fidelity stop, set back through its dialog
    }
)


class Refused(Exception):
    """Photoshop declined the command ("Could not complete..."): what it does, not a fault."""


class Blocked(Exception):
    """The spec must not run yet (a document of the person's is open); nothing was done."""


class Adapter(Protocol):
    def step(self, name: str, *args: Any) -> Any: ...


@dataclass
class RunResult:
    item_id: str
    status: Literal["ok", "refused", "failed", "interrupted", "blocked"]
    observations: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cleanup_errors: list[str] = field(default_factory=list)


def execute(
    spec: ScenarioSpec, adapter: Adapter, should_stop: Callable[[], bool] = lambda: False
) -> RunResult:
    """Run one spec's steps; whatever happens, even Ctrl+C, run the clean-up steps that remain."""
    result = RunResult(spec.item_id, "ok")
    for index, step in enumerate(spec.steps):
        name = str(step[0])
        if name in CLEANUP_STEPS:
            _clean(adapter, step, result, should_stop)
            continue
        try:
            if should_stop():
                raise Interrupted("the person is back")
            answer = adapter.step(name, *step[1:])
        except Interrupted as stop:
            result.status, result.error = "interrupted", str(stop)
        except Refused as declined:
            result.status, result.error = "refused", str(declined)
        except Blocked as wait:  # nothing was done, so nothing to undo: touch nothing
            result.status, result.error = "blocked", str(wait)
            return result
        except Exception as error:  # noqa: BLE001 - any failure ends the spec, then clean up
            result.status, result.error = "failed", f"{type(error).__name__}: {error}"
            traceback.print_exc(file=sys.stdout)  # the log, not the result: where it was raised
        except BaseException:  # Ctrl+C: clean up, then stop
            _clean_remaining(adapter, spec.steps[index + 1 :], result, should_stop)
            raise
        else:
            if name == "record" and isinstance(answer, dict):
                result.observations.update(answer)
            continue
        _clean_remaining(adapter, spec.steps[index + 1 :], result, should_stop)
        return result
    return result


def run_session(
    queue: list[ScenarioSpec],
    run_one: Callable[[ScenarioSpec, Callable[[], bool]], RunResult],
    idle_s: Callable[[], float],
    *,
    threshold_s: float,
    sleep: Callable[[float], None],
    write: Callable[[RunResult], None],
    recover: Callable[[], None] = lambda: None,
    should_quit: Callable[[], bool] = lambda: False,
    tidy: Callable[[], None] = lambda: None,
    poll_s: float = 30.0,
    failures_before_recovery: int = 3,
    max_recoveries: int = 2,
    max_interruptions: int = 3,
) -> str | None:
    """Run the queue only while the person is away; return why it stopped early, if it did.

    An interrupted spec is retried. Failures in a row usually mean Photoshop itself is stuck or
    gone, so after `failures_before_recovery` of them it is restarted (`recover`): the first of
    them, the likely culprit, is recorded as failed and the rest run again. Failures that persist
    through `max_recoveries` restarts in a row stop the session.

    An interrupted spec's own clean-up is not sent once the person is back (their desktop), so
    what it left open is closed by `tidy` once they are away again, before the next spec.
    """
    pending = list(queue)
    streak: list[tuple[ScenarioSpec, RunResult]] = []
    recoveries = 0
    interruptions: dict[str, int] = {}  # per spec, while the person stayed away
    untidy = False

    def person_is_back() -> bool:
        return idle_s() < threshold_s

    while pending:
        if should_quit():  # checked between probes only, so Photoshop is never left mid-command
            for _, failed in streak:
                write(failed)
            return "stopped: asked to stop"
        if person_is_back():
            sleep(poll_s)
            continue
        if untidy:
            untidy = False
            try:
                tidy()
            except Exception as error:  # noqa: BLE001 - what stays open will show as stuck
                print(f"tidying after an interrupted spec failed: {type(error).__name__}: {error}")
        spec = pending.pop(0)
        try:
            result = run_one(spec, person_is_back)
        except Exception as error:  # noqa: BLE001 - outside a spec, still just one failed spec
            result = RunResult(spec.item_id, "failed", error=f"{type(error).__name__}: {error}")
        if result.status == "interrupted":
            untidy = True
            if not person_is_back():  # nobody came back: something else took the foreground
                interruptions[spec.item_id] = interruptions.get(spec.item_id, 0) + 1
                if interruptions[spec.item_id] >= max_interruptions:
                    result.status = "failed"
                    result.error = (
                        f"interrupted {max_interruptions} times while the person was away "
                        f"(another program?): {result.error}"
                    )
                    write(result)
                    continue
            pending.insert(0, spec)  # runs again next time they are away
            continue
        if result.status == "blocked":  # the person's own work is open: wait, never count it
            pending.append(spec)  # specs that need no such check run meanwhile
            sleep(poll_s)
            continue
        if result.status == "failed" and not looks_stuck(result.error):
            write(result)  # a real failure, but nothing says Photoshop stopped answering
            continue
        if result.status in ("ok", "refused"):  # Photoshop answered: it is not stuck
            for _, failed in streak:  # a later success shows those failures were genuine
                write(failed)
            streak.clear()
            recoveries = 0  # Photoshop works again: the next hang gets its own restarts
            write(result)
            continue
        streak.append((spec, result))
        if len(streak) < failures_before_recovery:
            continue
        if recoveries >= max_recoveries:
            for _, failed in streak:
                write(failed)
            return (
                f"stopped: {len(streak)} specs failed in a row after {recoveries} Photoshop "
                f"restarts; last error: {result.error}"
            )
        recoveries += 1
        try:
            recover()
        except Exception as error:  # noqa: BLE001 - a refused restart ends the night cleanly
            for _, failed in streak:
                write(failed)
            return f"stopped: could not restart Photoshop: {error}"
        # The first failure most likely hung Photoshop (About sat modal): record it, retry the rest.
        culprit = streak[0][1]
        culprit.error = f"{culprit.error} (Photoshop stopped answering after this; restarted)"
        write(culprit)
        pending[0:0] = [s for s, _ in streak[1:]]
        streak.clear()
    for _, failed in streak:
        write(failed)
    return None


_STUCK_SIGNS = (
    "TimeoutError",  # a command never returned
    "application is busy",  # COM refused: Photoshop is modal or hung
    "-2147417846",
    "RPC server is unavailable",  # Photoshop vanished
    "-2147023174",
    "remote procedure call failed",
    "-2147023170",
    "not started: Photoshop has a dialog open",  # one left open blocks every probe after it
)


def looks_stuck(error: str | None) -> bool:
    """Whether a failure says Photoshop stopped answering; only those count toward a restart."""
    return error is not None and any(sign in error for sign in _STUCK_SIGNS)


def _clean(
    adapter: Adapter, step: Step, result: RunResult, should_stop: Callable[[], bool]
) -> None:
    if step[0] == "relaunch_app" and should_stop():
        result.cleanup_errors.append("relaunch_app: deferred, the person is back")
        return
    try:
        adapter.step(str(step[0]), *step[1:])
    except Exception as error:  # noqa: BLE001 - one failed clean-up must not skip the rest
        result.cleanup_errors.append(f"{step[0]}: {type(error).__name__}: {error}")


def _clean_remaining(
    adapter: Adapter, steps: tuple[Step, ...], result: RunResult, should_stop: Callable[[], bool]
) -> None:
    for step in steps:
        if step[0] in CLEANUP_STEPS:
            _clean(adapter, step, result, should_stop)


def done_items(lines: Iterable[str], *, retry_failed: bool) -> set[str]:
    """Items not to run again: the latest result per item counts; failures too unless retried.

    A line cut short (the runner stopped mid-write) is skipped, so it cannot block a resume.
    """
    latest: dict[str, str] = {}
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        latest[record["item_id"]] = record["status"]
    return {item for item, status in latest.items() if status == "ok" or not retry_failed}


def plan_queue(specs: list[ScenarioSpec], done: set[str]) -> list[ScenarioSpec]:
    """Runnable specs not yet finished, in order, with anything that quits the app last."""
    pending = [s for s in specs if s.safety == "run" and s.item_id not in done]
    return [s for s in pending if QUITS_APP not in s.steps] + [
        s for s in pending if QUITS_APP in s.steps
    ]
