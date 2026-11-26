from __future__ import annotations

import pytest

from scripts.adobe_observed_truth.win_input import clear_screensaver


class FakeScreensaver:
    """Answers `running()` from a script (the last answer repeats) and records close requests."""

    def __init__(self, running: list[bool], *, has_window: bool = True) -> None:
        self._answers = running
        self._has_window = has_window
        self.close_requests = 0

    def running(self) -> bool:
        return self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]

    def close(self) -> bool:
        self.close_requests += 1
        return self._has_window


def test_no_running_screensaver_is_left_alone() -> None:
    screensaver = FakeScreensaver([False])

    clear_screensaver(running=screensaver.running, close=screensaver.close, sleep=lambda _: None)

    assert screensaver.close_requests == 0


def test_running_screensaver_is_closed_once_and_awaited_until_gone() -> None:
    screensaver = FakeScreensaver([True, True, True, False])
    slept: list[float] = []

    clear_screensaver(running=screensaver.running, close=screensaver.close, sleep=slept.append)

    assert screensaver.close_requests == 1
    assert len(slept) == 3


def test_screensaver_that_will_not_close_stops_input_within_the_timeout() -> None:
    screensaver = FakeScreensaver([True])
    slept: list[float] = []

    with pytest.raises(RuntimeError, match="did not close within 2 s"):
        clear_screensaver(
            running=screensaver.running, close=screensaver.close, sleep=slept.append, timeout_s=2.0
        )

    assert screensaver.close_requests == 1
    assert sum(slept) == pytest.approx(2.0)


def test_screensaver_without_a_closable_window_is_refused_without_waiting() -> None:
    screensaver = FakeScreensaver([True], has_window=False)
    slept: list[float] = []

    with pytest.raises(RuntimeError, match="password-protected"):
        clear_screensaver(running=screensaver.running, close=screensaver.close, sleep=slept.append)

    assert slept == []
