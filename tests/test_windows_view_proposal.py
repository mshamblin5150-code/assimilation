"""Synthetic proposal parsing only; no native installation acceptance."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from windows_view_proposal import parse_proposal

VIEW = b'{"files":[{"origin":{"blob":"1111111111111111111111111111111111111111","mode":"100644","path":"docs/a.txt"},"path":"docs/a.txt","sha256":"2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824","size":5}],"mapping":"regular-files-only-v1","schema":"generated-files-v1","source":{"commit":"1111111111111111111111111111111111111111","lock_sha256":"3333333333333333333333333333333333333333333333333333333333333333","object_format":"sha1","tree":"2222222222222222222222222222222222222222"}}'


def plan_bytes():
    return json.dumps({
        "schema": "installation-plan-proposal-v1",
        "view_sha256": "51cc4ccf94eaf4445ad4ce1a3547b29a76ffdf1664cdb727bba31b3e6b59673e",
        "destination_display": "synthetic destination",
        "destination_binding": "unqualified",
        "effects": [{"action": "create", "path": "docs/a.txt", "before": None,
                     "after": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"}],
        "activation": "none", "recovery": "unqualified",
    }).encode()


class ProposalTests(unittest.TestCase):
    def test_unknown_view_field_is_refused(self):
        value = json.loads(VIEW)
        value["approved"] = True
        with self.assertRaisesRegex(ValueError, "invalid-fields"):
            parse_proposal(json.dumps(value).encode(), plan_bytes())

    def test_malformed_encoding_and_duplicate_fields_are_refused(self):
        cases = [b"[]", b"{}{}", bytes([255]), bytes([239, 187, 191]) + VIEW,
                 VIEW.replace(b'"schema":', b'"schema":"generated-files-v1","schema":')]
        for raw in cases:
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                parse_proposal(raw, plan_bytes())

    def test_unsupported_view_shapes_are_refused(self):
        for key, bad in [("schema", 2), ("mapping", "flatten"), ("files", []),
                         ("source", {}), ("files", [None])]:
            value = json.loads(VIEW)
            value[key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                parse_proposal(json.dumps(value).encode(), plan_bytes())

    def test_unsafe_and_colliding_view_names_are_refused(self):
        for paths, reason in [(("NUL.txt",), "unsupported-windows-component"),
                              (("../a",), "unsupported-windows-component"),
                              (("é.txt",), "unsupported-windows-component"),
                              (("a", "a/b"), "file-directory-collision"),
                              (("A.txt", "a.txt"), "casefold-collision"),
                              (("b.txt", "a.txt"), "unsorted-files")]:
            value = json.loads(VIEW)
            template = value["files"][0]
            value["files"] = [dict(template, path=path) for path in paths]
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, reason):
                parse_proposal(json.dumps(value).encode(), plan_bytes())

    def test_malformed_or_mismatched_plan_is_refused(self):
        for key, bad in [("approved", True), ("schema", "v2"),
                         ("destination_binding", "verified"), ("activation", "install"),
                         ("recovery", "qualified"), ("destination_display", ""),
                         ("effects", []), ("view_sha256", "0" * 64)]:
            value = json.loads(plan_bytes())
            value[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_proposal(VIEW, json.dumps(value).encode())

    def test_effects_match_exact_view_paths_and_bytes(self):
        for key, bad in [("action", "delete"), ("action", "replace"), ("path", "DOCS/a.txt"),
                         ("before", {}), ("after", "0" * 64), ("extra", 0)]:
            value = json.loads(plan_bytes())
            value["effects"][0][key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_proposal(VIEW, json.dumps(value).encode())
        value = json.loads(plan_bytes())
        value["effects"] *= 2
        with self.assertRaises(ValueError):
            parse_proposal(VIEW, json.dumps(value).encode())

    def test_surrogate_display_is_refused(self):
        value = json.loads(plan_bytes())
        value["destination_display"] = chr(0xd800)
        with self.assertRaises(ValueError):
            parse_proposal(VIEW, json.dumps(value).encode())

    def test_valid_proposal_returns_canonical_view(self):
        result = parse_proposal(VIEW, plan_bytes())
        self.assertEqual(result.canonical_view, VIEW)

    def test_worked_fixture_has_known_digests(self):
        result = parse_proposal(VIEW, plan_bytes())
        self.assertEqual(result.view_sha256,
                         "51cc4ccf94eaf4445ad4ce1a3547b29a76ffdf1664cdb727bba31b3e6b59673e")
        self.assertEqual(result.plan_sha256,
                         "70e11782295fea38e9a31600bba8a2ab5766e732e0ffa6b8da1e1bfb690e3ad0")

    def test_canonical_display_has_exact_escapes(self):
        value = json.loads(plan_bytes())
        value["destination_display"] = 'a/b\n\t\b\f\r"\\\x00\x7fé😀'
        result = parse_proposal(VIEW, json.dumps(value).encode())
        self.assertIn(
            b'"destination_display":"a/b\\n\\t\\b\\f\\r\\"\\\\\\u0000\\u007f\\u00e9\\ud83d\\ude00"',
            result.canonical_plan,
        )

    def test_whitespace_and_input_key_order_do_not_change_result(self):
        formatted = json.dumps(json.loads(VIEW), indent=2).encode()
        self.assertEqual(parse_proposal(formatted, plan_bytes()),
                         parse_proposal(VIEW, plan_bytes()))

    def test_non_bytes_and_oversized_input_are_refused(self):
        for raw in (VIEW.decode(), bytearray(VIEW), None, b" " * (8 * 1024 * 1024 + 1)):
            with self.subTest(kind=type(raw)), self.assertRaisesRegex(ValueError, "invalid-json-input"):
                parse_proposal(raw, plan_bytes())
            with self.subTest(plan_kind=type(raw)), self.assertRaisesRegex(ValueError, "invalid-json-input"):
                parse_proposal(VIEW, raw)

    def test_invalid_source_and_payload_fields_are_refused_before_binding(self):
        for field, bad in [("size", True), ("size", -1), ("size", 1.0),
                           ("size", 2**53), ("size", float("nan")),
                           ("sha256", "A" * 64), ("sha256", []), ("origin", {})]:
            value = json.loads(VIEW)
            value["files"][0][field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaisesRegex(ValueError, "invalid-(size|digest|fields)"):
                parse_proposal(json.dumps(value).encode(), plan_bytes())
        for field, bad in [("mode", "120000"), ("mode", "100755"),
                           ("blob", "1" * 64), ("path", "../x")]:
            value = json.loads(VIEW)
            value["files"][0]["origin"][field] = bad
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "unsupported-source-mode|invalid-digest|unsupported-windows-component"):
                parse_proposal(json.dumps(value).encode(), plan_bytes())

    def test_duplicate_nested_plan_field_is_refused(self):
        raw = plan_bytes().replace(b'"action":', b'"action":"create","action":')
        with self.assertRaisesRegex(ValueError, "duplicate-field"):
            parse_proposal(VIEW, raw)

    def test_two_sha256_files_require_matching_effect_order(self):
        view = json.loads(VIEW)
        view["source"].update(object_format="sha256", commit="1" * 64, tree="2" * 64)
        view["files"][0]["origin"]["blob"] = "1" * 64
        second = json.loads(json.dumps(view["files"][0]))
        second["path"] = "docs/b.txt"
        second["origin"]["path"] = "docs/b.txt"
        view["files"].append(second)
        raw = json.dumps(view, sort_keys=True, separators=(",", ":")).encode()
        plan = json.loads(plan_bytes())
        plan["view_sha256"] = hashlib.sha256(raw).hexdigest()
        plan["effects"].append(dict(plan["effects"][0], path="docs/b.txt"))
        result = parse_proposal(raw, json.dumps(plan).encode())
        self.assertEqual(result.canonical_view, raw)
        plan["effects"].reverse()
        with self.assertRaisesRegex(ValueError, "effect-binding-mismatch"):
            parse_proposal(raw, json.dumps(plan).encode())


if __name__ == "__main__":
    unittest.main()
