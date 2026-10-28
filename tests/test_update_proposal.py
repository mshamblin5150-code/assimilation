"""Offline CLI checks for monthly update proposals; no upstream code is executed."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


class UpdateProposalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.target = self.work / "assimilation"
        self.target.mkdir()
        shutil.copytree(SOURCE / "scripts", self.target / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        self.output = self.work / "proposal"
        self.env = os.environ.copy()
        self.env.update({"GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_NOSYSTEM": "1",
                         "GIT_CONFIG_GLOBAL": os.devnull,
                         "ASSIMILATION_MATT_SOURCE": str(self.work / "missing-matt"),
                         "ASSIMILATION_PSTACK_SOURCE": str(self.work / "missing-pstack")})

    def propose(self):
        return subprocess.run([sys.executable, str(self.target / "scripts/propose_update.py"),
                               "--output-dir", str(self.output)], cwd=self.target,
                              env=self.env, capture_output=True, text=True)

    def create_sources_and_lock(self):
        records = {}
        self.repositories = {}
        for name, url in (("matt", "https://github.com/mattpocock/skills.git"),
                          ("pstack", "https://github.com/cursor/plugins.git")):
            path = self.work / name
            path.mkdir()
            self.git(path, "init", "--initial-branch=main")
            self.git(path, "config", "user.email", "test@example.invalid")
            self.git(path, "config", "user.name", "Fixture")
            (path / "README.md").write_text("Synthetic source version one\n")
            self.git(path, "add", ".")
            self.git(path, "commit", "-m", "initial")
            records[name] = {"repository": url, "branch": "main", "sha": self.git(path, "rev-parse", "HEAD"),
                             "skills_exposed": 1, "installed_at_utc": "2026-01-01T00:00:00+00:00"}
            self.repositories[name] = path
            self.env[f"ASSIMILATION_{name.upper()}_SOURCE"] = str(path)
        self.lock = self.target / "sources.lock.json"
        self.lock.write_text(json.dumps({"schema": 1, "sources": records}, indent=2) + "\n")
        return records

    def git(self, path, *args):
        return subprocess.run(["git", *args], cwd=path, env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_missing_lock_reports_setup_needed_without_fetch_or_files(self):
        result = self.propose()
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "not-installed")
        self.assertFalse(self.output.exists())
        self.assertFalse((self.target / "sources.lock.json").exists())

    def test_dangling_lock_symlink_is_invalid_not_an_absent_baseline(self):
        lock = self.target / "sources.lock.json"
        try:
            lock.symlink_to(self.work / "missing-lock-target")
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        result = self.propose()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Symlink", result.stderr)
        self.assertTrue(lock.is_symlink())
        self.assertFalse(self.output.exists())

    def test_proposal_freezes_both_sources_and_preserves_the_installed_lock(self):
        records = self.create_sources_and_lock()
        original = self.lock.read_bytes()
        matt = self.repositories["matt"]
        (matt / "README.md").write_text("Synthetic source version two\n")
        self.git(matt, "commit", "-am", "new version")
        next_sha = self.git(matt, "rev-parse", "HEAD")
        result = self.propose()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "updates-available")
        plan = json.loads((self.output / "sources.update.json").read_text())
        self.assertEqual(plan, {"schema": 1, "sources": {
            "matt": {"from_sha": records["matt"]["sha"], "to_sha": next_sha},
            "pstack": {"from_sha": records["pstack"]["sha"], "to_sha": records["pstack"]["sha"]}}})
        body = (self.output / "PULL_REQUEST.md").read_text()
        self.assertIn(f"https://github.com/mattpocock/skills/compare/{records['matt']['sha']}..{next_sha}", body)
        self.assertIn("--approve-update --update-plan", body)
        self.assertEqual(self.lock.read_bytes(), original)
        self.assertFalse((self.target / "vendor").exists())

    def test_current_sources_do_not_create_an_empty_update_proposal(self):
        self.create_sources_and_lock()
        result = self.propose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "current")
        self.assertFalse(self.output.exists())

    def test_invalid_baseline_is_not_presented_as_a_real_update(self):
        records = self.create_sources_and_lock()
        records["matt"]["sha"] = "not-an-installed-commit"
        self.lock.write_text(json.dumps({"schema": 1, "sources": records}))
        original = self.lock.read_bytes()
        result = self.propose()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.lock.read_bytes(), original)

    def test_existing_output_is_not_overwritten(self):
        self.create_sources_and_lock()
        matt = self.repositories["matt"]
        (matt / "README.md").write_text("Synthetic source version two\n")
        self.git(matt, "commit", "-am", "new version")
        self.output.mkdir()
        existing = self.output / "sources.update.json"
        existing.write_text("Keep my prior reviewed proposal\n")
        result = self.propose()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(existing.read_text(), "Keep my prior reviewed proposal\n")

    def test_unavailable_source_does_not_leave_a_partial_proposal(self):
        self.create_sources_and_lock()
        original = self.lock.read_bytes()
        self.env["ASSIMILATION_PSTACK_SOURCE"] = str(self.work / "missing-pstack")
        result = self.propose()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.lock.read_bytes(), original)

    @unittest.skipUnless(shutil.which("bash"), "Bash is required to check the Linux workflow shell")
    def test_monthly_workflow_reports_missing_lock_and_skips_update_handoff(self):
        workflow = (SOURCE / ".github/workflows/monthly-skill-review.yml").read_text()
        script = workflow.split("        run: |\n", 1)[1].split("      - name:", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        outputs = self.work / "github-output"
        summary = self.work / "github-summary"
        self.env.update({"GITHUB_OUTPUT": str(outputs), "GITHUB_STEP_SUMMARY": str(summary),
                         "RUNNER_TEMP": str(self.work)})
        result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], cwd=self.target,
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.read_text(), "changed=false\n")
        self.assertIn("no committed sources.lock.json", summary.read_text())
        self.assertFalse((self.work / "skill-update-proposal").exists())


class MonthlyWorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (SOURCE / ".github/workflows/monthly-skill-review.yml").read_text()

    def test_only_default_branch_proposals_receive_minimal_write_permissions(self):
        permissions = self.workflow.split("permissions:\n", 1)[1].split("concurrency:", 1)[0]
        self.assertEqual(permissions, "  contents: read\n")
        self.assertIn("      contents: write\n      pull-requests: write\n", self.workflow)
        self.assertNotIn("issues: write", self.workflow)
        self.assertIn("github.event.repository.default_branch", self.workflow)
        self.assertIn("'0 9 1 * *'", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)
        self.assertIn("GIT_ALLOW_PROTOCOL: file", self.workflow)
        self.assertIn("scripts/propose_update.py", self.workflow)
        self.assertNotIn("skills.py install", self.workflow)
        self.assertNotIn("git push", self.workflow)
        self.assertIn("scripts/publish_update.py", self.workflow)
        self.assertNotIn("gh pr merge", self.workflow)
        self.assertNotIn("gh pr review", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)

    @unittest.skipUnless(shutil.which("bash"), "Bash is required to check the Linux workflow shell")
    def test_embedded_shell_scripts_are_syntactically_valid(self):
        lines = self.workflow.splitlines()
        scripts = []
        for index, line in enumerate(lines):
            if line.strip() != "run: |":
                continue
            indent = len(line) - len(line.lstrip())
            script = []
            for following in lines[index + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                script.append(following[indent + 2:])
            scripts.append("\n".join(script))
        self.assertEqual(len(scripts), 2)
        for script in scripts:
            result = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class GeneratedStateSafetyTests(unittest.TestCase):
    def test_installer_recovery_state_is_ignored_by_git(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copy2(SOURCE / ".gitignore", root / ".gitignore")
            env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_CONFIG_GLOBAL": os.devnull}
            subprocess.run(["git", "init", "--quiet"], cwd=root, env=env, check=True)
            paths = [".assimilation-stage-fixture/fetch-matt/.git/config",
                     ".assimilation-install.lock/owner", ".agents/.assimilation-stage-fixture/backup-skills/SKILL.md"]
            result = subprocess.run(["git", "check-ignore", "--stdin"], cwd=root, env=env,
                                    input="\n".join(paths) + "\n", text=True, capture_output=True)
            self.assertEqual(result.stdout.splitlines(), paths)


if __name__ == "__main__":
    unittest.main()
