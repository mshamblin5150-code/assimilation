"""Observable behavior of the isolated cold-start evaluation harness."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]


class ColdStartEvaluationTests(unittest.TestCase):
    def test_grader_detects_bug_then_real_fix_and_protected_file_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            trial = Path(folder) / 'trial'
            prepare = [sys.executable, str(ROOT / 'evals/cold-start/prepare.py'), str(trial)]
            created = subprocess.run(prepare, capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            grade = [sys.executable, str(ROOT / 'evals/cold-start/grade.py'), str(trial)]
            before = subprocess.run(grade, capture_output=True, text=True)
            self.assertEqual(before.returncode, 1)
            self.assertFalse(json.loads(before.stdout)['functional_pass'])
            self.assertTrue(json.loads(before.stdout)['project_tests_pass'])
            source = trial / 'project/shipping.py'
            source.write_text(source.read_text().replace('subtotal > 50', 'subtotal >= 50'))
            after = subprocess.run(grade, capture_output=True, text=True)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertTrue(json.loads(after.stdout)['functional_pass'])
            (trial / 'project/README.md').write_text('Changed without authority\n')
            invalid = subprocess.run(grade, capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse(json.loads(invalid.stdout)['protected_files_unchanged']['README.md'])
            repeat = subprocess.run(prepare, capture_output=True, text=True)
            self.assertNotEqual(repeat.returncode, 0)
            self.assertEqual((trial / 'project/README.md').read_text(), 'Changed without authority\n')
