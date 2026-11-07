"""Behavior-focused tests. Requirements, not the implementation, define results."""

import unittest
from collections.abc import Sequence
from readiness import Policy, assess


class ReadinessBehaviorTests(unittest.TestCase):
    def test_ready_immediately_has_no_scheduled_wait(self):
        result = assess(["READY", "BUSY"])
        self.assertEqual((result.outcome, result.checks, result.scheduled_delays_seconds),
                         ("ready", 1, ()))

    def test_busy_offline_ready_stops_at_third_check(self):
        result = assess(["BUSY", "OFFLINE", "READY", "BUSY"])
        self.assertEqual((result.outcome, result.checks, result.scheduled_delays_seconds),
                         ("ready", 3, (2, 2)))

    def test_two_stage_boundary_and_check_budget(self):
        result = assess(["BUSY"] * 10)
        self.assertEqual((result.outcome, result.checks, result.scheduled_delays_seconds),
                         ("exhausted", 5, (2, 2, 10, 10)))

    def test_short_evidence_is_incomplete_not_exhausted(self):
        result = assess(["BUSY", "BUSY"])
        self.assertEqual((result.outcome, result.checks, result.scheduled_delays_seconds),
                         ("incomplete", 2, (2,)))

    def test_no_evidence_is_not_false_success(self):
        result = assess([])
        self.assertEqual((result.outcome, result.checks, result.last_status),
                         ("incomplete", 0, None))

    def test_unknown_status_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            assess(["BUSY", "UNEXPECTED"])

    def test_bad_policy_refused(self):
        with self.assertRaises(ValueError):
            Policy(max_checks=0)

    def test_custom_policy_changes_schedule_without_changing_contract(self):
        result = assess(["BUSY", "BUSY", "BUSY", "READY"],
                        Policy(max_checks=4, fast_delay_seconds=1,
                               slow_delay_seconds=7, switch_after_check=1))
        self.assertEqual((result.outcome, result.checks, result.scheduled_delays_seconds),
                         ("ready", 4, (1, 7, 7)))

    def test_budget_does_not_consume_the_next_observation(self):
        class BudgetWitness(Sequence):
            def __init__(self):
                self.read_indices = []

            def __len__(self):
                return 6

            def __getitem__(self, index):
                self.read_indices.append(index)
                if index == 5:
                    raise AssertionError("sixth observation consumed")
                return "BUSY"

        observations = BudgetWitness()
        result = assess(observations, Policy(max_checks=5))
        self.assertEqual((result.outcome, result.checks, result.last_status),
                         ("exhausted", 5, "BUSY"))
        self.assertEqual(observations.read_indices, [0, 1, 2, 3, 4])

    def test_ready_consumes_no_later_observation(self):
        class EarlyReady(Sequence):
            def __len__(self):
                return 2

            def __getitem__(self, index):
                if index:
                    raise AssertionError("observation after READY consumed")
                return "READY"

        result = assess(EarlyReady())
        self.assertEqual((result.outcome, result.checks, result.last_status,
                          result.scheduled_delays_seconds), ("ready", 1, "READY", ()))

    def test_single_check_budget_has_no_final_delay(self):
        result = assess(["OFFLINE", "UNEXPECTED"], Policy(max_checks=1))
        self.assertEqual((result.outcome, result.checks, result.last_status,
                          result.scheduled_delays_seconds), ("exhausted", 1, "OFFLINE", ()))

    def test_exact_budget_ready_wins_over_exhaustion(self):
        result = assess(("BUSY", "BUSY", "READY"), Policy(max_checks=3))
        self.assertEqual((result.outcome, result.checks, result.last_status,
                          result.scheduled_delays_seconds), ("ready", 3, "READY", (2, 2)))

    def test_each_policy_field_refuses_nonpositive_or_noninteger_values(self):
        for field in ("max_checks", "fast_delay_seconds", "slow_delay_seconds", "switch_after_check"):
            for value in (0, -1, True, 1.5, "2", None):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    Policy(**{field: value})

    def test_invalid_status_values_are_errors(self):
        for value in ("ready", "", None, 2, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess([value])

    def test_text_is_not_a_status_sequence(self):
        for value in ("READY", b"READY"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                assess(value)


if __name__ == "__main__":
    unittest.main()
