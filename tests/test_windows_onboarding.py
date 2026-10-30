"""Exercise the standalone prerequisite report without source or host changes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import contextlib
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import windows_onboarding

MONITOR_ACTIVE = False
ATTEMPTS = []


def boundary_monitor(event, args):
    if MONITOR_ACTIVE and (event == 'open' or event.startswith(('subprocess.', 'socket.'))
                           or event in ('os.system', 'os.mkdir', 'os.remove', 'os.rename',
                                        'os.chmod', 'os.listdir', 'os.scandir', 'os.symlink',
                                        'os.link', 'os.putenv', 'os.unsetenv', 'os.chdir')):
        ATTEMPTS.append(event)
        raise PermissionError('test-boundary-blocked')


sys.addaudithook(boundary_monitor)

ROOT = Path(__file__).resolve().parents[1]


class WindowsOnboardingTests(unittest.TestCase):
    def test_minimum_python_prerequisite_is_reported_without_admission(self):
        for version, status in (((3, 9, 9), 'unsupported'), ((3, 10, 0), 'satisfied'),
                                ((3, 12, 8), 'satisfied')):
            with self.subTest(version=version), patch('sys.version_info', version):
                result = windows_onboarding.report()
                self.assertEqual(result['python_prerequisite'],
                                 {'minimum': [3, 10], 'status': status})
                self.assertFalse(result['installation_admitted'])
                if status == 'unsupported':
                    self.assertIn('Python 3.10', ' '.join(result['next_actions']))

    def run_cli(self, *args, env=None):
        return subprocess.run(
            [sys.executable, '-B', str(ROOT / 'scripts/windows_onboarding.py'), *args],
            capture_output=True, text=True, env=env, cwd=ROOT)

    def test_running_environment_is_observed_without_installation_admission(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['runtime']['platform'], sys.platform)
        self.assertEqual(report['runtime']['python'], list(sys.version_info[:3]))
        self.assertEqual(report['status'], 'observed-not-qualified')
        self.assertFalse(report['installation_admitted'])
        self.assertFalse(report['filesystem_verified'])
        self.assertFalse(report['source_verified'])
        self.assertEqual(report['git']['execution'], 'not-probed')

    def test_absent_path_and_environment_markers_do_not_leak_values_or_claim_git_readiness(self):
        env = {**os.environ, 'PATH': '', 'VIRTUAL_ENV': 'synthetic-private-environment',
               'CONDA_PREFIX': 'synthetic-private-conda', 'TOKEN': 'synthetic-private-token'}
        result = self.run_cli(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['git']['discovery'], 'not-probed')
        self.assertEqual(report['git']['availability'], 'unverified')
        self.assertEqual(report['environment']['markers'], ['virtual-env', 'conda'])
        self.assertEqual(report['environment']['status'], 'markers-only-not-validated')
        self.assertIn('Do not install', ' '.join(report['next_actions']))
        self.assertNotIn('synthetic-private', result.stdout + result.stderr)

    def test_unknown_arguments_are_refused_without_echo_and_help_does_not_probe(self):
        result = self.run_cli('synthetic-private-argument')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error'], 'invalid-arguments')
        self.assertNotIn('synthetic-private', result.stdout + result.stderr)
        help_result = self.run_cli('--help')
        self.assertEqual(help_result.returncode, 0)
        self.assertIn('No installation', help_result.stdout)

    def test_native_identity_and_runtime_eligibility_are_separate_from_permissions(self):
        report = windows_onboarding.report()
        expected = 'native-windows-unsupported' if sys.platform == 'win32' and os.name == 'nt' else 'not-qualified'
        self.assertEqual(report['source_operations'], expected)
        self.assertEqual(report['runtime']['windows_version'],
                         list(sys.getwindowsversion()[:3]) if sys.platform == 'win32' else None)
        for boundary in ('acl', 'ownership', 'junctions', 'symlinks', 'rollback', 'concurrency', 'msys'):
            self.assertEqual(report['qualification'][boundary], 'not-probed')

    def test_runtime_observation_failure_is_safe_and_does_not_trigger_fallback(self):
        with patch('sys.platform', 'win32'), \
                patch('sys.getwindowsversion', create=True,
                      side_effect=OSError('synthetic-private-denial')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = windows_onboarding.main([])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())['error'], 'observation-unavailable')
        self.assertNotIn('synthetic-private', output.getvalue())

    def test_report_does_not_search_paths_or_query_filesystem_metadata(self):
        with patch('shutil.which', side_effect=AssertionError('discovery forbidden')), \
                patch('os.stat', side_effect=AssertionError('metadata forbidden')), \
                patch('os.access', side_effect=AssertionError('metadata forbidden')):
            report = windows_onboarding.report()
        self.assertEqual(report['git']['discovery'], 'not-probed')
        self.assertEqual(report['git']['availability'], 'unverified')

    def test_report_and_help_attempt_no_payload_io_process_network_or_mutation(self):
        global MONITOR_ACTIVE
        ATTEMPTS.clear()
        output = io.StringIO()
        try:
            MONITOR_ACTIVE = True
            with contextlib.redirect_stdout(output):
                self.assertEqual(windows_onboarding.main([]), 0)
                self.assertEqual(windows_onboarding.main(['--help']), 0)
                self.assertEqual(windows_onboarding.main(['private-argument']), 2)
        finally:
            MONITOR_ACTIVE = False
        self.assertEqual(ATTEMPTS, [])

    def test_monitor_positive_controls_detect_each_prohibited_boundary(self):
        global MONITOR_ACTIVE
        for event in ('open', 'subprocess.Popen', 'socket.connect', 'os.mkdir', 'os.listdir'):
            with self.subTest(event=event):
                ATTEMPTS.clear()
                try:
                    MONITOR_ACTIVE = True
                    with self.assertRaises(PermissionError):
                        sys.audit(event, 'synthetic-no-operation')
                finally:
                    MONITOR_ACTIVE = False
                self.assertEqual(ATTEMPTS, [event])


if __name__ == '__main__':
    unittest.main()
