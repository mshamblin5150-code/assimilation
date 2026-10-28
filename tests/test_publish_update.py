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

from source_fixture import make_sources, snapshot_at, advance_matt

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
        if hasattr(self, "package_digest"):
            command.extend(["--expected-package-sha256", self.package_digest])
        return subprocess.run(command, cwd=self.target,
                              env=self.env, text=True, capture_output=True)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.target, env=self.env,
                              text=True, capture_output=True, check=True).stdout.strip()

    def prepare_repository(self, pin_only=False):
        self.repositories = make_sources(self.work, self.env)
        sources = snapshot_at(self.target, self.repositories, self.env)
        self.lock = self.target / "sources.lock.json"
        (self.target / "upstream/README.md").write_text("Keep Assimilation's source index\n")
        (self.target / ".github/workflows").mkdir(parents=True)
        (self.target / ".github/workflows/owned.yml").write_text("name: Keep root workflow unchanged\n")
        if pin_only:
            self.git("commit", "--allow-empty", "-m", "repository-only update", cwd=self.repositories["pstack"])
        else:
            advance_matt(self.repositories["matt"], self.env)
        proposed = snapshot_at(self.proposal, self.repositories, self.env)
        self.plan = {"schema": 1, "sources": {name: {"from_sha": sources[name]["sha"], "to_sha": proposed[name]["sha"]}
                                              for name in sources}}
        (self.proposal / "sources.update.json").write_text(json.dumps(self.plan, sort_keys=True, indent=2) + "\n")
        inventory = {}
        for path in self.proposal.rglob("*"):
            if path.is_dir():
                continue
            raw = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
            mode = "120000" if path.is_symlink() else "100755" if path.stat().st_mode & 0o111 else "100644"
            inventory[path.relative_to(self.proposal).as_posix()] = {"mode": mode, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        self.package_digest = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
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

    def test_api_error_reports_status_and_tree_size_without_service_payload(self):
        self.prepare_repository()
        secret = "synthetic-private-response-do-not-log"
        self.change_state(fail_tree_message=secret + " https://private.invalid/account (HTTP 422)")
        result = self.run_publisher()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP 422", result.stderr)
        self.assertIn("tree entries=", result.stderr)
        self.assertNotIn(secret, result.stderr + result.stdout)
        self.assertNotIn("private.invalid", result.stderr + result.stdout)
        self.assertEqual(self.state()["pulls"], [])

    def test_pin_only_update_reuses_scoped_trees_and_publishes_matching_metadata(self):
        self.prepare_repository(pin_only=True)
        self.change_state(reject_empty_tree=True)
        result = self.run_publisher()
        self.assertEqual(result.returncode, 0, result.stderr)
        pull = self.state()["pulls"][0]
        sha = pull["head"]["sha"]
        changed = self.git("diff", "--name-only", self.base, sha, cwd=self.remote).splitlines()
        self.assertEqual(changed, ["sources.lock.json", "sources.snapshot.json", "sources.update.json"])
        self.assertEqual(self.git("rev-parse", self.base + ":upstream", cwd=self.remote),
                         self.git("rev-parse", sha + ":upstream", cwd=self.remote))
        tree_calls = [call for call in self.state()["calls"] if call["method"] == "POST" and call["path"].endswith("/git/trees")]
        self.assertEqual(len(tree_calls), 1)
        self.assertTrue(pull["draft"])
        repeat = self.run_publisher()
        self.assertEqual(repeat.returncode, 0, repeat.stderr)
        self.assertEqual(json.loads(repeat.stdout)["status"], "draft-reused")
        self.assertEqual(len(self.state()["pulls"]), 1)

    def test_publishes_complete_snapshot_atomically_and_keeps_local_baseline_unchanged(self):
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
        changed = self.git("diff", "--name-only", self.base, sha, cwd=self.remote).splitlines()
        self.assertIn("sources.snapshot.json", changed)
        self.assertIn("sources.lock.json", changed)
        self.assertIn("upstream/matt-pocock/binary.dat", changed)
        self.assertIn("upstream/matt-pocock/obsolete.txt", changed)
        self.assertTrue(all(path in {"sources.lock.json", "sources.snapshot.json", "sources.update.json"}
                            or path.startswith(("upstream/matt-pocock/", "upstream/pstack/")) for path in changed))
        snapshot = json.loads((self.proposal / "sources.snapshot.json").read_text())
        for name, entry in snapshot["sources"].items():
            self.assertEqual(self.git("rev-parse", sha + ":" + entry["directory"], cwd=self.remote), entry["scope_tree_sha"])
        binary = subprocess.run(["git", "show", sha + ":upstream/matt-pocock/binary.dat"],
                                cwd=self.remote, env=self.env, capture_output=True, check=True).stdout
        self.assertEqual(binary, b"\x00\xff\xfe\x01source-binary\n")
        self.assertTrue(self.git("ls-tree", sha, "--", "upstream/matt-pocock/README-link", cwd=self.remote).startswith("120000 blob "))
        self.assertTrue(self.git("ls-tree", sha, "--", "upstream/matt-pocock/run.sh", cwd=self.remote).startswith("100755 blob "))
        self.assertEqual(self.git("show", sha + ":upstream/README.md", cwd=self.remote), "Keep Assimilation's source index")
        self.assertEqual(self.git("show", sha + ":.github/workflows/owned.yml", cwd=self.remote), "name: Keep root workflow unchanged")
        self.assertEqual(json.loads(self.git("show", sha + ":sources.update.json", cwd=self.remote)), self.plan)
        self.assertEqual(self.git("rev-parse", "main", cwd=self.remote), self.base)
        self.assertEqual(self.lock.read_bytes(), original)

    def test_generation_digest_flows_into_publication_without_refetching(self):
        self.prepare_repository()
        generated = self.work / "generated"
        result = subprocess.run([sys.executable, str(self.target / "scripts/propose_update.py"),
                                 "--output-dir", str(generated)], cwd=self.target,
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.proposal = generated
        self.package_digest = json.loads(result.stdout)["package_sha256"]
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

    def test_complete_package_drift_in_source_modes_or_metadata_stops_before_api(self):
        self.prepare_repository()
        mutations = [
            ("upstream/matt-pocock/binary.dat", b"changed binary bytes", None),
            ("upstream/matt-pocock/run.sh", None, 0o644),
            ("sources.snapshot.json", b" ", None),
            ("sources.lock.json", b" ", None),
            ("sources.update.json", None, 0o755),
        ]
        for relative, append, mode in mutations:
            with self.subTest(path=relative):
                path = self.proposal / relative
                original, original_mode = path.read_bytes(), path.stat().st_mode & 0o777
                if append is not None:
                    path.write_bytes(original + append)
                if mode is not None:
                    path.chmod(mode)
                result = self.run_publisher()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.state()["calls"], [])
                path.write_bytes(original)
                path.chmod(original_mode)

    def test_dirty_baseline_snapshot_and_untracked_plan_are_never_adopted(self):
        self.prepare_repository()
        for name, content in (("upstream/matt-pocock/README.md", "Human source edits\n"),
                              ("sources.snapshot.json", "{}\n"),
                              ("sources.update.json", "Human review plan\n")):
            with self.subTest(path=name):
                path = self.target / name
                original = path.read_bytes() if path.exists() else None
                path.write_text(content)
                result = self.run_publisher()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.state()["calls"], [])
                self.assertEqual(path.read_text(), content)
                path.write_bytes(original) if original is not None else path.unlink()

    def test_same_shape_forged_proposal_cannot_modify_unrelated_upstream_siblings(self):
        self.prepare_repository()
        first = self.run_publisher()
        self.assertEqual(first.returncode, 0, first.stderr)
        pull = self.state()["pulls"][0]
        message = self.git("show", "-s", "--format=%B", pull["head"]["sha"], cwd=self.remote)
        changed = self.new_commit(pull["head"]["sha"], "upstream/README.md", "Human sibling content\n", message)
        tree = self.git("show", "-s", "--format=%T", changed, cwd=self.remote)
        forged = self.git("commit-tree", tree, "-p", self.base, "-m", message, cwd=self.remote)
        self.git("update-ref", "refs/heads/" + pull["head"]["ref"], forged, cwd=self.remote)
        result = self.run_publisher()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.git("rev-parse", pull["head"]["ref"], cwd=self.remote), forged)
        self.assertEqual(self.git("show", forged + ":upstream/README.md", cwd=self.remote), "Human sibling content")
        self.assertEqual(self.state()["pulls"], [pull])

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
