"""Safe publisher diagnostics at the gh process boundary; no child is executed."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_update import GitHub


class PublisherDiagnosticsTests(unittest.TestCase):
    def error(self, body, stderr="gh: withheld (HTTP 403)"):
        result = subprocess.CompletedProcess([], 1, stdout=body, stderr=stderr)
        with patch("subprocess.run", return_value=result) as run:
            with self.assertRaises(RuntimeError) as caught:
                GitHub("fixture/assimilation").request("POST", "/git/trees", {"tree": [{}, {}]})
            self.assertEqual(run.call_count, 1, "A denied request must not be retried")
        return str(caught.exception)

    def test_identifies_resource_access_hint_without_echoing_response(self):
        for message in ("Resource not accessible by integration",
                        "Resource not accessible by personal access token"):
            with self.subTest(message=message):
                error = self.error(json.dumps({"message": message, "private": "synthetic-secret"}))
                self.assertIn("HTTP 403; service hint=resource-access-denied; tree entries=2", error)
                self.assertNotIn(message, error)
                self.assertNotIn("synthetic-secret", error)

    def test_secondary_limit_is_a_hint_not_a_retry(self):
        error = self.error(json.dumps({"message": "You have exceeded a secondary rate limit. Please wait before you try again."}))
        self.assertIn("service hint=secondary-rate-limit", error)
        self.assertNotIn("Please wait", error)

    def test_primary_limit_does_not_disclose_subject_or_service_fields(self):
        error = self.error(json.dumps({"message": "API rate limit exceeded for synthetic-private-subject.",
                                     "documentation_url": "https://private.invalid/account"}),
                           "gh: synthetic-private-stderr (HTTP 429)")
        self.assertIn("HTTP 429; service hint=primary-rate-limit", error)
        self.assertNotIn("synthetic-private", error)
        self.assertNotIn("private.invalid", error)

    def test_arbitrary_denial_is_unclassified_and_redacted(self):
        error = self.error(json.dumps({"message": "synthetic-secret: Resource not accessible by integration"}),
                           "gh: synthetic-secret (HTTP 403)")
        self.assertIn("service hint=unclassified", error)
        self.assertNotIn("synthetic-secret", error)

    def test_invalid_or_unstructured_body_keeps_original_failure(self):
        for body in ("", "synthetic-secret", "null", "[]", "{}", '{"message": {}}',
                     '[' * 2000 + '0' + ']' * 2000):
            with self.subTest(body_type=body[:20]):
                error = self.error(body)
                self.assertIn("HTTP 403; service hint=unclassified; tree entries=2", error)
                self.assertNotIn("synthetic-secret", error)

    def test_oversized_response_is_not_classified_or_echoed(self):
        error = self.error(json.dumps({"message": "Resource not accessible by integration",
                                     "private": "synthetic-secret" * 1000}))
        self.assertIn("service hint=unclassified", error)
        self.assertNotIn("synthetic-secret", error)

    def test_nonstandard_json_constants_refuse_even_with_recognized_message(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                body = '{"message":"Resource not accessible by integration","extra":' + constant + '}'
                self.assertIn("service hint=unclassified", self.error(body))

    def test_container_depth_limit_includes_unused_recognized_response_data(self):
        for extra_containers, expected in ((15, "resource-access-denied"), (16, "unclassified")):
            with self.subTest(extra_containers=extra_containers):
                nested = 0
                for unused in range(extra_containers):
                    nested = [nested]
                body = json.dumps({"message": "Resource not accessible by integration", "extra": nested})
                self.assertIn("service hint=" + expected, self.error(body))

    def test_duplicate_key_cannot_hide_an_overdepth_extra_field(self):
        body = ('{"message":"Resource not accessible by integration","extra":'
                + '[' * 16 + '0' + ']' * 16 + ',"extra":0}')
        self.assertIn("service hint=unclassified", self.error(body))

    def test_absent_status_is_explicit_and_stderr_is_not_echoed(self):
        error = self.error("", "synthetic-secret transport failure")
        self.assertIn("HTTP status unavailable; service hint=unclassified", error)
        self.assertNotIn("synthetic-secret", error)

    def test_success_preserves_json_result_without_diagnostic_reinterpretation(self):
        result = subprocess.CompletedProcess([], 0, stdout='{"sha": "synthetic-object"}', stderr="")
        with patch("subprocess.run", return_value=result) as run:
            self.assertEqual(GitHub("fixture/assimilation").request("GET", "/git/trees/synthetic"),
                             {"sha": "synthetic-object"})
            self.assertEqual(run.call_count, 1)
