"""Synthetic tests at the explicit receipt-ingest and CLI boundaries only."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/operation_receipts.py"
spec = importlib.util.spec_from_file_location("operation_receipts", SCRIPT)
receipts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receipts)


def event(**changes):
    record = {"source_id": "synthetic-service", "operation_id": "operation-1",
              "attempt_id": "attempt-1", "stage": "result", "outcome": "succeeded",
              "provenance": "direct_result", "execution": "completed"}
    record.update(changes)
    return record


class ReceiptTests(unittest.TestCase):
    def test_triage_surfaces_same_delivery_identity_with_different_content(self):
        report = receipts.ingest([event(delivery_id="delivery-1", target_ref="first"),
                                  event(delivery_id="delivery-1", target_ref="second")])
        self.assertEqual(len(report["events"]), 2)
        self.assertTrue(report["attempts"][0]["delivery_collision"])
        self.assertEqual(report["triage"]["review_leads"], [
            {"flag": "inconsistent_event_metadata", "event_indices": [1], "attempt_indices": [0]}])

    def test_success_with_structured_denial_reason_is_inconsistent_not_observed_denial(self):
        for reason in ("approval_denial", "access_denial"):
            report = receipts.ingest([event(reason=reason, authority_ref="synthetic-reference")])
            self.assertEqual(report["events"][0]["denial"], "none_observed")
            self.assertEqual(report["events"][0]["outcome"], "succeeded")
            self.assertEqual(report["events"][0]["reason"], reason)
            self.assertEqual(report["triage"]["review_leads"], [
                {"flag": "inconsistent_event_metadata", "event_indices": [0], "attempt_indices": [0]}])

    def test_triage_distinguishes_conflicts_from_denial_readback_scope_comparison(self):
        denied = event(outcome="denied", reason="access_denial", execution="unknown")
        readback = event(stage="readback", provenance="independent_readback")
        report = receipts.ingest([denied, readback])
        self.assertEqual(report["triage"]["review_leads"], [
            {"flag": "observed_denial", "event_indices": [0], "attempt_indices": [0]},
            {"flag": "unknown_execution", "event_indices": [0], "attempt_indices": [0]},
            {"flag": "result_readback_scope_comparison_needed", "event_indices": [0, 1], "attempt_indices": [0]},
        ])
        self.assertEqual(report["attempts"][0]["returned_outcome"], "denied")
        self.assertEqual(report["attempts"][0]["readback_outcome"], "succeeded")
        conflicting = receipts.ingest([denied, event(), readback,
                                       event(stage="readback", provenance="independent_readback", outcome="failed")])
        self.assertEqual(conflicting["triage"]["review_leads"][-2:], [
            {"flag": "conflicting_returned_results", "event_indices": [0, 1], "attempt_indices": [0]},
            {"flag": "conflicting_readbacks", "event_indices": [2, 3], "attempt_indices": [0]},
        ])

    def test_triage_preserves_partial_items_and_failed_transport_execution_uncertainty(self):
        records = [event(outcome="partial", execution="partial"),
                   event(item_id="item-1"),
                   event(item_id="item-2", outcome="failed", reason="timeout", execution="unknown"),
                   event(attempt_id="attempt-2", outcome="failed", reason="transport_loss", execution="unknown")]
        report = receipts.ingest(records)
        self.assertEqual(report["triage"]["review_leads"], [
            {"flag": "unknown_execution", "event_indices": [2, 3], "attempt_indices": [2, 3]},
            {"flag": "partial_execution", "event_indices": [0], "attempt_indices": [0]},
        ])
        self.assertEqual([a["returned_outcome"] for a in report["attempts"]], ["partial", "succeeded", "failed", "failed"])
        self.assertEqual(report["events"][2]["execution"], "unknown")

    def test_triage_incompatible_plan_is_a_metadata_lead_not_an_observed_denial(self):
        report = receipts.ingest([event(provenance="operator_plan", outcome="denied", execution="unknown",
                                        reason="approval_denial", authority_ref="synthetic-reference")])
        self.assertEqual(report["triage"]["review_leads"], [
            {"flag": "inconsistent_event_metadata", "event_indices": [0], "attempt_indices": [0]}])

    def test_triage_keeps_benign_and_missing_coverage_information_out_of_anomaly_leads(self):
        for records in ([event(text="permission denied", authority_ref="synthetic-reference")], [], [{}]):
            with self.subTest(records=records):
                triage = receipts.ingest(records)["triage"]
                self.assertEqual(triage["review_leads"], [])
                self.assertEqual(triage["coverage"], "caller_supplied_only")
                self.assertEqual(triage["visibility_limits"], [{
                    "flag": "missing_coverage", "event_indices": [0] if records else [],
                    "attempt_indices": [0] if records else []}])
        complete = [event(stage="planned", outcome="unknown", execution="not_started",
                          provenance="operator_plan", source_sequence=1),
                    event(stage="submitted", outcome="unknown", execution="started", source_sequence=2),
                    event(source_sequence=3)]
        report = receipts.ingest(complete)
        self.assertEqual(report["triage"]["review_leads"], [])
        self.assertEqual(report["triage"]["visibility_limits"], [])
        self.assertFalse(report["attempts"][0]["coverage_established"])

    def test_triage_denial_with_reference_requests_scope_comparison_without_validating_authority(self):
        report = receipts.ingest([event(outcome="denied", execution="unknown", reason="approval_denial",
                                        authority_ref="synthetic-private-source-reference")])
        self.assertEqual(report["triage"]["review_leads"], [
            {"flag": "observed_denial", "event_indices": [0], "attempt_indices": [0]},
            {"flag": "authority_scope_comparison_needed", "event_indices": [0], "attempt_indices": [0]},
            {"flag": "unknown_execution", "event_indices": [0], "attempt_indices": [0]},
        ])
        self.assertNotIn("synthetic-private-source-reference", json.dumps(report))

    def test_plan_provenance_cannot_be_promoted_to_observed_denial_or_readback(self):
        for stage in ("result", "submitted", "readback"):
            with self.subTest(stage=stage):
                report = receipts.ingest([event(stage=stage, provenance="operator_plan", outcome="denied",
                                                reason="approval_denial", execution="unknown")])
                safe = report["events"][0]
                self.assertEqual(safe["denial"], "none_observed")
                self.assertTrue(safe["provenance_stage_conflict"])
                self.assertEqual(report["attempts"][0]["returned_outcome"], "unknown")
                self.assertEqual(report["attempts"][0]["readback_outcome"], "unknown")
                self.assertEqual(safe["outcome"], "denied")
                self.assertEqual(safe["provenance"], "operator_plan")

    def test_unencodable_identifier_is_unknown_without_dropping_other_receipts(self):
        events = [event(operation_id="\ud800"),
                  event(outcome="denied", reason="approval_denial", execution="unknown", attempt_id="attempt-2")]
        report = receipts.ingest(events)
        self.assertEqual(len(report["events"]), 2)
        self.assertIsNone(report["events"][0]["identity_sha256"]["operation_id"])
        self.assertEqual(report["events"][1]["denial"], "approval_denial")

    def test_out_of_range_utc_conversion_does_not_drop_other_receipts(self):
        events = [event(source_time="0001-01-01T00:00:00+23:59"),
                  event(outcome="denied", reason="access_denial", execution="unknown", attempt_id="attempt-2")]
        report = receipts.ingest(events)
        self.assertEqual(report["capture_status"], "dry_run")
        self.assertEqual(len(report["events"]), 2)
        self.assertIsNone(report["events"][0]["source_time"])
        self.assertEqual(report["events"][1]["denial"], "access_denial")

    def test_delivery_identity_requires_exact_typed_content_not_python_equality(self):
        report = receipts.ingest([event(delivery_id="delivery-1", source_sequence=1),
                                  event(delivery_id="delivery-1", source_sequence=True)])
        self.assertEqual([e["duplicate_of"] for e in report["events"]], [None, None])
        self.assertTrue(report["attempts"][0]["delivery_collision"])

    def test_missing_delivery_or_attempt_ids_do_not_deduplicate(self):
        for changes in ({}, {"attempt_id": None, "delivery_id": "delivery-1"}):
            records = [event(**changes), event(**changes)]
            safe = receipts.ingest(records)["events"]
            self.assertEqual([e["duplicate_of"] for e in safe], [None, None])

    def test_dry_run_and_invalid_batches_do_not_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            report = receipts.ingest([event(outcome="unrecognized", source_time="not-a-time")])
            self.assertEqual(report["capture_status"], "dry_run")
            self.assertEqual(report["events"][0]["outcome"], "unknown")
            self.assertIsNone(report["events"][0]["source_time"])
            for records in ({}, [None], [event()] * 257, [event(payload="x" * 262144)]):
                self.assertEqual(receipts.ingest(records, private_output=output)["capture_status"], "invalid_input")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_planned_intent_is_not_a_submitted_action_or_observed_denial(self):
        report = receipts.ingest([event(stage="planned", outcome="denied", reason="approval_denial",
                                        provenance="operator_plan", execution="unknown")])
        self.assertEqual(report["events"][0]["denial"], "none_observed")
        self.assertTrue(report["events"][0]["stage_outcome_conflict"])
        self.assertEqual(report["attempts"][0]["returned_outcome"], "unknown")
        self.assertEqual(report["attempts"][0]["missing_stages"], ["submitted", "result"])

    def test_denial_retains_unknown_execution_and_argument_error_is_separate(self):
        denied = event(outcome="denied", reason="access_denial", execution="unknown")
        binding = event(outcome="failed", reason="argument_binding", attempt_id="attempt-2")
        safe = receipts.ingest([denied, binding])["events"]
        self.assertEqual([e["denial"] for e in safe], ["access_denial", "none_observed"])
        self.assertEqual(safe[0]["execution"], "unknown")

    def test_conflicting_results_are_not_erased_and_readback_is_separate(self):
        report = receipts.ingest([event(outcome="denied"), event(), event(stage="readback")])
        self.assertEqual(report["attempts"][0]["returned_outcome"], "unknown")
        self.assertTrue(report["attempts"][0]["returned_outcome_conflict"])
        self.assertEqual(report["attempts"][0]["readback_outcome"], "succeeded")

    @unittest.skipUnless(os.name == "posix", "private mode contract is POSIX-only")
    def test_capture_failure_does_not_send_retry_change_arguments_or_permissions(self):
        records = [event(action_args={"target": "synthetic-private-target"}, authority="synthetic-grant")]
        before = copy.deepcopy(records)
        with tempfile.TemporaryDirectory() as directory, \
                patch("socket.socket") as network, patch("subprocess.Popen") as process, \
                patch("os.system") as shell, patch("os.chmod") as permissions, \
                patch("os.fsync", side_effect=OSError("SYNTHETIC_SECRET_ONLY")):
            output = Path(directory) / "receipt.json"
            report = receipts.ingest(records, private_output=output)
            self.assertEqual(report["capture_status"], "capture_error")
            self.assertEqual(report["write_state"], "unknown_or_partial")
            self.assertNotIn("SYNTHETIC_SECRET_ONLY", json.dumps(report))
            self.assertNotIn("synthetic-private-target", output.read_text())
            for boundary in (network, process, shell, permissions):
                boundary.assert_not_called()
        self.assertEqual(records, before)

    @unittest.skipUnless(os.name == "posix", "private mode contract is POSIX-only")
    def test_nonprivate_and_symlink_destinations_are_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / "public"
            public.mkdir(mode=0o755)
            private = root / "private"
            private.mkdir(mode=0o700)
            link = root / "link"
            link.symlink_to(private, target_is_directory=True)
            final_link = private / "receipt.json"
            final_link.symlink_to(root / "untouched")
            for target in (public / "receipt.json", link / "other.json", final_link,
                           private / ".." / "escape.json", Path("relative.json")):
                with self.subTest(target=target):
                    report = receipts.ingest([event()], private_output=target)
                    self.assertEqual(report["capture_status"], "capture_error")
                    self.assertEqual(report["write_state"], "not_written")
            self.assertEqual(list(public.iterdir()), [])
            self.assertEqual(list(private.iterdir()), [final_link])
            self.assertFalse((root / "untouched").exists())

    def test_cli_dry_run_and_bad_input_never_echo_input_or_return_a_gate_failure(self):
        good = subprocess.run([sys.executable, "-B", str(SCRIPT)], input=json.dumps([event()]),
                              text=True, capture_output=True, check=False)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)["capture_status"], "dry_run")
        for bad in ('[{"outcome":"succeeded", "outcome":"denied"}]',
                    '[{"payload":NaN}]', 'SYNTHETIC_SECRET_ONLY', '[' * 2000):
            result = subprocess.run([sys.executable, "-B", str(SCRIPT)], input=bad,
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["capture_status"], "invalid_input")
            self.assertEqual(result.stderr, "")

    @unittest.skipUnless(os.name == "posix", "private mode contract is POSIX-only")
    def test_private_artifact_is_redacted_before_write_and_read_back(self):
        secret = "SYNTHETIC_SECRET_ONLY"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            record = event(operation_id=secret, text=secret, payload={"secret": secret},
                           custom_rule=secret, signed_url="https://example.invalid/?token=" + secret)
            report = receipts.ingest([record], private_output=output)
            self.assertEqual(report["capture_status"], "saved")
            self.assertTrue(report["readback_verified"])
            saved = output.read_text()
            self.assertNotIn(secret, saved)
            self.assertNotIn("https://", saved)
            self.assertEqual(json.loads(saved)["events"], report["events"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            before = output.read_bytes()
            again = receipts.ingest([event(outcome="denied")], private_output=output)
            self.assertEqual(again["capture_status"], "capture_error")
            self.assertEqual(again["write_state"], "not_written")
            self.assertEqual(output.read_bytes(), before)

    def test_missing_phases_and_sequences_stay_visible_without_reordering(self):
        report = receipts.ingest([event(source_sequence=4),
                                  event(stage="submitted", outcome="unknown", source_sequence=2)])
        self.assertEqual([e["source_sequence"] for e in report["events"]], [4, 2])
        attempt = report["attempts"][0]
        self.assertTrue(attempt["out_of_order"])
        self.assertEqual(attempt["missing_sequence_ranges"], [[1, 1], [3, 3]])
        self.assertEqual(attempt["missing_stages"], ["planned"])
        self.assertFalse(attempt["coverage_established"])
        self.assertTrue(receipts.ingest([event()])["attempts"][0]["sequence_unknown"])

    def test_partial_writes_remain_individual_and_readback_is_not_an_execution_receipt(self):
        records = [event(outcome="partial", execution="partial"),
                   event(item_id="file-1"), event(item_id="file-2", outcome="failed"),
                   event(stage="readback", outcome="succeeded", provenance="independent_readback")]
        report = receipts.ingest(records)
        self.assertEqual([a["event_indices"] for a in report["attempts"]], [[0, 3], [1], [2]])
        self.assertEqual([a["returned_outcome"] for a in report["attempts"]], ["partial", "succeeded", "failed"])
        self.assertEqual(report["attempts"][0]["readback_outcome"], "succeeded")
        self.assertEqual(receipts.ingest([records[-1]])["attempts"][0]["returned_outcome"], "unknown")

    def test_exact_duplicate_is_marked_but_distinct_retries_and_idless_records_survive(self):
        first = event(delivery_id="delivery-1")
        records = [first, copy.deepcopy(first), event(attempt_id="attempt-2"),
                   event(operation_id=None), event(operation_id=None)]
        report = receipts.ingest(records)
        self.assertEqual(len(report["events"]), 5)
        self.assertEqual([e["duplicate_of"] for e in report["events"]], [None, 0, None, None, None])
        self.assertEqual([a["event_indices"] for a in report["attempts"]], [[0, 1], [2], [3], [4]])

    def test_timeout_is_uncertain_and_late_result_is_preserved_and_reconciled(self):
        timeout = event(outcome="unknown", reason="timeout", execution="unknown", source_sequence=2)
        report = receipts.ingest([timeout])
        self.assertEqual(report["attempts"][0]["returned_outcome"], "unknown")
        report = receipts.ingest([timeout, event(source_sequence=3)])
        self.assertEqual([e["outcome"] for e in report["events"]], ["unknown", "succeeded"])
        self.assertEqual(report["attempts"][0]["returned_outcome"], "succeeded")
        self.assertEqual(report["attempts"][0]["readback_outcome"], "unknown")

    def test_success_text_does_not_become_a_denial_and_input_is_unchanged(self):
        records = [event(text="permission denied", credentials="synthetic-secret")]
        before = copy.deepcopy(records)
        report = receipts.ingest(records)
        self.assertEqual(report["events"][0]["outcome"], "succeeded")
        self.assertEqual(report["events"][0]["denial"], "none_observed")
        self.assertNotIn("permission denied", json.dumps(report))
        self.assertNotIn("synthetic-secret", json.dumps(report))
        self.assertEqual(records, before)


if __name__ == "__main__":
    unittest.main()
