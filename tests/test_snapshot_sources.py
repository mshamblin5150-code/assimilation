"""Offline public-CLI snapshot tests; synthetic Git repositories, no network."""
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
# Public MIT license texts are fixtures, not generated from code under test.
MIT = '''MIT License

Copyright (c) 2026 {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "assimilation"
        self.root.mkdir()
        shutil.copytree(SOURCE / "scripts", self.root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        self.env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull}
        self.repos = {}
        for name, author in (("matt", "Matt Pocock"), ("pstack", "Lauren Tan")):
            repo = self.work / name
            repo.mkdir()
            self.git(repo, "init", "--initial-branch=main")
            self.git(repo, "config", "user.email", "fixture@example.invalid")
            self.git(repo, "config", "user.name", "Synthetic Fixture")
            scope = repo if name == "matt" else repo / "pstack"
            scope.mkdir(exist_ok=True)
            (scope / "LICENSE").write_text(MIT.format(author=author))
            (scope / "skills/example").mkdir(parents=True)
            (scope / "skills/example/SKILL.md").write_text("Full original skill text\n")
            (scope / "dormant").mkdir()
            script = scope / "dormant/tool.sh"
            script.write_text("#!/bin/sh\nprintf forbidden > EXECUTED\n")
            script.chmod(0o755)
            (scope / "asset.bin").write_bytes(b"\x00\xff\r\n\x80binary\x00")
            if name == "matt":
                (scope / "CLAUDE.md").write_text("Original source instructions\n")
                (scope / "AGENTS.md").symlink_to("CLAUDE.md")
                (scope / ".github/workflows").mkdir(parents=True)
                (scope / ".github/workflows/dormant.yml").write_text("name: Dormant source data\n")
            else:
                (repo / "other-plugin").mkdir()
                (repo / "other-plugin/private-to-scope.txt").write_text("Outside the selected public subtree\n")
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-m", "synthetic initial source")
            self.repos[name] = repo
            self.env[f"ASSIMILATION_{name.upper()}_SOURCE"] = str(repo)
        self.write_lock()

    def git(self, root, *args):
        return subprocess.run(["git", *args], cwd=root, env=self.env, capture_output=True,
                              text=True, check=True).stdout.strip()

    def write_lock(self):
        urls = {"matt": "https://github.com/mattpocock/skills.git", "pstack": "https://github.com/cursor/plugins.git"}
        data = {"schema": 1, "sources": {name: {"repository": urls[name], "branch": "main",
                "sha": self.git(repo, "rev-parse", "HEAD")} for name, repo in self.repos.items()}}
        (self.root / "sources.lock.json").write_text(json.dumps(data, indent=2) + "\n")
        return data

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(self.root / "scripts/snapshot_sources.py"), *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def state(self):
        result = {}
        for rel in ("upstream", "sources.lock.json", "sources.snapshot.json"):
            path = self.root / rel
            if path.exists():
                for item in ([path, *path.rglob("*")] if path.is_dir() else [path]):
                    result[str(item.relative_to(self.root))] = (("link", os.readlink(item)) if item.is_symlink()
                        else ("dir", stat.S_IMODE(item.stat().st_mode)) if item.is_dir()
                        else ("file", stat.S_IMODE(item.stat().st_mode), item.read_bytes()))
        return result

    def run_fault(self, fault, approved=True):
        launcher = r"""
import errno, os, pathlib, runpy, sys
root = pathlib.Path(sys.argv[1])
faults = set(sys.argv[2].split('+'))
approved = sys.argv[3] == 'yes'
original_rename, original_replace = os.rename, os.replace
fired = set()
targets = {'matt': root / 'upstream/matt-pocock', 'pstack': root / 'upstream/pstack',
           'manifest': root / 'sources.snapshot.json'}
def operation(original, src, dst, *args, **kwargs):
    src, dst = pathlib.Path(src), pathlib.Path(dst)
    action = None
    for name, target in targets.items():
        if src == target and dst.name.startswith('backup-'):
            action = 'backup-' + name
        elif dst == target and src.name.startswith('backup-'):
            action = 'restore-' + name
        elif dst == target:
            action = 'install-' + name
        elif src == target:
            action = 'remove-' + name
    if 'device-boundaries' in faults:
        def device(path):
            return 'upstream' if path.is_relative_to(root / 'upstream') else 'root'
        if device(src.parent) != device(dst.parent):
            raise OSError(errno.EXDEV, 'simulated independent destination filesystems')
    if ('after-' + str(action)) in faults and action not in fired:
        fired.add(action)
        original(src, dst, *args, **kwargs)
        raise KeyboardInterrupt('injected after-' + action + ' failure')
    if action in faults and action not in fired:
        fired.add(action)
        raise OSError('injected ' + action + ' failure')
    return original(src, dst, *args, **kwargs)
os.rename = lambda src, dst, *args, **kwargs: operation(original_rename, src, dst, *args, **kwargs)
os.replace = lambda src, dst, *args, **kwargs: operation(original_replace, src, dst, *args, **kwargs)
sys.path.insert(0, str(root / 'scripts'))
sys.argv = [str(root / 'scripts/snapshot_sources.py'), 'refresh'] + (['--approve-update'] if approved else [])
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        return subprocess.run([sys.executable, "-c", launcher, str(self.root), fault, "yes" if approved else "no"],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def test_snapshot_staging_supports_independent_target_filesystems(self):
        result = self.run_fault("device-boundaries", approved=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_tool("verify").returncode, 0)

    def test_full_exact_snapshot_and_offline_verification(self):
        lock = (self.root / "sources.lock.json").read_bytes()
        result = self.run_tool("refresh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "sources.lock.json").read_bytes(), lock)
        matt, pstack = self.root / "upstream/matt-pocock", self.root / "upstream/pstack"
        self.assertEqual((matt / "asset.bin").read_bytes(), b"\x00\xff\r\n\x80binary\x00")
        self.assertEqual((pstack / "skills/example/SKILL.md").read_text(), "Full original skill text\n")
        self.assertEqual(os.readlink(matt / "AGENTS.md"), "CLAUDE.md")
        self.assertEqual(stat.S_IMODE((matt / "dormant/tool.sh").stat().st_mode), 0o755)
        self.assertTrue((matt / ".github/workflows/dormant.yml").is_file())
        self.assertFalse((pstack / "other-plugin").exists())
        self.assertFalse(list((self.root / "upstream").rglob(".git")))
        self.assertFalse(list(self.work.rglob("EXECUTED")))
        for name in self.repos:
            self.env[f"ASSIMILATION_{name.upper()}_SOURCE"] = str(self.work / "missing")
        verified = self.run_tool("verify")
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["status"], "verified")

    def test_changed_lock_is_not_silently_treated_as_owned_baseline(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        (self.repos["matt"] / "new.txt").write_text("New upstream content\n")
        self.git(self.repos["matt"], "add", ".")
        self.git(self.repos["matt"], "commit", "-m", "new revision")
        self.write_lock()
        before = self.state()
        result = self.run_tool("refresh", "--approve-update")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("mismatch", result.stderr)
        self.assertEqual(self.state(), before)

    def test_high_confidence_credential_material_is_not_copied(self):
        path = self.repos["matt"] / "leaked.txt"
        for raw in (b"ghp_" + b"A" * 36, b"-----BEGIN OPENSSH PRIVATE KEY-----\nfixture\n"):
            with self.subTest(kind=raw[:8]):
                path.write_bytes(raw)
                self.git(self.repos["matt"], "add", ".")
                self.git(self.repos["matt"], "commit", "-m", "credential-shaped fixture")
                self.write_lock()
                before = self.state()
                result = self.run_tool("refresh")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("leaked.txt", result.stderr)
                self.assertNotIn(raw.decode().strip(), result.stderr)
                self.assertEqual(self.state(), before)

    def plan_after_change(self):
        old = json.loads((self.root / "sources.lock.json").read_text())["sources"]
        changed = self.repos["matt"] / "new-root-file.txt"
        changed.write_text("Reviewed next source\n")
        self.git(self.repos["matt"], "add", ".")
        self.git(self.repos["matt"], "commit", "--allow-empty", "-m", "reviewed proposed version")
        plan = {"schema": 1, "sources": {name: {"from_sha": entry["sha"],
                "to_sha": self.git(self.repos[name], "rev-parse", "HEAD")} for name, entry in old.items()}}
        path = self.root / "sources.update.json"
        path.write_text(json.dumps(plan))
        return path, plan

    def test_prepare_freezes_complete_proposed_package_without_changing_baseline(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        plan_path, plan = self.plan_after_change()
        # A later upstream commit is not part of this reviewed proposal.
        (self.repos["matt"] / "new-root-file.txt").write_text("Later unreviewed version\n")
        self.git(self.repos["matt"], "add", ".")
        self.git(self.repos["matt"], "commit", "-m", "later main")
        before = self.state()
        output = self.root / "proposal"
        result = self.run_tool("prepare", "--update-plan", str(plan_path), "--output-dir", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state(), before)
        self.assertEqual((output / "upstream/matt-pocock/new-root-file.txt").read_text(), "Reviewed next source\n")
        proposed_lock = json.loads((output / "sources.lock.json").read_bytes())
        self.assertEqual(set(proposed_lock), {"schema", "sources"})
        for name, entry in proposed_lock["sources"].items():
            self.assertEqual(set(entry), {"repository", "branch", "sha"})
            self.assertEqual(entry["sha"], plan["sources"][name]["to_sha"])
        (output / "sources.update.json").write_text(json.dumps(plan))
        (output / "PULL_REQUEST.md").write_text("Review only, not approval\n")
        self.env["ASSIMILATION_MATT_SOURCE"] = str(self.work / "unavailable")
        self.assertEqual(self.run_tool("verify", "--root", str(output)).returncode, 0)

    def test_repeat_refresh_is_deterministic_and_keeps_unowned_siblings(self):
        sibling = self.root / "upstream/README.md"
        sibling.parent.mkdir()
        sibling.write_text("User-owned navigation\n")
        other = self.root / "upstream/unrelated"
        other.mkdir()
        (other / "keep.bin").write_bytes(b"\x00unchanged")
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        before = self.state()
        denied = self.run_tool("refresh")
        self.assertEqual(denied.returncode, 1)
        self.assertEqual(self.state(), before)
        repeated = self.run_tool("refresh", "--approve-update")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.state(), before)

    def test_edited_missing_and_added_owned_entries_are_preserved_on_refusal(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        root = self.root / "upstream/matt-pocock"
        cases = [("asset.bin", "edit"), ("skills/example/SKILL.md", "delete"), ("unknown.txt", "add"),
                 ("dormant/tool.sh", "mode"), ("AGENTS.md", "link")]
        for rel, action in cases:
            with self.subTest(action=action):
                path = root / rel
                raw = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.exists() else None
                mode = path.lstat().st_mode if path.exists() else None
                if action == "delete":
                    path.unlink()
                elif action == "mode":
                    path.chmod(0o644)
                elif action == "link":
                    path.unlink()
                    path.symlink_to("./CLAUDE.md")
                else:
                    path.write_bytes(b"User edit must remain\n")
                before = self.state()
                result = self.run_tool("refresh", "--approve-update")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.state(), before)
                if path.exists() or path.is_symlink():
                    path.unlink()
                if action == "link":
                    path.symlink_to(raw)
                elif raw is not None:
                    path.write_bytes(raw)
                    path.chmod(stat.S_IMODE(mode))

    def test_manifest_commit_tree_and_blob_metadata_tampering_is_rejected_offline(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        path = self.root / "sources.snapshot.json"
        original = path.read_bytes()
        for mutation in ("commit", "tree", "blob", "size", "scope", "directory"):
            with self.subTest(mutation=mutation):
                manifest = json.loads(original)
                source = manifest["sources"]["matt"]
                if mutation == "commit":
                    source["commit_object"] = base64.b64encode(b"forged commit").decode()
                elif mutation == "tree":
                    source["root_tree_object"] = base64.b64encode(b"forged tree").decode()
                elif mutation == "blob":
                    source["files"]["asset.bin"]["git_blob_sha"] = "0" * 40
                elif mutation == "size":
                    source["files"]["asset.bin"]["size"] += 1
                elif mutation == "scope":
                    source["scope"] = "skills"
                else:
                    source["directory"] = "../outside"
                path.write_text(json.dumps(manifest))
                before = self.state()
                self.assertEqual(self.run_tool("verify").returncode, 1)
                self.assertEqual(self.run_tool("refresh", "--approve-update").returncode, 1)
                self.assertEqual(self.state(), before)
        path.write_bytes(original)

    def test_license_changes_and_new_nested_terms_fail_closed(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        original_license = (self.repos["matt"] / "LICENSE").read_bytes()
        for case in ("changed", "nested"):
            with self.subTest(case=case):
                path, plan = self.plan_after_change()
                if case == "changed":
                    (self.repos["matt"] / "LICENSE").write_text("All rights reserved.\n")
                else:
                    (self.repos["matt"] / "LICENSE").write_bytes(original_license)
                    (self.repos["matt"] / "dormant/LICENSE.txt").write_text("Unexpected nested license\n")
                self.git(self.repos["matt"], "add", ".")
                self.git(self.repos["matt"], "commit", "-m", "changed license")
                plan["sources"]["matt"]["to_sha"] = self.git(self.repos["matt"], "rev-parse", "HEAD")
                path.write_text(json.dumps(plan))
                before = self.state()
                output = self.root / "proposal"
                result = self.run_tool("prepare", "--update-plan", str(path), "--output-dir", str(output))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("license", result.stderr)
                self.assertFalse(output.exists())
                self.assertEqual(self.state(), before)

    def test_changed_manifest_or_lock_modes_are_not_silently_reset(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        for name in ("sources.snapshot.json", "sources.lock.json"):
            with self.subTest(name=name):
                path = self.root / name
                path.chmod(0o755)
                before = self.state()
                self.assertEqual(self.run_tool("verify").returncode, 1)
                self.assertEqual(self.run_tool("refresh", "--approve-update").returncode, 1)
                self.assertEqual(self.state(), before)
                path.chmod(0o644)

    def test_every_backup_install_and_completed_move_failure_preserves_originals(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        before = self.state()
        faults = [prefix + name for prefix in ("backup-", "install-", "after-backup-", "after-install-")
                  for name in ("matt", "pstack", "manifest")]
        for fault in faults:
            with self.subTest(fault=fault):
                result = self.run_fault(fault)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(fault, result.stderr)
                self.assertEqual(self.state(), before)
                self.assertFalse(list(self.root.rglob(".assimilation-snapshot-stage-*")))

    def test_initial_install_failures_leave_no_published_or_temporary_sources(self):
        before = self.state()
        for fault in ("install-matt", "install-pstack", "install-manifest", "after-install-matt", "after-install-manifest"):
            with self.subTest(fault=fault):
                result = self.run_fault(fault, approved=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.state(), before)
                self.assertFalse((self.root / "upstream").exists())
                self.assertFalse(list(self.root.glob(".assimilation-*")))

    def test_restore_failure_retains_original_backup_and_refuses_retry(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        original = (self.root / "upstream/matt-pocock/asset.bin").read_bytes()
        failed = self.run_fault("install-manifest+restore-matt")
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn("rollback incomplete", failed.stderr)
        backups = list((self.root / "upstream").glob(".assimilation-snapshot-stage-*/backup-matt"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "asset.bin").read_bytes(), original)
        self.assertEqual(os.readlink(backups[0] / "AGENTS.md"), "CLAUDE.md")
        retry = self.run_tool("refresh", "--approve-update")
        self.assertEqual(retry.returncode, 1)
        self.assertIn("Retained snapshot", retry.stderr)
        self.assertTrue(backups[0].is_dir())

    def test_shared_installer_guard_blocks_snapshots(self):
        guard = self.root / ".assimilation-install.lock"
        guard.mkdir()
        before = self.state()
        result = self.run_tool("refresh")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("shared guard", result.stderr)
        self.assertEqual(self.state(), before)
        self.assertTrue(guard.is_dir())

    def test_existing_unowned_source_tree_is_never_adopted_or_deleted(self):
        path = self.root / "upstream/matt-pocock/keep.txt"
        path.parent.mkdir(parents=True)
        path.write_text("User-owned source copy\n")
        before = self.state()
        result = self.run_tool("refresh", "--approve-update")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("ownership manifest", result.stderr)
        self.assertEqual(self.state(), before)

    def test_stale_malformed_or_existing_output_plan_is_rejected(self):
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        path, plan = self.plan_after_change()
        original = path.read_bytes()
        for value in ([], {"schema": 1, "sources": {}},
                      {"schema": 1, "sources": {**plan["sources"], "matt": {"from_sha": "0" * 40, "to_sha": "1" * 40}}}):
            with self.subTest(plan=value):
                path.write_text(json.dumps(value))
                before = self.state()
                result = self.run_tool("prepare", "--update-plan", str(path), "--output-dir", str(self.root / "proposal"))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.state(), before)
                self.assertFalse((self.root / "proposal").exists())
        path.write_bytes(original)
        existing = self.root / "proposal"
        existing.mkdir()
        (existing / "keep.txt").write_text("Existing output\n")
        result = self.run_tool("prepare", "--update-plan", str(path), "--output-dir", str(existing))
        self.assertEqual(result.returncode, 1)
        self.assertEqual((existing / "keep.txt").read_text(), "Existing output\n")

    def test_destination_and_output_symlinks_cannot_reach_external_data(self):
        outside = self.work / "outside"
        outside.mkdir()
        canary = outside / "keep.txt"
        canary.write_text("External content\n")
        (self.root / "upstream").symlink_to(outside, target_is_directory=True)
        refused = self.run_tool("refresh")
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertEqual(list(outside.iterdir()), [canary])
        (self.root / "upstream").unlink()
        self.assertEqual(self.run_tool("refresh").returncode, 0)
        path, _ = self.plan_after_change()
        (self.root / "output-link").symlink_to(outside, target_is_directory=True)
        refused = self.run_tool("prepare", "--update-plan", str(path), "--output-dir", str(self.root / "output-link/proposal"))
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(list(outside.iterdir()), [canary])
        self.assertEqual(canary.read_text(), "External content\n")

    def test_oversized_blob_and_aggregate_snapshot_fail_before_materialization(self):
        repo = self.repos["matt"]
        large = repo / "large.bin"
        large.write_bytes(b"0" * (16 * 1024 * 1024 + 1))
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "oversized blob")
        self.write_lock()
        before = self.state()
        result = self.run_tool("refresh")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("size", result.stderr)
        self.assertEqual(self.state(), before)
        large.write_bytes(b"0" * (16 * 1024 * 1024))
        self.git(repo, "add", ".")
        oid = self.git(repo, "hash-object", "large.bin")
        for index in range(8):
            self.git(repo, "update-index", "--add", "--cacheinfo", "100644", oid, f"large-copy-{index}.bin")
        self.git(repo, "commit", "-m", "oversized aggregate")
        self.write_lock()
        before = self.state()
        result = self.run_tool("refresh")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("aggregate", result.stderr)
        self.assertEqual(self.state(), before)

    def test_windows_superscript_device_names_fail_closed(self):
        repo = self.repos["matt"]
        for name in ("COM¹.txt", "LPT².md", "com³", "lpt¹.log"):
            with self.subTest(name=name):
                path = repo / name
                path.write_text("Portable path counterexample\n")
                self.git(repo, "add", ".")
                self.git(repo, "commit", "-m", "reserved Windows alias")
                self.write_lock()
                before = self.state()
                result = self.run_tool("refresh")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("Unsafe source path", result.stderr)
                self.assertEqual(self.state(), before)
                path.unlink()

    def test_git_config_cannot_redirect_fetch_to_an_external_helper(self):
        marker = self.work / "helper-executed"
        helper = self.work / "malicious-helper"
        helper.write_text("#!/bin/sh\nprintf executed > " + str(marker) + "\nexit 1\n")
        helper.chmod(0o755)
        config = self.work / "hostile.gitconfig"
        self.git(self.work, "config", "--file", str(config),
                 "url.ext::" + str(helper) + ".insteadOf", str(self.repos["matt"]))
        self.env["GIT_CONFIG_GLOBAL"] = str(config)
        self.env["GIT_ALLOW_PROTOCOL"] = "file:ext"
        result = self.run_tool("refresh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual(self.run_tool("verify").returncode, 0)

        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_COUNT"] = "1"
        self.env["GIT_CONFIG_KEY_0"] = "url.ext::" + str(helper) + ".insteadOf"
        self.env["GIT_CONFIG_VALUE_0"] = str(self.repos["matt"])
        redirected = self.work / "redirected-git-directory"
        self.env["GIT_DIR"] = str(redirected)
        result = self.run_tool("refresh", "--approve-update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse(redirected.exists())

    def test_commit_provenance_cannot_publish_credential_shaped_metadata(self):
        secret = "ghp_" + "B" * 36
        self.git(self.repos["matt"], "commit", "--allow-empty", "-m", "Metadata contains " + secret)
        self.write_lock()
        before = self.state()
        result = self.run_tool("refresh")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("commit provenance", result.stderr)
        self.assertNotIn(secret, result.stderr)
        self.assertEqual(self.state(), before)


if __name__ == "__main__":
    unittest.main()
