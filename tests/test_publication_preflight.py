"""Synthetic contract tests for the offline, status-only publication preflight."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "check_publication_preflight.py"


def example():
    return {
        "schema_version": 1,
        "destination": {"visibility": "public", "audience": "public"},
        "authority": {"publication": "confirmed", "scope": "confirmed"},
        "content": {
            "review": "completed", "redistribution": "confirmed",
            "sensitive_material": "none",
        },
        "evaluation": {
            "context": "none", "undisclosed_material": "none",
            "release_clearance": "not_applicable",
        },
    }


class PublicationPreflightTests(unittest.TestCase):
    def run_bytes(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "status-only.json"
            record.write_bytes(payload)
            result = subprocess.run(
                [sys.executable, "-B", str(COMMAND), str(record)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", timeout=10,
            )
            self.assertEqual(record.read_bytes(), payload)
            self.assertEqual(list(Path(directory).iterdir()), [record])
            return result

    def run_record(self, record):
        return self.run_bytes(json.dumps(record).encode("utf-8"))

    def test_plain_public_document_with_declared_review_is_consistent_not_approved(self):
        result = self.run_record(example())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DECLARATIONS_CONSISTENT", result.stdout)
        self.assertIn("not verified", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_unreleased_assessment_notes_cannot_be_cleared_by_generic_permission(self):
        record = example()
        record["evaluation"] = {
            "context": "active", "undisclosed_material": "present",
            "release_clearance": "unconfirmed",
        }
        result = self.run_record(record)
        self.assertEqual(result.returncode, 1)
        self.assertIn("evaluation: release clearance not verified", result.stdout)
        self.assertIn("evaluation: nonpublic evaluation material not cleared", result.stdout)

    def test_scope_and_visibility_mismatch_fail_even_when_other_checks_pass(self):
        record = example()
        record["destination"]["audience"] = "restricted"
        record["authority"]["scope"] = "unknown"
        result = self.run_record(record)
        self.assertEqual(result.returncode, 1)
        self.assertIn("visibility and intended audience differ", result.stdout)
        self.assertIn("disclosure scope not verified", result.stdout)

    def test_sanitization_and_review_are_independent(self):
        for changes in (
            {"review": "incomplete"},
            {"redistribution": "unknown"},
            {"sensitive_material": "present"},
            {"sensitive_material": "unknown"},
        ):
            with self.subTest(changes=changes):
                record = example()
                record["content"].update(changes)
                self.assertEqual(self.run_record(record).returncode, 1)

    def test_missing_approval_and_unresolved_evaluation_context_fail_closed(self):
        record = example()
        record["authority"]["publication"] = "unknown"
        record["evaluation"]["context"] = "unknown"
        record["evaluation"]["undisclosed_material"] = "unknown"
        result = self.run_record(record)
        self.assertEqual(result.returncode, 1)
        self.assertIn("REVIEW_REQUIRED", result.stdout)

    def test_assessment_material_with_explicit_release_clearance_is_not_auto_authorized(self):
        record = example()
        record["evaluation"] = {
            "context": "active", "undisclosed_material": "present",
            "release_clearance": "confirmed",
        }
        result = self.run_record(record)
        self.assertEqual(result.returncode, 0)
        self.assertIn("actual material, authority, audience and delivery not verified", result.stdout)

    def test_private_restricted_scope_is_not_confused_with_public_release(self):
        record = example()
        record["destination"] = {"visibility": "restricted", "audience": "restricted"}
        self.assertEqual(self.run_record(record).returncode, 0)

    def test_schema_errors_and_ambiguous_json_are_rejected(self):
        for payload in (
            b"{",
            b"\xff",
            b'{"schema_version":1,"schema_version":1}',
            b'{"x":NaN}',
            b" " * 32769,
            json.dumps({**example(), "schema_version": True}).encode("utf-8"),
        ):
            with self.subTest(payload=payload[:35]):
                result = self.run_bytes(payload)
                if payload.startswith(b"{") and payload.endswith(b"}") and b"NaN" not in payload and b"schema_version" in payload and b'"schema_version": true' in payload:
                    self.assertEqual(result.returncode, 1)
                else:
                    self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_unexpected_fields_and_nonstring_status_are_review_findings(self):
        for change in ("new", "bad"):
            record = example()
            if change == "new":
                record["destination"]["unknown_extra"] = "value"
            else:
                record["content"]["review"] = True
            result = self.run_record(record)
            self.assertEqual(result.returncode, 1)
            self.assertIn("REVIEW_REQUIRED", result.stdout)

    def test_no_private_text_is_echoed(self):
        record = example()
        record["extra"] = "SYNTHETIC_PRIVATE_MARKER"
        result = self.run_record(record)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("SYNTHETIC_PRIVATE_MARKER", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
