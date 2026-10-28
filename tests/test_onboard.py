"""Exercise the cold-start CLI, not an agent's ability to repeat instructions."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from source_fixture import make_sources, snapshot_at

SOURCE = Path(__file__).resolve().parents[1]


class OnboardTests(unittest.TestCase):
    def run_cli(self, *args, root=SOURCE, env=None):
        with tempfile.TemporaryDirectory() as elsewhere:
            return subprocess.run([sys.executable, '-B', str(root / 'scripts/onboard.py'), *args],
                                  cwd=elsewhere, env=env, capture_output=True, text=True)

    def test_inspection_from_another_directory_reports_verified_original_files_not_host_claims(self):
        result = self.run_cli('inspect')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'verified')
        self.assertEqual(report['capabilities']['python']['status'], 'observed-running')
        self.assertEqual(report['capabilities']['delegation']['status'], 'unknown')
        self.assertEqual(report['capabilities']['network']['status'], 'not-probed')
        self.assertFalse(report['skills_loaded'])
        self.assertEqual(set(report['sources']), {'matt', 'pstack'})
        skills = report['skills']
        self.assertGreater(len(skills), 0)
        for skill in skills:
            data = (SOURCE / skill['path']).read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            self.assertEqual(skill['git_blob_sha'], blob)
            self.assertEqual(skill['commit'], report['sources'][skill['source']]['commit'])

    def test_bug_route_points_to_original_skills_and_requires_actual_reads(self):
        result = self.run_cli('route', '--task-type', 'bug')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        paths = [entry['path'] for entry in report['skills']]
        self.assertIn('upstream/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md', paths)
        self.assertIn('upstream/pstack/skills/principle-fix-root-causes/SKILL.md', paths)
        self.assertFalse(report['skills_loaded'])
        self.assertIn('Read each returned original SKILL.md', ' '.join(report['next_actions']))
        self.assertEqual(report['task_type'], 'bug')

    def test_unknown_route_stays_uncertain_and_does_not_invent_an_implementation_plan(self):
        result = self.run_cli('route', '--task-type', 'unknown')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'needs-context')
        self.assertIn('ask-matt/SKILL.md', report['skills'][0]['path'])
        self.assertIn('operator goal', ' '.join(report['next_actions']))
        self.assertFalse(report['skills_loaded'])

    def test_all_deliberate_routes_resolve_and_report_no_execution(self):
        for task_type in ('feature', 'review', 'planning', 'writing'):
            with self.subTest(task_type=task_type):
                result = self.run_cli('route', '--task-type', task_type)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual({skill['source'] for skill in report['skills']}, {'matt', 'pstack'})
                self.assertLessEqual(len(report['skills']), 3)
                self.assertFalse(report['skills_loaded'])

    def test_git_unavailable_is_not_inferred_as_network_or_delegation_access(self):
        result = self.run_cli('inspect', env={**os.environ, 'PATH': ''})
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['capabilities']['git']['status'], 'not-found-on-path')
        self.assertEqual(report['capabilities']['network']['status'], 'not-probed')
        self.assertEqual(report['capabilities']['delegation']['status'], 'unknown')

    def copied_repo(self, folder):
        root = Path(folder) / 'reference'
        root.mkdir()
        for name in ('scripts', 'upstream'):
            shutil.copytree(SOURCE / name, root / name, symlinks=True,
                            ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('sources.lock.json', 'sources.snapshot.json'):
            shutil.copy2(SOURCE / name, root / name)
        return root

    def test_changed_or_missing_sources_fail_closed_without_private_error_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.copied_repo(folder)
            skill = root / 'upstream/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md'
            skill.write_text('synthetic-private-marker-do-not-echo')
            result = self.run_cli('route', '--task-type', 'bug', root=root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['error'], 'source-verification-failed')
            self.assertNotIn('synthetic-private-marker', result.stdout + result.stderr)
            (root / 'sources.snapshot.json').unlink()
            missing = self.run_cli('inspect', root=root)
            self.assertNotEqual(missing.returncode, 0)
            self.assertEqual(json.loads(missing.stdout)['status'], 'blocked')

    def test_invalid_arguments_are_json_and_do_not_echo_untrusted_values(self):
        result = self.run_cli('route', '--task-type', 'synthetic-private-argument')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error'], 'invalid-arguments')
        self.assertNotIn('synthetic-private-argument', result.stdout + result.stderr)

    def test_helper_does_not_write_or_install_into_reference_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.copied_repo(folder)
            def digest_tree():
                return {p.relative_to(root).as_posix():
                        (os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest())
                        for p in root.rglob('*') if p.is_file() or p.is_symlink()}
            before = digest_tree()
            result = self.run_cli('route', '--task-type', 'review', root=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(digest_tree(), before)

    def test_valid_smaller_snapshot_does_not_invent_missing_route_skills(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            root = work / 'reference'
            root.mkdir()
            shutil.copytree(SOURCE / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            env = {**os.environ, 'GIT_ALLOW_PROTOCOL': 'file', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
            repositories = make_sources(work, env)
            snapshot_at(root, repositories, env)
            inspected = self.run_cli('inspect', root=root, env=env)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            result = self.run_cli('route', '--task-type', 'bug', root=root, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['error'], 'route-skill-unavailable')


if __name__ == '__main__':
    unittest.main()
