"""Exercise the actual offline teaching contract in existing PR validation."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DistinctivenessLessonTests(unittest.TestCase):
    def test_instructor_satisfies_public_behavior_without_skips(self):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s",
             "examples/chad-add-distinctiveness/instructor", "-p", "test_readiness.py", "-v"],
            cwd=ROOT, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertRegex(output, r"Ran [1-9][0-9]* tests")
        self.assertNotIn("skipped", output.lower())


if __name__ == "__main__":
    unittest.main()
