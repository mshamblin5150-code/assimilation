"""The decisions inside the live Photoshop adapter, tested without Photoshop."""

from __future__ import annotations

import pytest

from scripts.adobe_observed_truth.idle import Interrupted
from scripts.adobe_observed_truth.runner_photoshop import (
    TopWindow,
    dialog_record,
    escape_due,
    history_observation,
    hung_too_long,
    keep_watching,
    leave_mode,
    may_cancel_now,
    may_force_quit,
    new_adobe_windows,
    photoshop_refusal,
    quiet_seconds,
    wait_until,
    watchdog_should_kill,
    window_observation,
)

BEFORE = [
    TopWindow(hwnd=1, class_name="Chrome_WidgetWin_1", program="Creative Cloud.exe"),
    TopWindow(hwnd=2, class_name="Notepad", program="notepad.exe"),
]


def test_an_attended_run_stops_its_input_the_moment_the_person_types() -> None:
    """With --now the runner's idle clock always read 10^9 s, so the person typing in another
    program never counted as back and the harness kept taking the foreground (2026-11-11)."""
    from scripts.adobe_observed_truth.runner import RunResult, ScenarioSpec, run_session
    from scripts.adobe_observed_truth.runner_photoshop import away_after_s

    clock = {"idle": 60.0}  # quiet for a minute: an attended run starts at once
    seen: list[bool] = []

    def run_one(spec: ScenarioSpec, should_stop) -> RunResult:
        seen.append(should_stop())
        clock["idle"] = 1.0  # the person types
        seen.append(should_stop())
        clock["idle"] = 60.0
        return RunResult(spec.item_id, "ok")

    run_session(
        [ScenarioSpec("menu:1@controls", "dialog_controls", "run", [])],
        run_one,
        lambda: clock["idle"],
        threshold_s=away_after_s(now=True, idle_minutes=20),
        sleep=lambda s: None,
        write=lambda r: None,
    )

    assert seen == [False, True]
    assert away_after_s(now=False, idle_minutes=20) == 1200


def test_escape_is_pressed_after_8_seconds_without_a_dialog_then_every_8_more_at_most_3_times() -> (
    None
):
    assert not escape_due(waited_s=5, escapes=0)
    assert escape_due(waited_s=9, escapes=0)
    assert not escape_due(waited_s=12, escapes=1)
    assert escape_due(waited_s=17, escapes=1)
    assert not escape_due(waited_s=90, escapes=3)


def test_escape_is_never_pressed_while_the_person_is_back_or_a_dialog_is_showing() -> None:
    assert not escape_due(waited_s=30, escapes=0, person_is_back=True)
    assert not escape_due(waited_s=30, escapes=0, dialog_showing=True)


def test_an_on_canvas_mode_is_committed_once_with_a_gesture_when_ok_is_wanted_else_left() -> None:
    # Free Transform and the warps open no window: committing (drag, then Enter) is their OK.
    assert leave_mode(accepting=True, escapes=0) == "commit"
    assert leave_mode(accepting=True, escapes=1) == "escape"  # a commit that did not end it
    assert leave_mode(accepting=False, escapes=0) == "escape"


def test_only_windows_that_appeared_during_the_probe_from_other_adobe_programs_are_closed() -> None:
    now = [
        *BEFORE,
        TopWindow(hwnd=3, class_name="bridge16", program="Adobe Bridge.exe"),
        TopWindow(hwnd=4, class_name="Chrome_WidgetWin_1", program="Creative Cloud.exe"),
        TopWindow(hwnd=5, class_name="Notepad", program="notepad.exe"),
        TopWindow(hwnd=6, class_name="Photoshop", program="Photoshop.exe"),
    ]

    assert [w.hwnd for w in new_adobe_windows(before={1, 2}, now=now)] == [3, 4]


def test_waiting_for_another_program_stops_the_moment_the_person_is_back() -> None:
    with pytest.raises(Interrupted):
        wait_until(lambda: False, seconds=30, should_stop=lambda: True, sleep=lambda _: None)


def test_waiting_ends_as_soon_as_the_window_appears() -> None:
    answers = iter([False, False, True])
    slept: list[float] = []

    wait_until(lambda: next(answers), seconds=30, should_stop=lambda: False, sleep=slept.append)

    assert len(slept) == 2


def test_waiting_for_a_window_that_never_appears_gives_up_quietly() -> None:
    assert not wait_until(lambda: False, seconds=3, should_stop=lambda: False, sleep=lambda _: None)


def test_a_build_state_step_runs_that_states_script_on_the_open_chart() -> None:
    from scripts.adobe_observed_truth.document_states import STATES
    from scripts.adobe_observed_truth.runner_photoshop import PhotoshopAdapter

    class ScriptedPhotoshop:
        def __init__(self) -> None:
            self.scripts: list[str] = []

        def js(self, body: str) -> None:
            self.scripts.append(body)

    adapter = PhotoshopAdapter.__new__(PhotoshopAdapter)
    adapter.ps = ScriptedPhotoshop()

    adapter._build_state("smart_object")

    assert adapter.ps.scripts == [STATES["smart_object"]]
    with pytest.raises(KeyError):
        adapter._build_state("no such state")


def test_a_use_tool_step_sends_the_gesture_where_the_chart_is_on_screen_then_commits(monkeypatch) -> None:
    from scripts.adobe_observed_truth import runner_photoshop as rp
    from scripts.adobe_observed_truth.input_plan import KeyDown, MouseDown
    from scripts.adobe_observed_truth.tool_gestures import gesture_events

    sent: list[list] = []
    monkeypatch.setattr(rp.canvas, "read_view", lambda ps, identity: "the view")
    monkeypatch.setattr(rp.canvas, "document_to_screen", lambda view, x, y: (int(x) + 7, int(y) + 9))
    monkeypatch.setattr(rp.win_input, "focus", lambda *a, **k: None)
    monkeypatch.setattr(rp.win_input, "perform", lambda events, **k: sent.append(list(events)))

    class Front:
        def bring_to_front(self) -> None:
            pass

    class Identity:
        hwnd, pid = 1, 2

    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.ps, adapter.identity, adapter.should_stop = Front(), Identity(), lambda: False
    adapter._capture_and_cancel_dialogs = lambda: 0
    monkeypatch.setattr(rp, "keep_watching", lambda *a: False)

    adapter._use_tool("drag", "enter")

    assert sent[0] == gesture_events("drag", lambda x, y: (int(x) + 7, int(y) + 9))
    assert MouseDown() in sent[0] and sent[1] == [KeyDown("enter"), *sent[1][1:]]


def test_escape_for_a_command_still_running_takes_the_foreground_past_windows_lock(monkeypatch, tmp_path) -> None:
    # After a force-quit Chrome held the foreground; a bare SetForegroundWindow is refused from
    # a background program, so every Escape stopped at the foreground check (2026-11-24).
    from scripts.adobe_observed_truth import runner_photoshop as rp

    in_front = {"pid": 99}  # Chrome
    sent: list[tuple[int, list]] = []
    monkeypatch.setattr(rp, "dialog_record", lambda label, name, capture: {"dialog": label})
    monkeypatch.setattr(rp.win_input, "focus", lambda hwnd, pid, **k: in_front.update(pid=pid))
    monkeypatch.setattr(rp.win_input, "perform", lambda events, pid, **k: sent.append((in_front["pid"], list(events))))
    monkeypatch.setattr(rp.ctypes.windll.user32, "SetForegroundWindow", lambda hwnd: 0, raising=False)

    class Identity:
        hwnd, pid = 1, 2

    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.identity, adapter.should_stop, adapter.view = Identity(), lambda: False, None
    adapter.captures, adapter.item_id, adapter.dialogs_seen = tmp_path, "menu:1032@work", []

    adapter._escape_modal_mode()

    assert [front for front, _ in sent] == [2]


def test_the_watchdog_writes_every_threads_stack_before_it_ends_a_frozen_photoshop(monkeypatch) -> None:
    # Place Linked froze Photoshop again after its folder was fixed, and what the runner was
    # doing at that moment was gone with the force-quit (2026-11-24).
    import io

    from scripts.adobe_observed_truth import runner_photoshop as rp

    order: list[str] = []
    monkeypatch.setattr(rp.subprocess, "run", lambda *a, **k: order.append("killed"))
    out = io.StringIO()

    rp.end_frozen_photoshop(4242, out)

    assert "test_the_watchdog_writes_every_threads_stack" in out.getvalue() and order == ["killed"]


def test_the_watchdog_still_ends_photoshop_when_a_stack_holds_text_the_log_cannot_encode(monkeypatch) -> None:
    # A control's OCR label held a CJK character; writing it to the cp1252 log raised, the
    # watchdog thread died before its taskkill, and Photoshop stayed frozen (2026-11-24).
    import io
    import threading

    from scripts.adobe_observed_truth import runner_photoshop as rp

    killed: list[int] = []
    monkeypatch.setattr(rp.subprocess, "run", lambda args, **k: killed.append(int(args[2])))
    waiting = threading.Event()

    def drive_slider(control) -> None:
        waiting.wait(5)

    threading.Thread(target=drive_slider, args=("slider 回",), daemon=True).start()
    log = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    rp.end_frozen_photoshop(4924, log)
    waiting.set()

    log.seek(0)
    assert killed == [4924] and "control: 'slider \\u56de'" in log.read()


def test_a_written_stack_names_the_control_each_frame_was_driving(tmp_path) -> None:
    # Three file dialogs froze Photoshop during drive_slider, and the stacks could not say which
    # of the dialog's controls was being driven (2026-11-24).
    import io
    import threading

    from scripts.adobe_observed_truth.runner_photoshop import dump_stacks_if_asked

    waiting = threading.Event()

    def drive_slider(control) -> None:
        waiting.wait(5)

    worker = threading.Thread(target=drive_slider, args=("slider at (218, 149, 351, 298)",), daemon=True)
    worker.start()
    request, out = tmp_path / "STACKS-RUNNER", io.StringIO()
    request.touch()

    dump_stacks_if_asked(request, out)
    waiting.set()

    assert "control: 'slider at (218, 149, 351, 298)'" in out.getvalue()


def test_a_windows_file_dialog_gets_no_control_pass_it_is_left_to_the_work_pass(monkeypatch, tmp_path) -> None:
    # The operator, watching Place Linked wander (2026-11-24): "should it not just simply click
    # on that observed truth chart and then click place? The end." The work pass does exactly
    # that; walking Windows' folder browser maps nothing of Photoshop.
    from types import SimpleNamespace

    from scripts.adobe_observed_truth import runner_photoshop as rp

    driven: list = []
    monkeypatch.setattr(rp, "drive_dialog", lambda *a, **k: driven.append(a) or [])
    monkeypatch.setattr(rp.time, "sleep", lambda s: None)

    class FileDialog:
        def __init__(self, *a):
            pass

        def is_file_dialog(self):
            return True

    monkeypatch.setattr(rp, "DialogSurface", FileDialog)
    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.should_stop, adapter.ocr, adapter.identity = (lambda: False), object(), SimpleNamespace(pid=1, hwnd=2)
    adapter.dialog_path, adapter.expected, adapter.item_id, adapter.parity = "File > Place Linked", [], "menu:3090@controls", {}
    adapter.captures, adapter.control_actions, adapter.known_labels = tmp_path / "captures", None, set()

    summary = adapter._drive_controls(SimpleNamespace(hwnd=5))

    full = (tmp_path / "control-actions-full.jsonl").read_text(encoding="utf-8")
    assert driven == [] and "left to the work pass" in full and summary is not None


def test_every_recipe_script_names_no_path_outside_its_sandbox_folder(tmp_path) -> None:
    # A recipe does a dialog's work by script (PDF Presentation, Save for Web): it reads
    # and writes only the sandbox folder the harness made for it (2026-11-24).
    import re

    from scripts.adobe_observed_truth.runner_photoshop import RECIPES, recipe_script

    folder = tmp_path / "recipes" / "x"
    for name in RECIPES:
        paths = re.findall(r'"([A-Za-z]:/[^"]*)"', recipe_script(name, folder))
        assert paths and all(p.startswith(folder.as_posix()) for p in paths), (name, paths)


def test_a_recipe_runs_by_script_from_a_fresh_input_into_an_empty_output_folder(monkeypatch, tmp_path) -> None:
    from scripts.adobe_observed_truth import runner_photoshop as rp

    driven: list[str] = []
    monkeypatch.setattr(rp, "_js_in_own_apartment", lambda script: driven.append(script) or "null")
    monkeypatch.setattr(rp, "_photoshop_hung", lambda pid: False)
    monkeypatch.setattr(rp.photoshop, "list_dialogs", lambda pid: [])
    stale = tmp_path / "recipes" / "pdf_presentation" / "out" / "old.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"x")

    class Identity:
        hwnd, pid = 1, 2

    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.sandbox, adapter.identity, adapter.should_stop = tmp_path, Identity(), lambda: False
    adapter._capture_and_cancel_dialogs = lambda: 0

    adapter._run_recipe("pdf_presentation")

    folder = tmp_path / "recipes" / "pdf_presentation"
    assert (folder / "in" / "observed-truth-chart.png").exists() and not stale.exists()
    assert driven == [rp.recipe_script("pdf_presentation", folder)]
    # What this recipe wrote is the observation (the fake script wrote nothing), not another's
    # leftovers: PDF Presentation's record listed Save for Web's file (2026-11-24).
    (folder / "out" / "observed-truth-chart.psd").write_bytes(b"x")
    other = tmp_path / "recipes" / "save_for_web" / "out"
    other.mkdir(parents=True)
    (other / "observed-truth-web.png").write_bytes(b"x")
    assert adapter._record("recipe_files") == {"recipe_files": ["observed-truth-chart.psd"]}


def test_the_runner_gives_every_key_press_its_person_is_back_guard() -> None:
    # The dialog answerer pressed Enter with no guard: it ignored the person, and could not take
    # back a foreground the Claude app had taken (File Info, 2026-11-24).
    from scripts.adobe_observed_truth import win_input
    from scripts.adobe_observed_truth.runner_photoshop import install_session_guard

    idle = {"s": 0.5}
    install_session_guard(lambda: idle["s"], threshold_s=3.0)
    try:
        back = win_input._guard(None)()
        idle["s"] = 60.0
        away = win_input._guard(None)()
    finally:
        win_input.set_session_guard(None)

    assert (back, away) == (True, False)


def test_a_running_runner_writes_every_threads_stack_when_asked(tmp_path) -> None:
    # A Save a Copy sat unanswered for 5 minutes with no way to see where the runner waited
    # (2026-11-24): a request file gets every thread's stack, without stopping the run.
    import io
    import threading

    from scripts.adobe_observed_truth.runner_photoshop import dump_stacks_if_asked

    request, out = tmp_path / "STACKS-RUNNER", io.StringIO()
    waiting = threading.Event()

    def stuck_in_a_capture() -> None:
        waiting.wait(5)

    worker = threading.Thread(target=stuck_in_a_capture, daemon=True)
    worker.start()

    assert dump_stacks_if_asked(request, out) is False and out.getvalue() == ""
    request.touch()
    assert dump_stacks_if_asked(request, out) is True
    waiting.set()

    assert "stuck_in_a_capture" in out.getvalue() and not request.exists()


def test_a_photoshop_the_watchdog_ended_is_started_again_before_the_next_spec(monkeypatch) -> None:
    # The next three specs failed on a dead Photoshop and used up the restarts (2026-11-24).
    from scripts.adobe_observed_truth import runner_photoshop as rp

    launched: list[int] = []

    class Identity:
        pid = 17740

    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.identity = Identity()
    adapter._relaunch_app = lambda: launched.append(adapter.identity.pid)

    monkeypatch.setattr(rp, "_alive", lambda pid: True)
    adapter.relaunch_if_gone()
    assert launched == []

    monkeypatch.setattr(rp, "_alive", lambda pid: False)
    adapter.relaunch_if_gone()
    assert launched == [17740]


def test_a_read_flyouts_step_reads_every_visible_panel_groups_flyout_and_records_it(monkeypatch) -> None:
    from scripts.adobe_observed_truth import runner_photoshop as rp
    from scripts.adobe_observed_truth.families import ScenarioSpec

    read = [{"group": [1, 2, 3, 4], "entries": [{"command": 2941, "enabled": True, "position": [0]}]}]
    asked: list[tuple] = []
    monkeypatch.setattr(rp, "read_flyouts", lambda pid, hwnd, click, escape: asked.append((pid, hwnd)) or read)
    monkeypatch.setattr(rp.win_input, "focus", lambda *a, **k: None)

    class Identity:
        hwnd, pid = 11, 22

    class Front:
        def bring_to_front(self) -> None:
            pass

    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.ps, adapter.identity = Front(), Identity()
    adapter.begin(ScenarioSpec("panel:layers@flyout", "flyout_discovery", "run"), lambda: False)

    adapter._read_flyouts()

    assert asked == [(22, 11)] and adapter._record("flyouts") == {"flyouts": read}


def test_a_command_that_closed_the_document_is_recorded_as_such_not_as_a_failure() -> None:
    assert history_observation(documents_open=0, states=None) == {
        "count": 0,
        "last": [],
        "no_document_open": True,
    }
    states = [
        {"name": "observed-truth-probe"},
        {"name": "New"},
        {"name": "Rotate Canvas"},
        {"name": "x"},
    ]
    assert history_observation(documents_open=1, states=states) == {
        "count": 4,
        "last": ["New", "Rotate Canvas", "x"],
    }


def test_a_dialog_that_vanished_before_capture_is_noted_without_failing() -> None:
    def gone() -> str:
        raise OSError("DwmGetWindowAttribute failed: 0x80070006")

    assert dialog_record("PSFloatC", "a.png", lambda: "abc123") == {
        "class": "PSFloatC",
        "image": "a.png",
        "sha256": "abc123",
    }
    assert dialog_record("PSFloatC", "a.png", gone) == {
        "class": "PSFloatC",
        "image": None,
        "capture_error": "DwmGetWindowAttribute failed: 0x80070006",
    }


def test_photoshop_is_force_quit_only_if_the_last_check_saw_nothing_but_scratch_work() -> None:
    assert may_force_quit(["observed-truth-probe"], reading_age_s=60, idle_s=600)
    assert may_force_quit([], reading_age_s=60, idle_s=600)
    assert not may_force_quit(["observed-truth-probe", "holiday.psd"], reading_age_s=60, idle_s=600)
    assert not may_force_quit(None, reading_age_s=0, idle_s=600)  # never read: cannot know


def test_a_reading_taken_before_the_person_last_touched_the_machine_does_not_count() -> None:
    # Read 10 minutes ago; they typed 2 minutes ago and could have opened their own file.
    assert not may_force_quit(["observed-truth-probe"], reading_age_s=600, idle_s=120)


def test_escape_is_never_sent_to_a_dialog_once_the_person_is_back() -> None:
    assert not may_cancel_now("escape", person_is_back=True)
    assert may_cancel_now("escape", person_is_back=False)
    assert may_cancel_now("cancel_command", person_is_back=True)  # posted, takes no focus


def test_without_a_window_snapshot_nothing_is_closed() -> None:
    now = [TopWindow(hwnd=9, class_name="bridge16", program="Adobe Bridge.exe")]

    assert new_adobe_windows(before=None, now=now) == []


def test_the_escape_clock_restarts_when_a_dialog_has_just_been_dealt_with() -> None:
    assert quiet_seconds(now=40.0, started=0.0, last_dialog_at=35.0) == 5.0
    assert quiet_seconds(now=40.0, started=0.0, last_dialog_at=None) == 40.0


def test_only_photoshop_declining_a_command_counts_as_a_refusal() -> None:
    declined = "menu_command failed in Photoshop: Error: Could not complete the Equalize command ^0."
    broken = "Error: Could not complete your request because of a program error."

    assert photoshop_refusal(declined) == "Could not complete the Equalize command"
    assert photoshop_refusal(broken) is None
    assert photoshop_refusal("TimeoutError: no answer") is None


def test_new_windows_name_adobe_and_photoshop_programs_and_only_count_the_rest() -> None:
    now = [
        *BEFORE,
        TopWindow(hwnd=3, class_name="bridge16", program="Adobe Bridge.exe"),
        TopWindow(hwnd=6, class_name="PSFloatC", program="Photoshop.exe"),
        TopWindow(hwnd=7, class_name="Chrome_WidgetWin_1", program="chrome.exe"),
    ]

    assert window_observation(before={1, 2}, now=now) == {
        "new_windows": ["PSFloatC|Photoshop.exe", "bridge16|Adobe Bridge.exe"],
        "other_new_windows": 1,
    }


def test_a_command_photoshop_says_is_unavailable_is_a_refusal_not_a_hang() -> None:
    # tool:distort, 2026-11-09: Photoshop answered, so it is not stuck and needs no restart.
    error = (
        "com_error: (-2147352567, 'Exception occurred.', (0, 'Adobe Photoshop', 'General Photoshop"
        " error occurred. This functionality may not be available in this version of Photoshop.\n"
        "- The command \"Select\" is not currently available.\rLine: 13\r-&gt;  ', None, 0, -1), None)"
    )

    assert photoshop_refusal(error) == 'The command "Select" is not currently available'


def test_the_command_named_in_curly_quotes_is_kept_not_the_generic_line() -> None:
    # The brush probe's refusal said only "This functionality may not be available": the detail
    # line named Select in curly quotes, which the pattern missed (2026-11-25).
    error = ("General Photoshop error occurred. This functionality may not be available in this version of Photoshop.\n"
             "- Error 8800: General Photoshop error occurred.\n- The command “Select” is not currently available.")

    assert photoshop_refusal(error) == 'The command "Select" is not currently available'


def test_functionality_photoshop_says_is_unavailable_is_a_refusal() -> None:
    error = "General Photoshop error occurred. This functionality may not be available in this version of Photoshop.\n- "

    assert photoshop_refusal(error) == (
        "This functionality may not be available in this version of Photoshop"
    )


def test_photoshop_being_busy_is_still_a_failure_so_a_hang_gets_a_restart() -> None:
    busy = "com_error: (-2147417846, 'The message filter indicated that the application is busy.')"

    assert photoshop_refusal(busy) is None


def test_enter_is_never_sent_to_a_dialog_once_the_person_is_back() -> None:
    assert not may_cancel_now("enter", person_is_back=True)


def test_a_window_hung_for_a_minute_means_photoshop_froze() -> None:
    # Filter > Render > Fibers, 2026-11-09: Photoshop's window hung with no CPU use.
    assert hung_too_long(hung_since=40.0, now=101.0)


def test_a_window_hung_briefly_is_a_busy_filter_not_a_freeze() -> None:
    assert not hung_too_long(hung_since=40.0, now=70.0)


def test_a_window_that_is_answering_is_not_hung() -> None:
    assert not hung_too_long(hung_since=None, now=500.0)


def test_the_watchdog_kills_photoshop_frozen_for_two_minutes_when_only_scratch_work_is_open() -> None:
    # A script call to a frozen Photoshop never returns: only ending Photoshop frees the runner.
    assert watchdog_should_kill(hung_since=0.0, now=121.0, safe_to_quit=True)


def test_the_watchdog_waits_out_a_shorter_freeze() -> None:
    assert not watchdog_should_kill(hung_since=0.0, now=90.0, safe_to_quit=True)


def test_the_watchdog_never_kills_photoshop_when_the_persons_work_may_be_open() -> None:
    assert not watchdog_should_kill(hung_since=0.0, now=600.0, safe_to_quit=False)


def test_after_a_key_press_dialogs_are_watched_for_at_least_eight_seconds() -> None:
    # Print, Preferences, Liquify open seconds after their shortcut (2026-11-09: a single check
    # at 0.8 s missed them and the next probe found Photoshop busy).
    assert keep_watching(elapsed_s=5.0, quiet_s=5.0)


def test_watching_ends_once_nothing_new_has_appeared_for_eight_seconds() -> None:
    assert not keep_watching(elapsed_s=12.0, quiet_s=8.0)


def test_watching_goes_on_while_dialogs_keep_appearing_but_never_past_thirty_seconds() -> None:
    assert keep_watching(elapsed_s=20.0, quiet_s=1.0)
    assert not keep_watching(elapsed_s=30.0, quiet_s=1.0)


def _adapter_with_a_late_save_as(monkeypatch):
    """An adapter whose test document cannot close while a Save As is open: a panel menu
    command opened one a moment after it returned, past the dialog check (2026-11-24)."""
    import threading

    from scripts.adobe_observed_truth import runner_photoshop as rp
    from scripts.adobe_observed_truth.families import ScenarioSpec

    save_as_open, cancelled = threading.Event(), threading.Event()

    def script_waits_on_the_save_as(body: str) -> str:
        save_as_open.set()
        if not cancelled.wait(5):
            raise TimeoutError("closing the document waited on the Save As")
        return "null"

    class Photoshop:
        def js(self, body: str) -> str:
            return script_waits_on_the_save_as(body)

    class Identity:
        hwnd, pid = 11, 22

    monkeypatch.setattr(rp, "_js_in_own_apartment", script_waits_on_the_save_as)
    monkeypatch.setattr(rp, "_photoshop_hung", lambda pid: False)
    monkeypatch.setattr(rp.photoshop, "list_dialogs", lambda pid: [])
    adapter = rp.PhotoshopAdapter.__new__(rp.PhotoshopAdapter)
    adapter.ps, adapter.identity = Photoshop(), Identity()
    adapter.begin(ScenarioSpec("flyout:1", "flyout_command", "run"), lambda: False)

    def capture_and_cancel() -> int:
        if not save_as_open.is_set() or cancelled.is_set():
            return 0
        adapter.dialogs_seen.append({"class": "#32770", "answer": "cancel_command"})
        cancelled.set()
        return 1

    adapter._capture_and_cancel_dialogs = capture_and_cancel
    return adapter, cancelled


def test_closing_the_test_document_cancels_a_dialog_that_opened_late_instead_of_waiting_on_it(
    monkeypatch,
) -> None:
    adapter, cancelled = _adapter_with_a_late_save_as(monkeypatch)

    adapter._close_throwaway_document()

    assert cancelled.is_set()


def test_exporting_the_pixels_cancels_a_dialog_instead_of_waiting_on_it(monkeypatch, tmp_path) -> None:
    # Image > Mode > CMYK Color: PNG cannot hold CMYK, so the export's save opened a Save a
    # Copy and the bare script call waited on it for minutes, three times (2026-11-24).
    adapter, cancelled = _adapter_with_a_late_save_as(monkeypatch)
    adapter.sandbox = tmp_path

    with pytest.raises(FileNotFoundError):  # the cancelled save wrote nothing
        adapter._export_pixels("after")

    assert cancelled.is_set()


def test_a_dialog_that_opened_after_the_record_step_still_appears_in_the_result(monkeypatch) -> None:
    adapter, _ = _adapter_with_a_late_save_as(monkeypatch)
    recorded = adapter._record("dialogs")

    adapter._close_throwaway_document()

    assert recorded["dialogs"] == [{"class": "#32770", "answer": "cancel_command"}]