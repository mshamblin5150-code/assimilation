"""Read-only PR workflow contract and its real snapshot-check boundary."""
import os
import hashlib
import importlib.util
import json
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
        self.assertEqual(len(actions), 4)
        self.assertTrue(all(re.fullmatch(r'actions/(checkout|setup-python)@[0-9a-f]{40}', action) for action in actions))
        commands = re.findall(r'^        run: (.+)$', workflow, re.M)
        self.assertEqual(commands, ['python -m unittest discover -s tests -v', 'python scripts/snapshot_sources.py verify',
                                    'python -B tests/windows_contract.py --expected-sha "$env:CONTRACT_EXPECTED_SHA"',
                                    'python -B -m unittest discover -s tests -p test_windows_onboarding.py -v'])
        self.assertEqual(workflow.count('ref: ${{ github.event.pull_request.head.sha }}'), 2)
        self.assertEqual(workflow.count('persist-credentials: false'), 2)
        self.assertNotIn('GIT_ALLOW_PROTOCOL', workflow.split('    steps:', 1)[0])
        self.assertEqual(workflow.count('GIT_ALLOW_PROTOCOL: file'), 2)
        self.assertIn('GIT_CONFIG_GLOBAL: /dev/null', workflow)
        self.assertIn('timeout-minutes: 15', workflow)

    def test_windows_job_is_refusal_and_onboarding_only_and_binds_contract_source_bytes(self):
        workflow = self.workflow()
        windows = workflow.split('  windows-contract:\n', 1)[1]
        self.assertIn('runs-on: windows-2022', windows)
        self.assertIn('timeout-minutes: 10', windows)
        self.assertIn("PYTHONDONTWRITEBYTECODE: '1'", windows)
        expected = json.loads(re.search(r"CONTRACT_SOURCE_SHA256: '(.*)'", windows)[1])
        files = {'scripts/skills.py', 'scripts/snapshot_sources.py', 'scripts/git_runtime.py',
                 'scripts/propose_update.py', 'scripts/publish_update.py', 'tests/windows_contract.py'}
        self.assertEqual(set(expected), files)
        self.assertEqual(expected, {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in files})
        onboarding = 'python -B -m unittest discover -s tests -p test_windows_onboarding.py -v'
        self.assertEqual(re.findall(r'^        run: (.+)$', windows, re.M),
                         ['python -B tests/windows_contract.py --expected-sha "$env:CONTRACT_EXPECTED_SHA"',
                          onboarding])
        self.assertEqual(windows.count(onboarding), 1)
        self.assertNotRegex(windows.replace(onboarding, ''),
                            r'pip install|git fetch|unittest discover|skills.py install|snapshot_sources.py verify')

    @unittest.skipIf(sys.platform == 'win32', 'Linux negative control; native contract is run separately')
    def test_native_contract_refuses_to_claim_windows_on_another_platform(self):
        result = subprocess.run([sys.executable, '-B', str(SOURCE / 'tests/windows_contract.py'),
                                 '--expected-sha', '0' * 40], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('requires actual Windows; no native checks ran', result.stderr)
        self.assertNotIn('WINDOWS_CONTRACT_RESULT', result.stdout)

    def test_contract_monitor_rejects_direct_os_metadata_probes(self):
        spec = importlib.util.spec_from_file_location('windows_contract_monitor', SOURCE / 'tests/windows_contract.py')
        monitor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(monitor)
        operations = (lambda: os.stat(SOURCE / 'scripts/skills.py'),
                      lambda: os.lstat(SOURCE / 'scripts/skills.py'),
                      lambda: os.access(SOURCE / 'scripts/skills.py', os.R_OK),
                      lambda: os.stat(monitor.LOCALE_ROOT / '..' / 'escape.mo'))
        for operation in operations:
            with self.subTest(operation=operation):
                monitor.ATTEMPTS.clear()
                with self.assertRaisesRegex(AssertionError, 'Contract attempted filesystem'), monitor.no_source_io():
                    operation()
                self.assertEqual(len(monitor.ATTEMPTS), 1)

    @unittest.skipIf(os.name == 'nt', 'POSIX synthetic checkout control; native contract checks actual Windows bytes separately')
    def test_scoped_lf_attributes_preserve_contract_bytes_under_autocrlf(self):
        names = ('scripts/skills.py', 'scripts/snapshot_sources.py', 'scripts/git_runtime.py',
                 'scripts/propose_update.py', 'scripts/publish_update.py', 'tests/windows_contract.py')
        attributes = (SOURCE / '.gitattributes').read_bytes()
        declarations = [line for line in attributes.decode('ascii').splitlines() if line and not line.startswith('#')]
        self.assertEqual(set(declarations), {f'/{name} text eol=lf' for name in names})
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            repo = work / 'source'
            repo.mkdir()
            env = {**os.environ, 'GIT_ALLOW_PROTOCOL': 'file', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}

            def git(*args, cwd=repo):
                return subprocess.run(['git', *args], cwd=cwd, env=env, check=True, capture_output=True)

            git('init', '--quiet')
            git('config', 'user.name', 'Synthetic Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            expected = {name: (SOURCE / name).read_bytes() for name in names}
            for name, raw in expected.items():
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            (repo / 'outside.txt').write_bytes(b'Outside the scoped declaration\n')
            git('add', '.')
            git('commit', '--quiet', '-m', 'unattributed fixture')
            before = work / 'before'
            git('-c', 'core.autocrlf=true', 'clone', '--quiet', str(repo), str(before), cwd=work)
            for name, raw in expected.items():
                self.assertNotEqual((before / name).read_bytes(), raw)
                self.assertEqual((before / name).read_bytes().replace(b'\r\n', b'\n'), raw)
            (repo / '.gitattributes').write_bytes(attributes)
            git('add', '.gitattributes')
            git('commit', '--quiet', '-m', 'scoped LF declaration')
            after = work / 'after'
            git('-c', 'core.autocrlf=true', 'clone', '--quiet', str(repo), str(after), cwd=work)
            for name, raw in expected.items():
                self.assertEqual((after / name).read_bytes(), raw)
            self.assertEqual((after / 'outside.txt').read_bytes(), b'Outside the scoped declaration\r\n')

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
