"""Include the standalone synthetic lesson verifier in offline PR validation."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

LAB = Path(__file__).resolve().parents[1] / "examples/chad-architecture-lab"


class ArchitectureLabTests(unittest.TestCase):
    def test_all_declared_teaching_outcomes_are_verified(self):
        result = subprocess.run([sys.executable, "-B", str(LAB / "verify_lab.py")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["outcomes"][-1], {
            "stage": "unchanged-original-source-rerun", "tests_run": 6, "passed": 6,
            "expected_behavior_failures": [], "errors": 0, "skips": 0})

    def test_demo_reports_the_hidden_state_bug_without_touching_inputs(self):
        result = subprocess.run([sys.executable, "-B", str(LAB / "demo.py"),
                                 "--stage", "03-tangled", "--scenario", "repeat"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["plan"], {"rows": [
            {"source": "drawing.jpg", "category": "Images", "destination": "Images/drawing.jpg"}
        ], "counts": {"Text": 1, "Images": 1, "Keep": 1}})
        self.assertEqual((report["earlier_plan_stable"], report["input_files_preserved"]),
                         (False, True))

    def test_demo_rejects_a_user_folder_argument(self):
        result = subprocess.run([sys.executable, "-B", str(LAB / "demo.py"),
                                 "--folder", "not-an-authorized-target"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
