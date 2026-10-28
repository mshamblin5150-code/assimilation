"""CLI/API-boundary publication tests with synthetic Git data and no network access."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == "nt", "The Ubuntu Actions transport fixture requires POSIX executable scripts")
class PublishUpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.target = self.work / "checkout"
        shutil.copytree(SOURCE / "scripts", self.target / "scripts")
        self.proposal = self.work / "proposal"
        self.proposal.mkdir()
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull, "GITHUB_ACTIONS": "true",
                    "GITHUB_EVENT_NAME": "schedule", "GITHUB_REPOSITORY": "fixture/assimilation",
                    "GITHUB_REF": "refs/heads/main", "GH_TOKEN": "synthetic-not-a-credential",
                    "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
                    "FIXTURE_STATE": str(self.work / "api.json")}

    def run_publisher(self):
        command = [sys.executable, str(self.target / "scripts/publish_update.py"), "--proposal-dir", str(self.proposal)]
        if hasattr(self, "plan_digest"):
            command.extend(["--expected-plan-sha256", self.plan_digest])
        return subprocess.run(command, cwd=self.target,
                              env=self.env, text=True, capture_output=True)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.target, env=self.env,
                              text=True, capture_output=True, check=True).stdout.strip()

    def prepare_repository(self):
        sources = {name: {"repository": url, "branch": "main", "sha": sha}
                   for name, url, sha in (("matt", "https://github.com/mattpocock/skills.git", "a" * 40),
                                          ("pstack", "https://github.com/cursor/plugins.git", "b" * 40))}
        self.lock = self.target / "sources.lock.json"
        self.lock.write_text(json.dumps({"schema": 1, "sources": sources}, indent=2) + "\n")
        self.plan = {"schema": 1, "sources": {"matt": {"from_sha": "a" * 40, "to_sha": "c" * 40},
                                               "pstack": {"from_sha": "b" * 40, "to_sha": "b" * 40}}}
        (self.proposal / "sources.update.json").write_text(json.dumps(self.plan, indent=2) + "\n")
        self.plan_digest = hashlib.sha256((self.proposal / "sources.update.json").read_bytes()).hexdigest()
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", ".")
        self.git("commit", "-m", "baseline")
        self.base = self.git("rev-parse", "HEAD")
        self.env["GITHUB_SHA"] = self.base
        self.remote = self.work / "remote"
        self.git("clone", "--quiet", "--bare", str(self.target), str(self.remote))
        self.git("config", "user.name", "Fixture", cwd=self.remote)
        self.git("config", "user.email", "fixture@example.invalid", cwd=self.remote)
        (self.work / "api.json").write_text(json.dumps({"repo": str(self.remote), "calls": [], "pulls": []}))
        transport = self.bin / "gh"
        transport.write_text("#!" + sys.executable + "\n" + (SOURCE / "tests/fixture_gh_api.py").read_text())
        transport.chmod(0o755)

    def state(self):
        return json.loads((self.work / "api.json").read_text())

    def change_state(self, **values):
        state = self.state()
        state.update(values)
        (self.work / "api.json").write_text(json.dumps(state))

    def new_commit(self, parent, name, content, message):
        with tempfile.TemporaryDirectory() as folder:
            env = {**self.env, "GIT_INDEX_FILE": str(Path(folder) / "index")}
            def command(*args, data=None):
                return subprocess.run(["git", *args], cwd=self.remote, env=env, input=data,
                                      text=True, capture_output=True, check=True).stdout.strip()
            command("read-tree", parent)
            blob = command("hash-object", "-w", "--stdin", data=content)
            command("update-index", "--add", "--cacheinfo", "100644," + blob + "," + name)
            tree = command("write-tree")
            return command("commit-tree", tree, "-p", parent, "-m", message)

    def test_publishes_only_frozen_plan_as_a_draft_and_keeps_lock_unchanged(self):
        self.prepare_repository()
        original = self.lock.read_bytes()
        (self.target / "private-extra.txt").write_text("Synthetic local-only material\n")
        (self.proposal / "unrelated.txt").write_text("Synthetic artifact-only material\n")
        result = self.run_publisher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "draft-created")
        pull = self.state()["pulls"][0]
        self.assertTrue(pull["draft"])
        self.assertEqual(pull["base"]["ref"], "main")
        sha = pull["head"]["sha"]
        self.assertEqual(self.git("diff", "--name-only", self.base, sha, cwd=self.remote), "sources.update.json")
        self.assertEqual(json.loads(self.git("show", sha + ":sources.update.json", cwd=self.remote)), self.plan)
        self.assertEqual(self.git("rev-parse", "main", cwd=self.remote), self.base)
        self.assertEqual(self.lock.read_bytes(), original)

    def test_generation_digest_flows_into_publication_without_refetching(self):
        self.prepare_repository()
        self.env.update({"ASSIMILATION_MATT_SOURCE": str(self.remote), "ASSIMILATION_PSTACK_SOURCE": str(self.remote)})
        generated = self.work / "generated"
        result = subprocess.run([sys.executable, str(self.target / "scripts/propose_update.py"),
                                 "--output-dir", str(generated)], cwd=self.target,
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.proposal = generated
        self.plan_digest = json.loads(result.stdout)["plan_sha256"]
        expected = json.loads((generated / "sources.update.json").read_text())
        self.env.update({"ASSIMILATION_MATT_SOURCE": str(self.work / "unavailable"),
                         "ASSIMILATION_PSTACK_SOURCE": str(self.work / "unavailable")})
        published = self.run_publisher()
        self.assertEqual(published.returncode, 0, published.stderr)
        sha = self.state()["pulls"][0]["head"]["sha"]
        self.assertEqual(json.loads(self.git("show", sha + ":sources.update.json", cwd=self.remote)), expected)

    def test_repeated_run_reuses_the_same_draft_without_branch_changes(self):
        self.prepare_repository()
        first = self.run_publisher()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.state()["pulls"][0]
        again = self.run_publisher()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(json.loads(again.stdout)["status"], "draft-reused")
        self.assertEqual(self.state()["pulls"], [before])
        self.assertEqual(self.git("rev-parse", before["head"]["ref"], cwd=self.remote), before["head"]["sha"])

    def test_old_base_proposal_is_reused_without_rewriting_branch_or_new_main_files(self):
        self.prepare_repository()
        self.assertEqual(self.run_publisher().returncode, 0)
        pull = self.state()["pulls"][0]
        moved = self.new_commit(self.base, "README.md", "New unrelated main content\n", "Advance default")
        self.git("update-ref", "refs/heads/main", moved, cwd=self.remote)
        self.git("fetch", str(self.remote), "main")
        self.git("reset", "--hard", "FETCH_HEAD")
        self.env["GITHUB_SHA"] = moved
        result = self.run_publisher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "draft-reused")
        self.assertEqual(self.git("rev-parse", pull["head"]["ref"], cwd=self.remote), pull["head"]["sha"])
        self.assertEqual(self.git("show", "main:README.md", cwd=self.remote), "New unrelated main content")
        self.assertEqual(self.state()["pulls"], [pull])

    def test_retry_recovers_branch_commit_followed_by_pr_failure(self):
        self.prepare_repository()
        self.change_state(fail_pr_before=True)
        failed = self.run_publisher()
        self.assertEqual(failed.returncode, 1, failed.stderr)
        branch = self.git("for-each-ref", "--format=%(refname)", "refs/heads/automation", cwd=self.remote)
        created_sha = self.git("rev-parse", branch, cwd=self.remote)
        self.assertEqual(self.state()["pulls"], [])
        retried = self.run_publisher()
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(self.state()["pulls"][0]["head"]["sha"], created_sha)

    def test_retry_recovers_lost_branch_creation_response(self):
        self.prepare_repository()
        self.change_state(fail_ref_after=True)
        self.assertEqual(self.run_publisher().returncode, 1)
        branch = self.git("for-each-ref", "--format=%(refname)", "refs/heads/automation", cwd=self.remote)
        created_sha = self.git("rev-parse", branch, cwd=self.remote)
        retried = self.run_publisher()
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(self.state()["pulls"][0]["head"]["sha"], created_sha)

    def test_retry_recovers_lost_pr_creation_response_without_duplicate(self):
        self.prepare_repository()
        self.change_state(fail_pr_after=True)
        self.assertEqual(self.run_publisher().returncode, 1)
        before = self.state()["pulls"]
        self.assertEqual(len(before), 1)
        retried = self.run_publisher()
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(self.state()["pulls"], before)

    def test_human_branch_edits_are_never_overwritten(self):
        self.prepare_repository()
        first = self.run_publisher()
        self.assertEqual(first.returncode, 0, first.stderr)
        pull = self.state()["pulls"][0]
        human = self.new_commit(pull["head"]["sha"], "human.txt", "Keep my work\n", "Human edit")
        self.git("update-ref", "refs/heads/" + pull["head"]["ref"], human, cwd=self.remote)
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.git("rev-parse", pull["head"]["ref"], cwd=self.remote), human)
        self.assertEqual(self.git("show", human + ":human.txt", cwd=self.remote), "Keep my work")
        self.assertEqual(self.state()["pulls"], [pull])

    def test_closed_promoted_and_human_owned_prs_need_manual_review(self):
        self.prepare_repository()
        self.assertEqual(self.run_publisher().returncode, 0)
        original = self.state()["pulls"][0]
        for change in ({"state": "closed"}, {"draft": False}, {"user": {"login": "human"}}):
            with self.subTest(change=change):
                changed = {**original, **change}
                self.change_state(pulls=[changed])
                result = self.run_publisher()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.state()["pulls"], [changed])

    def test_human_title_or_body_edits_stop_reuse_without_changing_their_text(self):
        self.prepare_repository()
        first = self.run_publisher()
        self.assertEqual(first.returncode, 0, first.stderr)
        original = self.state()["pulls"][0]
        writes = [call for call in self.state()["calls"] if call["method"] != "GET"]
        for change in ({"body": "Human review notes: preserve these decisions."},
                       {"title": "Human title: hold for compatibility review"}):
            with self.subTest(change=change):
                changed = {**original, **change}
                self.change_state(pulls=[changed])
                result = self.run_publisher()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.state()["pulls"], [changed])
                self.assertEqual([call for call in self.state()["calls"] if call["method"] != "GET"], writes)

    def test_default_branch_change_before_create_ref_stops_publication(self):
        self.prepare_repository()
        moved = self.new_commit(self.base, "README.md", "New default branch content\n", "Advance default")
        self.change_state(move_default_on_read=2, replacement_base=moved)
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.git("for-each-ref", "--format=%(refname)", "refs/heads", cwd=self.remote), "refs/heads/main")
        self.assertEqual(self.state()["pulls"], [])

    def test_stale_local_lock_fails_before_branch_creation(self):
        self.prepare_repository()
        lock = json.loads(self.lock.read_text())
        lock["sources"]["matt"]["sha"] = "d" * 40
        self.lock.write_text(json.dumps(lock))
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.state()["calls"], [])

    def test_committed_lock_link_cannot_be_hidden_by_a_dirty_regular_copy(self):
        self.prepare_repository()
        original = self.lock.read_bytes()
        self.lock.rename(self.target / "lock-target.json")
        self.lock.symlink_to("lock-target.json")
        self.git("add", ".")
        self.git("commit", "-m", "Replace baseline with a link")
        self.base = self.git("rev-parse", "HEAD")
        self.env["GITHUB_SHA"] = self.base
        self.git("push", str(self.remote), "HEAD:main")
        self.lock.unlink()
        self.lock.write_bytes(original)
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.state()["calls"], [])
        self.assertEqual(self.state()["pulls"], [])

    def test_changed_artifact_cannot_publish_an_unchecked_target(self):
        self.prepare_repository()
        self.plan["sources"]["matt"]["to_sha"] = "e" * 40
        (self.proposal / "sources.update.json").write_text(json.dumps(self.plan))
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.state()["calls"], [])

    def test_default_branch_race_after_pr_creation_is_reported_not_success(self):
        self.prepare_repository()
        moved = self.new_commit(self.base, "README.md", "New default branch content\n", "Advance default")
        self.change_state(move_default_on_read=4, replacement_base=moved)
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(self.state()["pulls"]), 1)
        self.assertTrue(self.state()["pulls"][0]["draft"])

    def test_untrusted_event_and_nondefault_ref_cannot_publish(self):
        self.prepare_repository()
        for values in ({"GITHUB_EVENT_NAME": "pull_request"},
                       {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/feature"}):
            with self.subTest(values=values):
                self.env.update(values)
                result = self.run_publisher()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn(self.env["GH_TOKEN"], result.stderr)
                self.assertEqual(self.state()["pulls"], [])
                self.assertEqual(self.git("for-each-ref", "--format=%(refname)", "refs/heads", cwd=self.remote), "refs/heads/main")

    def test_missing_lock_is_setup_needed_without_api_or_branch(self):
        result = self.run_publisher()
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "not-installed")
        self.assertFalse((self.work / "api.json").exists())


if __name__ == "__main__":
    unittest.main()
