"""Synthetic public-command contracts for private handoff validation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "check_fleet_handoff.py"


class FleetHandoffCommand(unittest.TestCase):
    def example(self):
        return json.loads((ROOT / "docs/templates/FLEET_HANDOFF.json").read_text(encoding="utf-8"))

    def run_record(self, record):
        return self.run_bytes(json.dumps(record).encode("utf-8"))

    def run_bytes(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "handoff.json"
            path.write_bytes(payload)
            result = subprocess.run(
                [sys.executable, "-B", str(COMMAND), str(path)],
                capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            self.assertEqual(path.read_bytes(), payload, "checker changed its input")
            self.assertEqual(list(Path(directory).iterdir()), [path], "checker wrote output beside its input")
            return result

    def test_missing_fields_are_a_finding_not_success(self):
        result = self.run_record({})
        self.assertEqual(result.returncode, 1)
        self.assertIn("schema_version", result.stdout)

    def test_complete_synthetic_record_is_structurally_valid(self):
        result = self.run_record(self.example())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("claims and authorization not verified", result.stdout)

    def test_wrong_types_and_empty_required_identity_are_findings(self):
        for key, value in [("owner", " "), ("schema_version", True), ("phase", "stopped"),
                           ("evidence", []), ("instructions", []), ("scope", []),
                           ("pending_operations", {}), ("blockers", "none")]:
            with self.subTest(key=key):
                record = self.example()
                record[key] = value
                result = self.run_record(record)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(key, result.stdout)

    def test_completion_with_pending_work_or_uncertain_admission_refuses(self):
        for patch in [
            {"pending_operations": [{"id": "in-flight", "state": "running"}]},
            {"admission": {"status": "uncertain", "operation_id": None, "evidence": "unconfirmed response"}},
            {"completed": []},
        ]:
            with self.subTest(patch=patch):
                record = self.example()
                record.update(patch)
                self.assertEqual(self.run_record(record).returncode, 1)

    def test_uncertain_admission_names_reconciliation_not_retry(self):
        record = self.example()
        record["work_state"] = "running"
        record["admission"] = {"status": "uncertain", "operation_id": "uncertain-id", "evidence": "unconfirmed response"}
        record["retry"]["decision"] = "reconcile"
        record["retry"]["prior_outcome"] = "uncertain"
        record["next"]["kind"] = "reconcile"
        self.assertEqual(self.run_record(record).returncode, 0)
        record["next"]["kind"] = "continue"
        self.assertEqual(self.run_record(record).returncode, 1)

    def test_incomplete_work_has_an_owned_continuation(self):
        record = self.example()
        record["work_state"] = "running"
        self.assertEqual(self.run_record(record).returncode, 1)
        record["next"]["kind"] = "continue"
        self.assertEqual(self.run_record(record).returncode, 0)

    def blocked(self):
        record = self.example()
        record["work_state"] = "blocked"
        record["next"]["kind"] = "resolve"
        record["blockers"] = [{
            "action": "Read authorized receipt", "target": "synthetic receipt",
            "outcome": "denied", "reason": "Explicit access denial; cause unknown",
            "attempts": ["One supported read returned denied"],
            "alternatives": {
                "local": {"status": "blocked", "reason": "Denial stays in force"},
                "cloud": {"status": "not_applicable", "reason": "Changing host would evade the same denial"}
            }
        }]
        return record

    def test_blocker_requires_exact_diagnosis_and_both_route_dispositions(self):
        record = self.blocked()
        self.assertEqual(self.run_record(record).returncode, 0)
        for field in ["action", "target", "outcome", "reason", "attempts", "alternatives"]:
            with self.subTest(field=field):
                record = self.blocked()
                del record["blockers"][0][field]
                self.assertEqual(self.run_record(record).returncode, 1)
        record = self.blocked()
        del record["blockers"][0]["alternatives"]["cloud"]
        self.assertEqual(self.run_record(record).returncode, 1)
        record["blockers"] = []
        self.assertEqual(self.run_record(record).returncode, 1)

    def retrying(self):
        record = self.blocked()
        record["observed_at"] = "2026-10-31T10:10:00Z"
        record["retry"] = {
            "decision": "retry", "reason": "New relevant evidence resolves the scoped denial",
            "prior_outcome": "known_not_executed", "window_started_at": "2026-10-31T10:00:00Z",
            "window_expires_at": "2026-10-31T10:15:00Z", "materially_new_evidence": "synthetic explicit grant receipt",
            "attempt_for_evidence": 1
        }
        return record

    def test_retry_requires_known_outcome_window_and_one_new_evidence_attempt(self):
        self.assertEqual(self.run_record(self.retrying()).returncode, 0)
        for key, value in [("prior_outcome", "uncertain"), ("prior_outcome", "running"),
                           ("materially_new_evidence", None), ("attempt_for_evidence", 2),
                           ("window_expires_at", "2026-10-31T10:16:00Z")]:
            with self.subTest(key=key, value=value):
                record = self.retrying()
                record["retry"][key] = value
                self.assertEqual(self.run_record(record).returncode, 1)
        record = self.retrying()
        record["observed_at"] = "2026-10-31T10:15:01Z"
        self.assertEqual(self.run_record(record).returncode, 1)

    def test_admitted_work_outlives_retry_window(self):
        record = self.retrying()
        record["observed_at"] = "2026-10-31T18:00:00Z"
        record["work_state"] = "running"
        record["blockers"] = []
        record["pending_operations"] = [{"id": "example-operation", "state": "running"}]
        record["retry"]["decision"] = "none"
        record["retry"]["prior_outcome"] = "running"
        record["next"]["kind"] = "wait"
        record["next"]["check_at"] = "2026-10-31T18:05:00Z"
        self.assertEqual(self.run_record(record).returncode, 0)

    def test_task_handoff_is_due_within_original_24_hours(self):
        record = self.example()
        record["handoff_due_at"] = "2026-11-01T10:00:01Z"
        self.assertEqual(self.run_record(record).returncode, 1)
        record = self.example()
        record["work_state"] = "running"
        record["observed_at"] = "2026-11-01T10:00:00Z"
        record["next"]["kind"] = "continue"
        self.assertEqual(self.run_record(record).returncode, 1)
        record["next"]["kind"] = "handoff"
        self.assertEqual(self.run_record(record).returncode, 0)

    def test_invalid_or_ambiguous_json_is_input_error(self):
        for payload in [b"{", b"\xff", b'{"schema_version":1,"schema_version":1}',
                        b'{"version": NaN}', b" " * 262145]:
            with self.subTest(payload=payload[:30]):
                result = self.run_bytes(payload)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)
        record = self.example()
        record["objective"] = "x" * 262145
        self.assertEqual(self.run_record(record).returncode, 2)

    def test_malformed_nested_values_never_crash_or_echo_record_values(self):
        for field in self.example():
            for value in [None, [], {}, "PRIVATE-SYNTHETIC-MARKER"]:
                with self.subTest(field=field, value=value):
                    record = self.example()
                    record[field] = value
                    result = self.run_record(record)
                    self.assertIn(result.returncode, (0, 1))
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertNotIn("PRIVATE-SYNTHETIC-MARKER", result.stdout + result.stderr)

    def test_missing_input_is_unreadable_not_a_clean_record(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", str(COMMAND), str(Path(directory) / "absent")],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)

    def test_completed_record_cannot_schedule_retry_or_reconciliation(self):
        for decision in ("retry", "reconcile", "hold"):
            with self.subTest(decision=decision):
                record = self.retrying()
                record["work_state"] = "complete"
                record["blockers"] = []
                record["next"]["kind"] = "none"
                record["retry"]["decision"] = decision
                self.assertEqual(self.run_record(record).returncode, 1)

    def test_unresolved_uncertain_or_pending_blocker_prevents_retry(self):
        for outcome in ("uncertain", "pending"):
            with self.subTest(outcome=outcome):
                record = self.retrying()
                record["blockers"][0]["outcome"] = outcome
                self.assertEqual(self.run_record(record).returncode, 1)


if __name__ == "__main__":
    unittest.main()
