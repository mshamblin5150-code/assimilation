from __future__ import annotations

import pytest

from scripts.adobe_observed_truth.families import ScenarioSpec
from scripts.adobe_observed_truth.idle import Interrupted
from scripts.adobe_observed_truth.runner import (
    Blocked,
    Refused,
    RunResult,
    done_items,
    execute,
    looks_stuck,
    plan_queue,
    run_session,
)


def spec(item_id: str, safety: str = "run", steps: tuple = ()) -> ScenarioSpec:
    return ScenarioSpec(item_id, "menu_command", safety, steps=steps)  # type: ignore[arg-type]


EXIT = spec("menu:exit", steps=(("run_menu_command", 1), ("wait_for_app_exit",), ("relaunch_app",)))


def test_the_queue_skips_finished_and_unrunnable_items_and_puts_quitting_last() -> None:
    specs = [
        EXIT,
        spec("menu:1"),
        spec("menu:2"),
        spec("pref:x", safety="observed"),
        spec("submenu:Edit", safety="covered_by_items"),
        spec("menu:3"),
    ]

    queue = plan_queue(specs, done={"menu:2"})

    assert [s.item_id for s in queue] == ["menu:1", "menu:3", "menu:exit"]


class FakeAdapter:
    """Records every step; can fail on one step name; answers record steps with their kinds."""

    def __init__(self, fail_on: str | None = None, error: Exception | None = None) -> None:
        self.calls: list[tuple] = []
        self.fail_on, self.error = fail_on, error

    def step(self, name: str, *args: object) -> object:
        self.calls.append((name, *args))
        if name == self.fail_on:
            raise self.error or RuntimeError(f"{name} refused")
        return {kind: f"<{kind}>" for kind in args} if name == "record" else None


GUARDED = ScenarioSpec(
    "menu:1134",
    "menu_command_sandboxed",
    "run",
    steps=(
        ("new_throwaway_document",),
        ("snapshot_documents",),
        ("run_menu_command", 1134),
        ("record", "dialogs", "history"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    ),
)
CLEANUP = [("cancel_dialogs",), ("close_new_documents",), ("close_throwaway_document",)]


def test_a_spec_runs_its_steps_in_order_and_returns_what_it_recorded() -> None:
    adapter = FakeAdapter()

    result = execute(GUARDED, adapter)

    assert adapter.calls == list(GUARDED.steps)
    assert (result.status, result.observations) == (
        "ok",
        {"dialogs": "<dialogs>", "history": "<history>"},
    )


def test_a_failed_step_still_runs_every_clean_up_step_after_it() -> None:
    adapter = FakeAdapter(fail_on="run_menu_command")

    result = execute(GUARDED, adapter)

    assert adapter.calls[3:] == CLEANUP
    assert (result.status, result.error) == ("failed", "RuntimeError: run_menu_command refused")


def test_a_failed_brush_stroke_still_writes_the_persons_brush_options_back() -> None:
    from scripts.adobe_observed_truth.brush_probe import brush_specs

    spec = brush_specs()[0]
    adapter = FakeAdapter(fail_on="brush_stroke")

    execute(spec, adapter)

    assert [c[0] for c in adapter.calls] == ["brush_canvas", "brush_stroke", "brush_restore", "close_throwaway_document"]


def test_a_failed_bucket_fill_still_writes_the_persons_tool_state_back() -> None:
    from scripts.adobe_observed_truth.selection_probe import selection_specs

    spec = next(s for s in selection_specs() if s.item_id.startswith("bucket:"))
    adapter = FakeAdapter(fail_on="bucket_click")

    execute(spec, adapter)

    assert [c[0] for c in adapter.calls][-2:] == ["restore_tool_state", "close_throwaway_document"]


def test_a_failed_steps_traceback_goes_to_the_log(capsys) -> None:
    # Three dialogs kept failing on a shape mismatch, and only its last line was logged: the
    # comparison that raised it could not be told from the one already fixed (2026-11-24).
    execute(GUARDED, FakeAdapter(fail_on="run_menu_command"))

    logged = capsys.readouterr()
    assert "Traceback" in logged.out and "run_menu_command refused" in logged.out


def test_coming_back_mid_spec_stops_it_and_still_cleans_up() -> None:
    adapter = FakeAdapter()
    checks = iter([False, False, True])

    result = execute(GUARDED, adapter, should_stop=lambda: next(checks, True))

    assert adapter.calls == [("new_throwaway_document",), ("snapshot_documents",), *CLEANUP]
    assert result.status == "interrupted"


AWAY, PRESENT = 2000.0, 5.0


class Idle:
    """Replays idle readings; the last one repeats."""

    def __init__(self, *readings: float) -> None:
        self.readings = list(readings)

    def __call__(self) -> float:
        return self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]


def test_nothing_runs_while_the_person_is_present_and_each_result_is_written_as_it_finishes() -> (
    None
):
    queue = [spec("menu:1"), spec("menu:2")]
    ran: list[str] = []
    written: list[RunResult] = []
    slept: list[float] = []

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        ran.append(s.item_id)
        assert len(written) == len(ran) - 1  # the previous result is already saved
        return RunResult(s.item_id, "ok")

    run_session(
        queue,
        run_one,
        Idle(PRESENT, PRESENT, AWAY),
        threshold_s=1200,
        sleep=slept.append,
        write=written.append,
    )

    assert len(slept) == 2
    assert ran == ["menu:1", "menu:2"]
    assert [r.item_id for r in written] == ["menu:1", "menu:2"]


def test_a_spec_interrupted_by_the_person_returning_is_retried_not_recorded() -> None:
    queue = [spec("menu:1"), spec("menu:2")]
    outcomes = iter(["interrupted", "ok", "ok"])
    ran: list[str] = []
    written: list[RunResult] = []

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        ran.append(s.item_id)
        return RunResult(s.item_id, next(outcomes))  # type: ignore[arg-type]

    run_session(
        queue, run_one, Idle(AWAY), threshold_s=1200, sleep=lambda _: None, write=written.append
    )

    assert ran == ["menu:1", "menu:1", "menu:2"]
    assert [(r.item_id, r.status) for r in written] == [("menu:1", "ok"), ("menu:2", "ok")]


def test_resuming_counts_the_latest_result_per_item_and_survives_a_half_written_line() -> None:
    lines = [
        '{"item_id": "menu:1", "status": "failed"}',
        '{"item_id": "menu:2", "status": "ok"}',
        '{"item_id": "menu:1", "status": "ok"}',
        '{"item_id": "menu:3", "status": "failed"}',
        '{"item_id": "menu:4", "sta',
    ]

    assert done_items(lines, retry_failed=False) == {"menu:1", "menu:2", "menu:3"}
    assert done_items(lines, retry_failed=True) == {"menu:1", "menu:2"}


def test_every_step_the_families_can_generate_has_a_runner_handler() -> None:
    from scripts.adobe_observed_truth.families import scenarios_for
    from scripts.adobe_observed_truth.inventory import Item
    from scripts.adobe_observed_truth.runner_photoshop import PhotoshopAdapter

    def menu(path: str) -> Item:
        return Item("menu_command", "menu:1", path.rsplit(" > ", 1)[-1], path, {"command": 1})

    def key(command: str) -> Item:
        facts = {"keys": "Ctrl+J", "command": command, "set": "x"}
        return Item("shortcut", "shortcut:Ctrl+J", "Ctrl+J", "x", facts)

    items = [
        menu("Image > Duplicate"),
        menu("File > Close and Go to Bridge"),
        menu("View > Rulers"),
        menu("File > Save As"),
        menu("File > Exit"),
        menu("Window > Workspace > Painting"),
        menu("Help > Photoshop Help"),
        menu("Edit > Generative Fill"),
        menu("Filter > Blur > Gaussian Blur"),
        key("Layer via Copy"),
        key("Save As..."),
        key("Generative Workspace..."),
        Item("tool", "tool:a", "A Tool", "x", {"tool_id": "a", "shortcut": "B"}),
        Item("tool", "tool:b", "B Tool", "x", {"tool_id": "b", "shortcut": None}),
        Item("panel", "panel:p", "P", "Window > P", {}),
    ]
    steps = {str(s[0]) for item in items for s in scenarios_for(item, sandbox=True).steps}

    assert {name for name in steps if not hasattr(PhotoshopAdapter, f"_{name}")} == set()


class InterruptingAdapter(FakeAdapter):
    def step(self, name: str, *args: object) -> object:
        self.calls.append((name, *args))
        if name == "run_menu_command":
            raise Interrupted("the person is back")
        return None


def test_the_person_returning_mid_step_is_an_interruption_not_a_failure() -> None:
    adapter = InterruptingAdapter()

    result = execute(GUARDED, adapter)

    assert result.status == "interrupted"
    assert adapter.calls[3:] == CLEANUP


def test_clean_up_never_relaunches_photoshop_while_the_person_is_there() -> None:
    quitting = ScenarioSpec(
        "menu:exit",
        "menu_command_sandboxed",
        "run",
        steps=(("run_menu_command", 1), ("wait_for_app_exit",), ("relaunch_app",)),
    )
    adapter = FakeAdapter(fail_on="wait_for_app_exit")

    execute(quitting, adapter, should_stop=lambda: True)

    assert ("relaunch_app",) not in adapter.calls


def test_ctrl_c_still_cleans_up_before_stopping() -> None:
    class CtrlC(FakeAdapter):
        def step(self, name: str, *args: object) -> object:
            self.calls.append((name, *args))
            if name == "run_menu_command":
                raise KeyboardInterrupt
            return None

    adapter = CtrlC()

    with pytest.raises(KeyboardInterrupt):
        execute(GUARDED, adapter)

    assert adapter.calls[3:] == CLEANUP


# What a hung Photoshop answers over COM (seen live, 2026-11-09).
BUSY = "com_error: (-2147417846, 'The message filter indicated that the application is busy.')"


def outcomes(*statuses: str) -> object:
    """run_one that answers with these statuses in turn (the last repeats)."""
    remaining = list(statuses)
    ran: list[str] = []

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        ran.append(s.item_id)
        status = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        if status == "raise":
            raise RuntimeError("preflight: a dialog is open")
        error = None if status == "ok" else BUSY if status == "failed" else status
        return RunResult(s.item_id, status, error=error)  # type: ignore[arg-type]

    run_one.ran = ran  # type: ignore[attr-defined]
    return run_one


class HangingPhotoshop:
    """Some specs hang Photoshop: every spec then fails until it is restarted."""

    def __init__(self, *hangs: str) -> None:
        self.hangs, self.stuck, self.ran = set(hangs), False, []

    def run_one(self, s: ScenarioSpec, should_stop: object) -> RunResult:
        self.ran.append(s.item_id)
        if self.stuck or s.item_id in self.hangs:
            self.stuck = True
            return RunResult(s.item_id, "failed", error=BUSY)
        return RunResult(s.item_id, "ok")

    def recover(self) -> None:
        self.stuck = False


def test_a_probe_that_hangs_photoshop_is_recorded_and_the_rest_are_retried() -> None:
    photoshop = HangingPhotoshop("menu:1")
    written: list[RunResult] = []

    stopped = run_session(
        [spec(f"menu:{n}") for n in range(1, 6)],
        photoshop.run_one,
        Idle(AWAY),
        threshold_s=1200,
        sleep=lambda _: None,
        write=written.append,
        recover=photoshop.recover,
    )

    assert [(r.item_id, r.status) for r in written] == [
        ("menu:1", "failed"),
        ("menu:2", "ok"),
        ("menu:3", "ok"),
        ("menu:4", "ok"),
        ("menu:5", "ok"),
    ]
    assert stopped is None


def test_several_separate_hangs_in_one_night_do_not_stop_it() -> None:
    photoshop = HangingPhotoshop("menu:1", "menu:5", "menu:9")
    written: list[RunResult] = []

    stopped = run_session(
        [spec(f"menu:{n}") for n in range(1, 12)],
        photoshop.run_one,
        Idle(AWAY),
        threshold_s=1200,
        sleep=lambda _: None,
        write=written.append,
        recover=photoshop.recover,
    )

    assert stopped is None
    assert sorted(r.item_id for r in written if r.status == "failed") == [
        "menu:1",
        "menu:5",
        "menu:9",
    ]


def test_a_session_that_keeps_failing_after_restarts_stops_and_says_why() -> None:
    queue = [spec(f"menu:{n}") for n in range(10)]
    written: list[RunResult] = []
    recoveries: list[str] = []

    stopped = run_session(
        queue,
        outcomes("failed"),
        Idle(AWAY),
        threshold_s=1200,
        sleep=lambda _: None,
        write=written.append,
        recover=lambda: recoveries.append("restart"),
    )

    assert len(recoveries) == 2
    assert stopped is not None and "failed" in stopped
    assert all(r.status == "failed" for r in written) and written


def test_an_error_outside_a_spec_is_a_failed_result_not_a_crash() -> None:
    written: list[RunResult] = []

    run_session(
        [spec("menu:1"), spec("menu:2")],
        outcomes("raise", "ok"),
        Idle(AWAY),
        threshold_s=1200,
        sleep=lambda _: None,
        write=written.append,
        recover=lambda: None,
    )

    assert [(r.item_id, r.status) for r in written] == [("menu:1", "failed"), ("menu:2", "ok")]
    assert "preflight" in (written[0].error or "")


class RefusingAdapter(FakeAdapter):
    def step(self, name: str, *args: object) -> object:
        self.calls.append((name, *args))
        if name == "run_menu_command":
            raise Refused("Could not complete the Equalize command")
        return None


def test_photoshop_refusing_a_command_is_an_observation_not_a_failure() -> None:
    adapter = RefusingAdapter()

    result = execute(GUARDED, adapter)

    assert (result.status, result.error) == ("refused", "Could not complete the Equalize command")
    assert adapter.calls[3:] == CLEANUP


def test_refusals_never_count_toward_restarting_photoshop() -> None:
    written: list[RunResult] = []
    recoveries: list[str] = []

    run_session(
        [spec(f"menu:{n}") for n in range(5)],
        outcomes("refused"),
        Idle(AWAY),
        threshold_s=1200,
        sleep=lambda _: None,
        write=written.append,
        recover=lambda: recoveries.append("restart"),
    )

    assert recoveries == []
    assert [r.status for r in written] == ["refused"] * 5


def test_asking_the_runner_to_stop_ends_it_between_probes_never_mid_probe() -> None:
    written: list[RunResult] = []
    stop_after = iter([False, False, True])

    stopped = run_session(
        [spec(f"menu:{n}") for n in range(5)],
        outcomes("ok"),
        Idle(AWAY),
        threshold_s=1200,
        sleep=lambda _: None,
        write=written.append,
        should_quit=lambda: next(stop_after),
    )

    assert [r.item_id for r in written] == ["menu:0", "menu:1"]
    assert stopped == "stopped: asked to stop"


def test_a_spec_blocked_by_the_persons_own_document_waits_and_never_restarts_photoshop() -> None:
    blocked = iter([True, True, True, True, False])
    slept: list[float] = []
    recoveries: list[str] = []
    written: list[RunResult] = []

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        if next(blocked):
            return RunResult(s.item_id, "blocked", error="1 document not opened by the harness")
        return RunResult(s.item_id, "ok")

    run_session(
        [spec("menu:1")], run_one, Idle(AWAY), threshold_s=1200, sleep=slept.append,
        write=written.append, recover=lambda: recoveries.append("restart"),
    )

    assert recoveries == []
    assert len(slept) == 4  # waits a poll each time, no busy loop
    assert [(r.item_id, r.status) for r in written] == [("menu:1", "ok")]

def test_a_restart_that_refuses_stops_the_session_instead_of_crashing_it() -> None:
    def refuse() -> None:
        raise RuntimeError("will not restart Photoshop: a document of the person's may be open")

    stopped = run_session(
        [spec(f"menu:{n}") for n in range(3)],
        lambda s, stop: RunResult(s.item_id, "failed", error="TimeoutError"),
        Idle(AWAY), threshold_s=1200, sleep=lambda _: None, write=lambda r: None,
        recover=refuse,
    )

    assert stopped == (
        "stopped: could not restart Photoshop: "
        "will not restart Photoshop: a document of the person's may be open"
    )


def test_a_blocked_spec_waits_at_the_back_so_the_specs_behind_it_still_run() -> None:
    ran: list[str] = []

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        ran.append(s.item_id)
        if s.item_id == "menu:1" and ran.count("menu:1") == 1:
            return RunResult(s.item_id, "blocked", error="1 document not opened by the harness")
        return RunResult(s.item_id, "ok")

    run_session(
        [spec("menu:1"), spec("menu:2")], run_one, Idle(AWAY), threshold_s=1200,
        sleep=lambda _: None, write=lambda r: None,
    )

    assert ran == ["menu:1", "menu:2", "menu:1"]


def test_a_blocked_spec_touches_nothing_not_even_its_clean_up() -> None:
    adapter = FakeAdapter(fail_on="require_only_harness_documents", error=Blocked("1 document"))

    result = execute(
        spec("menu:1", steps=(("require_only_harness_documents",), ("cancel_dialogs",))), adapter
    )

    assert (result.status, adapter.calls) == ("blocked", [("require_only_harness_documents",)])


def test_failures_where_photoshop_was_never_stuck_are_written_and_never_restart_it() -> None:
    # 2026-11-09: panels with no Window menu command failed in a row, restarted Photoshop twice
    # and stopped the night, though Photoshop was never even asked.
    recoveries: list[str] = []
    written: list[RunResult] = []
    gap = "NotImplementedError: no Window menu command shows panelid.static.textcharacter"

    stopped = run_session(
        [spec(f"panel:{n}") for n in range(5)],
        lambda s, stop: RunResult(s.item_id, "failed", error=gap),
        Idle(AWAY), threshold_s=1200, sleep=lambda _: None, write=written.append,
        recover=lambda: recoveries.append("restart"),
    )

    assert (stopped, recoveries, len(written)) == (None, [], 5)


def test_only_timeouts_and_a_busy_or_vanished_photoshop_look_stuck() -> None:
    assert looks_stuck("TimeoutError: Photoshop's helper did not answer menu_command within 90 s")
    assert looks_stuck("com_error: (-2147417846, 'The message filter indicated that the application is busy.')")
    assert looks_stuck("com_error: (-2147023174, 'The RPC server is unavailable.')")
    assert not looks_stuck("NotImplementedError: no Window menu command shows panelid.static.options")
    assert not looks_stuck(None)


def test_a_dialog_left_open_that_blocks_every_next_probe_looks_stuck() -> None:
    # 2026-11-23: About Photoshop, interrupted before its Escape, stayed open; the next 1,432
    # specs each refused to start behind it and were recorded failed. Stuck: restart instead.
    assert looks_stuck("RuntimeError: menu:4002 not started: Photoshop has a dialog open: ")


def test_a_probe_interrupted_again_and_again_while_the_person_stays_away_is_recorded_not_retried() -> None:
    # 2026-11-09: pressing Alt+Ctrl+G opened Google Drive's search box (its global hotkey), which
    # took the foreground; the probe was retried 13 times until stopped by hand.
    tries: list[str] = []
    written: list[RunResult] = []
    stolen = "Foreground left the target process before KeyUp(key='g')."

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        tries.append(s.item_id)
        return RunResult(s.item_id, "interrupted", error=stolen)

    run_session(
        [spec("shortcut:Alt+Ctrl+G")], run_one, Idle(AWAY), threshold_s=1200,
        sleep=lambda _: None, write=written.append,
    )

    assert len(tries) == 3
    assert [(r.status, r.error) for r in written] == [
        ("failed", f"interrupted 3 times while the person was away (another program?): {stolen}")
    ]


def test_what_an_interrupted_probe_left_open_is_tidied_before_the_next_one() -> None:
    # 2026-11-23: the person came back mid About Photoshop, so its Escape was rightly not sent;
    # once they were away again nothing closed it. Tidy once, before the next probe runs.
    events: list[str] = []

    def run_one(s: ScenarioSpec, should_stop: object) -> RunResult:
        events.append(s.item_id)
        status = "interrupted" if s.item_id == "menu:1" and events.count("menu:1") == 1 else "ok"
        return RunResult(s.item_id, status)

    run_session(
        [spec("menu:1"), spec("menu:2")], run_one, Idle(AWAY), threshold_s=1200,
        sleep=lambda _: None, write=lambda r: None, tidy=lambda: events.append("tidy"),
    )

    assert events == ["menu:1", "tidy", "menu:1", "menu:2"]