"""Read-only PR workflow contract and its real snapshot-check boundary."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from source_fixture import make_sources, snapshot_at

SOURCE = Path(__file__).resolve().parents[1]


class PullRequestValidationTests(unittest.TestCase):
    def workflow(self):
        return (SOURCE / '.github/workflows/pr-validation.yml').read_text()

    def test_pr_head_is_checked_without_write_permissions_or_upstream_execution(self):
        workflow = self.workflow()
        self.assertIn('  pull_request:', workflow)
        self.assertIn('ref: ${{ github.event.pull_request.head.sha }}', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertEqual(re.findall(r'^permissions:\n((?:  .+\n)+)', workflow, re.M), ['  contents: read\n'])
        self.assertNotRegex(workflow, r'(?m)^\s+permissions:|pull_request_target|secrets\.|GH_TOKEN|GITHUB_TOKEN|: write')
        actions = re.findall(r'uses: ([^\n]+)', workflow)
        self.assertEqual(len(actions), 2)
        self.assertTrue(all(re.fullmatch(r'actions/(checkout|setup-python)@[0-9a-f]{40}', action) for action in actions))
        commands = re.findall(r'^        run: (.+)$', workflow, re.M)
        self.assertEqual(commands, ['python -m unittest discover -s tests -v', 'python scripts/snapshot_sources.py verify'])
        self.assertNotIn('GIT_ALLOW_PROTOCOL', workflow.split('    steps:', 1)[0])
        self.assertEqual(workflow.count('GIT_ALLOW_PROTOCOL: file'), 2)
        self.assertIn('GIT_CONFIG_GLOBAL: /dev/null', workflow)
        self.assertIn('timeout-minutes: 15', workflow)

    def test_snapshot_check_accepts_complete_fixture_and_rejects_changed_bytes(self):
        workflow = self.workflow()
        command = re.findall(r'^        run: (.+)$', workflow, re.M)[1].split()
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            target = work / 'target'
            target.mkdir()
            env = os.environ.copy()
            env.update({'GIT_ALLOW_PROTOCOL': 'file', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'})
            repositories = make_sources(work, env)
            snapshot_at(target, repositories, env)
            shutil.copytree(SOURCE / 'scripts', target / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            command[0] = sys.executable
            good = subprocess.run(command, cwd=target, env=env, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            changed = target / 'upstream/matt-pocock/LICENSE'
            changed.write_text(changed.read_text() + '\nUnreviewed alteration\n')
            bad = subprocess.run(command, cwd=target, env=env, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
