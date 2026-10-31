"""Verify known teaching outcomes; unexpected passes, failures and errors fail."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import checks

BASE = ["test_text_and_unknown_plan", "test_preview_preserves_files_and_ignores_directories"]
CATEGORY = "test_jpg_has_an_image_destination"
SUMMARY = "test_summary_counts_match_the_plan"
ISOLATION = "test_later_preview_does_not_change_an_earlier_plan"
UPPERCASE = "test_uppercase_extensions_have_matching_rows_and_counts"
ALL = BASE + [CATEGORY, SUMMARY, ISOLATION, UPPERCASE]


def check(stage, names, expected_failures=None, preview_module=None):
    expected_failures = expected_failures or {}
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        checks.suite(stage, names, preview_module))
    failures = {test._testMethodName: trace for test, trace in result.failures}
    if (result.testsRun != len(names) or result.errors or result.skipped
            or result.expectedFailures or result.unexpectedSuccesses
            or set(failures) != set(expected_failures)
            or any(marker not in failures[name] for name, marker in expected_failures.items())):
        raise AssertionError(f"Unexpected outcome for {stage}:\n{stream.getvalue()}")
    return {"stage": stage, "tests_run": result.testsRun,
            "passed": result.testsRun - len(failures),
            "expected_behavior_failures": sorted(failures),
            "errors": 0, "skips": 0}


def verify():
    outcomes = [
        check("01-start", BASE + [CATEGORY],
              {CATEGORY: "JPG category is part of the proposed plan"}),
        check("02-category", BASE + [CATEGORY, SUMMARY],
              {SUMMARY: "Summary counts describe the proposed plan"}),
        check("03-tangled", BASE + [CATEGORY, SUMMARY]),
        check("03-tangled", [ISOLATION],
              {ISOLATION: "Earlier preview remains a stable plan"}),
        check("04-deepened", ALL,
              {UPPERCASE: "Uppercase extensions agree in rows and summary"}),
        check("05-casefold", ALL),
    ]
    # Mutate a disposable source copy, not the tracked implementation or a mock.
    final_path = checks.ROOT / "stages/05-casefold/preview.py"
    original = final_path.read_bytes()
    source = original.decode("utf-8")
    needle = 'path.suffix.lower()'
    if source.count(needle) != 1:
        raise AssertionError("Mutation target changed: inspect before adapting the demonstration")
    with tempfile.TemporaryDirectory(prefix="architecture-mutant-") as temp:
        mutant = Path(temp) / "preview.py"
        mutant.write_text(source.replace(needle, "path.suffix"), encoding="utf-8")
        outcome = check("05-casefold", [UPPERCASE],
                        {UPPERCASE: "Uppercase extensions agree in rows and summary"},
                        checks.load_source(mutant))
        outcome["stage"] = "disposable-case-sensitive-mutant"
        outcomes.append(outcome)
    if final_path.read_bytes() != original:
        raise AssertionError("Tracked final source changed during mutation demonstration")
    restored = check("05-casefold", ALL)
    restored["stage"] = "unchanged-original-source-rerun"
    outcomes.append(restored)
    return {"status": "verified", "outcomes": outcomes,
            "scope": "finite synthetic preview-only teaching cases, not installation or agent obedience"}


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("verify_lab.py accepts no arguments or user paths")
    print(json.dumps(verify(), indent=2, sort_keys=True))
