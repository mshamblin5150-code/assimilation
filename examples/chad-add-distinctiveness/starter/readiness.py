"""Chad's exercise: implement a bounded, offline readiness assessment.

This is a learner starter, intentionally unfinished. Do not use actual printer
network access, credentials, or real waits for this exercise.
"""

from dataclasses import dataclass
from typing import Literal, Sequence

Outcome = Literal["ready", "exhausted", "incomplete"]


@dataclass(frozen=True)
class Policy:
    max_checks: int = 5
    fast_delay_seconds: int = 2
    slow_delay_seconds: int = 10
    switch_after_check: int = 2


@dataclass(frozen=True)
class Assessment:
    outcome: Outcome
    checks: int
    scheduled_delays_seconds: tuple[int, ...]
    last_status: str | None


def assess(observations: Sequence[str], policy: Policy = Policy()) -> Assessment:
    """Assess synthetic READY/BUSY/OFFLINE snapshots, without real waiting.

    Contract: See the lesson and tests. The exercise is to supply an
    independent implementation rather than copying decompiled source.
    """
    raise NotImplementedError("implement after reading the behavioral contract")
