"""Synthetic portable scanner regressions; no Clinical fixtures or private data.

Behavior cases follow the source test_spelling_scan.py's matching, mention,
staged, reporting, and unreadable-input seams. Provenance: docs/SPELLING_SCAN.md.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("assimilation_spelling_scan", ROOT / "scripts/spelling_scan.py")
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


class Matching(unittest.TestCase):
    def test_all_37_entries_and_american_counterparts(self):
        self.assertEqual((len(scan.TABLE), len(scan.STEM_CHANGES), len(scan.DRUGS)), (31, 3, 3))
        for form, american in scan.ALL_FORMS.items():
            with self.subTest(form=form):
                self.assertEqual([f.form for f in scan.scan_text(form.upper(), "a.md")], [form])
                self.assertEqual(scan.scan_text(american, "a.md"), [])
                self.assertEqual(scan.scan_text("prefix" + form + "suffix", "a.md"), [])

    # spelling-scan: mentions 4
    def test_bounded_inflections_and_negative_language_coverage(self):
        for word in ("colours", "behaviourally", "millilitres", "labelling"):
            self.assertEqual(len(scan.scan_text(word, "a.md")), 1)
        for word in ("greyhound", "seizure", "figure", "recognis" + "able", "organis" + "ation"):
            self.assertEqual(scan.scan_text(word, "a.md"), [])

    # spelling-scan: mentions 2
    def test_mentions_are_local_and_fences_are_not_exempt(self):
        self.assertEqual(scan.scan_text("`colour` and ``grey``", "a.md"), [])
        self.assertEqual(len(scan.scan_text("```\ncolour\n```", "a.md")), 1)

    # spelling-scan: mentions 4
    def test_python_exact_statement_count_not_file_exemption(self):
        text = '# spelling-scan: mentions 1\nvalue = "colour"\nother = "grey"\n'
        self.assertEqual([f.form for f in scan.scan_python_text(text, "a.py")], ["grey"])
        self.assertEqual(len(scan.scan_python_text('value = "`colour`"', "a.py")), 1)

    # spelling-scan: mentions 1
    def test_stale_detached_and_zero_declarations_refuse(self):
        for text in (
            '# spelling-scan: mentions 2\nvalue = "grey"\n',
            '# spelling-scan: mentions 1\n\nvalue = 0\n',
            '# spelling-scan: mentions 0\nvalue = 0\n',
        ):
            with self.assertRaises(scan.InputError):
                scan.path_findings("a.py", text)

    # spelling-scan: mentions 1
    def test_diagnostics_do_not_echo_input_or_parser_payload(self):
        finding = scan.scan_text("PRIVATE-SENTINEL grey", "docs/a.md")[0]
        self.assertNotIn("PRIVATE-SENTINEL", finding.render())
        with self.assertRaises(scan.InputError) as raised:
            scan.path_findings("a.py", '# spelling-scan: mentions 1\nPRIVATE-SENTINEL = "')
        self.assertNotIn("PRIVATE-SENTINEL", str(raised.exception))


class RepositoryModes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = mock.patch.object(scan, "REPO_ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def write(self, path, text):
        full = self.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf8")
        return full

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scan.main(list(args))
        return code, out.getvalue() + err.getvalue()

    # spelling-scan: mentions 6
    def test_staged_index_bytes_added_lines_quoted_names_and_filename(self):
        path = "docs/a space-é.md"
        self.write(path, "grey\nold\n")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.write(path, "grey\ncolour\n")
        self.write("docs/grey-helper.txt", "ignored contents")
        self.git("add", ".")
        self.write(path, "unstaged clean\n")
        report = scan.scan_staged()
        self.assertEqual([(f.path, f.line, f.form) for f in report.findings],
                         [(path, 2, "colour"), ("docs/grey-helper.txt", 0, "grey")])
        self.assertEqual(self.main()[0], 0)  # report remains advisory

    # spelling-scan: mentions 1
    def test_scope_prunes_upstream_licenses_generated_vendor_and_evidence(self):
        outside = ["upstream/README.md", "vendor/a.md", "evals/recorded/a.md",
                   "LICENSE.md", "THIRD_PARTY_NOTICES.md", "docs/NOTICE.md",
                   "scripts/generated/a.py", "docs/vendor/a.md"]
        for path in outside + ["docs/owned.md"]:
            self.write(path, "colour")
        self.git("add", ".")
        seen = []
        def read(path):
            seen.append(path)
            return scan.read_file(path)
        report = scan.scan(scan.tracked_files(), read)
        self.assertEqual(seen, ["docs/owned.md"])
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.excluded, len(outside))
        self.assertEqual(self.main("upstream/README.md")[0], 2)
        self.assertEqual(self.main("--record")[0], 0)
        evidence = scan.scan(scan.tracked_files(), records=True)
        self.assertEqual(evidence.findings, [])
        self.assertEqual(len(evidence.evidence), 1)
        self.assertIn("never findings", self.main("--record")[1])

    # spelling-scan: mentions 1
    def test_ci_read_fails_new_owned_prose_but_cli_is_advisory(self):
        self.write("README.md", "colour")
        self.git("add", ".")
        self.assertTrue(scan.scan(scan.tracked_files()).findings)
        code, output = self.main("--all")
        self.assertEqual(code, 0)
        self.assertIn("Unlisted forms are not detected", output)
        self.assertIn("untracked files unread", output)

    def test_unreadable_invalid_utf8_and_symlinks_refuse_without_clean_claim(self):
        for payload in (b"\xff", b"hello\0world"):
            path = self.write("docs/a.md", "")
            path.write_bytes(payload)
            code, output = self.main("docs/a.md")
            self.assertEqual(code, 2)
            self.assertNotIn("no listed form found", output)
        self.assertEqual(self.main("docs/missing.md")[0], 2)
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("PRIVATE-SENTINEL")):
            code, output = self.main("docs/a.md")
        self.assertEqual(code, 2)
        self.assertNotIn("PRIVATE-SENTINEL", output)
        link = self.root / "docs/link.md"
        link.symlink_to(path)
        self.assertEqual(self.main("docs/link.md")[0], 2)
        self.git("add", ".")
        self.assertEqual(self.main()[0], 2)

    def test_unreadable_directory_and_link_directory_refuse(self):
        self.write("docs/a.md", "plain")
        with mock.patch.object(os, "scandir", side_effect=PermissionError("PRIVATE-SENTINEL")):
            self.assertEqual(self.main("docs")[0], 2)
        (self.root / "docs/link").symlink_to(self.root / "docs", target_is_directory=True)
        self.assertEqual(self.main("docs/link")[0], 2)

    def test_external_paths_and_incomplete_git_population_refuse(self):
        self.assertEqual(self.main(str(self.root.parent / "outside.md"))[0], 2)
        with mock.patch.object(scan, "git_bytes", return_value=b"docs/a.md"):
            with self.assertRaises(scan.InputError):
                scan.tracked_files()

    def test_untracked_population_and_quiet_clean(self):
        self.write("docs/a.md", "plain")
        self.assertEqual(scan.scan(scan.tracked_files()).files_read, 0)
        self.assertEqual(self.main("--all", "--quiet"), (0, ""))


class MaintainedWritingRegression(unittest.TestCase):
    def test_tracked_maintained_writing_has_no_listed_uses(self):
        """Normal unittest discovery enforces only the declared owned population."""
        report = scan.scan(scan.tracked_files())
        self.assertEqual(report.findings, [], "\n".join(f.render() for f in report.findings))


if __name__ == "__main__":
    unittest.main()
