"""Offline integration tests for the source installer with local fake upstream git repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


def git(folder, *args):
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    return subprocess.run(["git", *args], cwd=folder, env=env, capture_output=True, text=True, check=True).stdout.strip()


def fixture(root, name, data):
    p = root / name
    p.mkdir()
    git(p, "init", "--initial-branch=main")
    git(p, "config", "user.email", "test@example.invalid")
    git(p, "config", "user.name", "Fixture")
    for rel, content in data.items():
        f = p / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    git(p, "add", ".")
    git(p, "commit", "-m", "initial")
    return p


class SkillInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.target = self.work / "assimilation"
        shutil.copytree(SOURCE, self.target, ignore=shutil.ignore_patterns("vendor", ".agents", ".git", "sources.lock.json", ".assimilation-*", "__pycache__"))
        self.matt = fixture(self.work, "matt", {
            "skills/engineering/grill-with-docs/SKILL.md": "---\nname: grill-with-docs\n---\nOriginal Matt source\n",
            "skills/engineering/wayfinder/SKILL.md": "---\nname: wayfinder\n---\nOriginal Wayfinder\n",
            "skills/productivity/grill-me/SKILL.md": "---\nname: grill-me\n---\nOriginal productivity\n",
            "docs/engineering/wayfinder.md": "Full Wayfinder docs\n",
            "LICENSE": "MIT fixture Matt\n",
        })
        self.pstack = fixture(self.work, "pstack", {
            "pstack/skills/how/SKILL.md": "---\nname: how\n---\nOriginal PStack\n",
            "pstack/skills/why/SKILL.md": "---\nname: why\n---\nOriginal PStack why\n",
            "pstack/agents/architect.md": "Architect support\n",
            "pstack/LICENSE": "MIT fixture PStack\n",
        })
        self.env = os.environ.copy()
        self.env["GIT_ALLOW_PROTOCOL"] = "file"
        self.env["GIT_CONFIG_NOSYSTEM"] = "1"
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["ASSIMILATION_MATT_SOURCE"] = str(self.matt)
        self.env["ASSIMILATION_PSTACK_SOURCE"] = str(self.pstack)

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(self.target / "scripts/skills.py"), *args],
                              cwd=self.target, env=self.env, capture_output=True, text=True)

    def snapshot(self):
        result = {}
        for name in ("vendor", ".agents/skills", "sources.lock.json"):
            root = self.target / name
            if root.exists():
                paths = [root, *root.rglob("*")] if root.is_dir() else [root]
                for path in paths:
                    result[str(path.relative_to(self.target))] = (
                        "directory" if path.is_dir() else path.read_bytes())
        return result

    def run_fault(self, fault):
        launcher = r"""
import errno, os, pathlib, runpy, sys
root = pathlib.Path(sys.argv[1])
faults = set(sys.argv[2].split('+'))
original_rename, original_replace = os.rename, os.replace
fired = set()
targets = {'vendor': root / 'vendor', 'skills': root / '.agents/skills', 'lock': root / 'sources.lock.json'}
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
            if not path.is_relative_to(root):
                return 'system-temp'
            return 'agents-mount' if path.is_relative_to(root / '.agents') else 'project-mount'
        if device(src.parent) != device(dst.parent):
            raise OSError(errno.EXDEV, 'simulated independent filesystems')
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
sys.argv = [str(root / 'scripts/skills.py'), 'install', '--approve-update']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        return subprocess.run([sys.executable, "-c", launcher, str(self.target), fault],
                              cwd=self.target, env=self.env, capture_output=True, text=True)

    def test_backup_failure_preserves_both_originals(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        result = self.run_fault("backup-vendor")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("injected backup-vendor failure", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_full_install_readonly_check_and_controlled_update(self):
        first = self.run_tool("install")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("2 Matt engineering and 2 P-Stack", first.stdout)
        self.assertTrue((self.target / ".agents/skills/matt-wayfinder/SKILL.md").is_file())
        self.assertTrue((self.target / ".agents/skills/pstack-how/SKILL.md").is_file())
        self.assertTrue((self.target / ".agents/skills/assimilation-chief-of-staff/SKILL.md").is_file())
        self.assertTrue((self.target / "vendor/matt/skills/productivity/grill-me/SKILL.md").is_file())
        self.assertTrue((self.target / "vendor/pstack/agents/architect.md").is_file())
        self.assertEqual(self.run_tool("check").returncode, 0)
        lock = json.loads((self.target / "sources.lock.json").read_text())
        self.assertEqual(len(lock["sources"]), 2)

        # Upstream changes cannot be silently adopted: the check reveals them.
        f = self.matt / "skills/engineering/new-skill/SKILL.md"
        f.parent.mkdir(parents=True)
        f.write_text("---\nname: new-skill\n---\nNew\n")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "new skill")
        after = self.run_tool("check")
        self.assertEqual(after.returncode, 2)
        self.assertTrue(json.loads(after.stdout)["sources"]["matt"]["changed"])
        self.assertEqual(self.run_tool("install").returncode, 1)
        self.assertFalse((self.target / ".agents/skills/matt-new-skill/SKILL.md").exists())
        updated = self.run_tool("install", "--approve-update")
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.assertTrue((self.target / ".agents/skills/matt-new-skill/SKILL.md").is_file())
        self.assertEqual(self.run_tool("check").returncode, 0)

    def test_failed_install_does_not_mutate_working_tree(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        original = (self.target / "sources.lock.json").read_text()
        self.env["ASSIMILATION_PSTACK_SOURCE"] = str(self.work / "missing")
        result = self.run_tool("install", "--approve-update")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(original, (self.target / "sources.lock.json").read_text())
        self.assertTrue((self.target / ".agents/skills/matt-wayfinder/SKILL.md").is_file())

    def test_unmanaged_skills_directory_is_not_overwritten(self):
        existing = self.target / ".agents/skills/unrelated/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("Keep me untouched\n")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ownership marker", result.stderr)
        self.assertEqual(existing.read_text(), "Keep me untouched\n")

    def test_unmanaged_extra_skill_survives_a_reviewed_update(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        existing = self.target / ".agents/skills/unrelated/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("Private extra skill\n")
        result = self.run_tool("install", "--approve-update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(existing.read_text(), "Private extra skill\n")

    def test_unmanaged_vendor_is_not_overwritten(self):
        original = self.target / "vendor/unrelated/important.txt"
        original.parent.mkdir(parents=True)
        original.write_text("Unmanaged dependency\n")
        before = self.snapshot()
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("ownership marker", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_edited_owned_wrapper_is_not_overwritten(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        original = self.target / ".agents/skills/matt-wayfinder/SKILL.md"
        original.write_text("My deliberately edited wrapper\n")
        before = self.snapshot()
        result = self.run_tool("install", "--approve-update")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("changed", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_missing_lock_is_not_an_invented_update_baseline(self):
        self.env["ASSIMILATION_MATT_SOURCE"] = str(self.work / "missing")
        result = self.run_tool("check")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"status": "not-installed", "sources": {}})
        self.assertFalse((self.target / "sources.lock.json").exists())

    def test_reviewed_update_plan_installs_exact_commits_not_later_main(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        old = json.loads((self.target / "sources.lock.json").read_text())["sources"]
        skill = self.matt / "skills/engineering/wayfinder/SKILL.md"
        skill.write_text("Reviewed version\n")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "reviewed")
        reviewed = git(self.matt, "rev-parse", "HEAD")
        plan = {"schema": 1, "sources": {
            "matt": {"from_sha": old["matt"]["sha"], "to_sha": reviewed},
            "pstack": {"from_sha": old["pstack"]["sha"], "to_sha": old["pstack"]["sha"]},
        }}
        path = self.target / "sources.update.json"
        path.write_text(json.dumps(plan))
        skill.write_text("Not reviewed yet\n")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "not reviewed")
        result = self.run_tool("install", "--approve-update", "--update-plan", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / "vendor/matt/skills/engineering/wayfinder/SKILL.md").read_text(),
                         "Reviewed version\n")
        self.assertEqual(json.loads((self.target / "sources.lock.json").read_text())["sources"]["matt"]["sha"],
                         reviewed)

    def test_existing_install_guard_blocks_mutation(self):
        guard = self.target / ".assimilation-install.lock"
        guard.mkdir()
        (guard / "owner.txt").write_text("Another installer or interrupted install\n")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("installer", result.stderr)
        self.assertEqual((guard / "owner.txt").read_text(), "Another installer or interrupted install\n")
        self.assertFalse((self.target / "vendor").exists())

    def test_every_backup_and_install_failure_restores_original_trees_and_lock(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        for fault in ("backup-vendor", "backup-skills", "backup-lock", "install-vendor", "install-skills", "install-lock"):
            with self.subTest(fault=fault):
                result = self.run_fault(fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("injected " + fault + " failure", result.stderr)
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(list(self.target.rglob(".assimilation-stage-*")))

    def test_restore_failure_retains_recoverable_original_and_blocks_retry(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        result = self.run_fault("install-lock+restore-vendor")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("rollback incomplete", result.stderr)
        backups = list(self.target.glob(".assimilation-stage-*/backup-vendor"))
        self.assertEqual(len(backups), 1)
        for relative, expected in before.items():
            if relative.startswith("vendor/") and expected != "directory":
                self.assertEqual((backups[0] / relative.removeprefix("vendor/")).read_bytes(), expected)
        self.assertEqual((self.target / "sources.lock.json").read_bytes(), before["sources.lock.json"])
        self.assertTrue((self.target / ".agents/skills/matt-wayfinder/SKILL.md").is_file())
        retry = self.run_tool("install", "--approve-update")
        self.assertEqual(retry.returncode, 1)
        self.assertIn("retained backups", retry.stderr)
        self.assertTrue(backups[0].is_dir())

    def test_failed_removal_keeps_original_backup_and_new_tree(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        result = self.run_fault("install-lock+remove-skills")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("rollback incomplete", result.stderr)
        backups = list((self.target / ".agents").glob(".assimilation-stage-*/backup-skills"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "matt-wayfinder/SKILL.md").read_bytes(),
                         (self.target / ".agents/skills/matt-wayfinder/SKILL.md").read_bytes())

    def test_replacement_staging_respects_independent_destination_filesystems(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        result = self.run_fault("device-boundaries")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / "vendor/matt/LICENSE").is_file())

    def test_locked_materialization_uses_baseline_and_preserves_lock_bytes(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = (self.target / "sources.lock.json").read_bytes()
        shutil.rmtree(self.target / "vendor")
        shutil.rmtree(self.target / ".agents")
        path = self.matt / "skills/engineering/wayfinder/SKILL.md"
        path.write_text("Unreviewed later revision\n")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "later")
        result = self.run_tool("install", "--locked")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / "sources.lock.json").read_bytes(), before)
        self.assertEqual((self.target / "vendor/matt/skills/engineering/wayfinder/SKILL.md").read_text(),
                         "---\nname: wayfinder\n---\nOriginal Wayfinder\n")

    def test_owned_tree_additions_deletions_and_vendor_edits_are_rejected(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        cases = [
            (".agents/skills/matt-wayfinder/extra.txt", "add"),
            (".agents/skills/matt-wayfinder/SKILL.md", "delete"),
            (".agents/skills/assimilation-chief-of-staff/SKILL.md", "edit"),
            ("vendor/matt/LICENSE", "edit"),
            ("vendor/unmanaged.txt", "add"),
        ]
        for name, change in cases:
            with self.subTest(name=name):
                path = self.target / name
                previous = path.read_bytes() if path.exists() else None
                if change == "delete":
                    path.unlink()
                else:
                    path.write_text("User content must survive\n")
                before = self.snapshot()
                result = self.run_tool("install", "--approve-update")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.snapshot(), before)
                if previous is None:
                    path.unlink()
                else:
                    path.write_bytes(previous)

    def test_legacy_and_malformed_ownership_markers_fail_closed(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        marker = self.target / ".agents/skills/.assimilation-managed.json"
        original = marker.read_bytes()
        for data in ({"owned": ["matt-wayfinder"]}, [], {"schema": 2, "owned": {"../escape": "a" * 64}}):
            with self.subTest(data=data):
                marker.write_text(json.dumps(data))
                before = self.snapshot()
                result = self.run_tool("install", "--approve-update")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.snapshot(), before)
                marker.write_bytes(original)

    def test_symlink_destination_ancestor_never_touches_external_tree(self):
        outside = self.work / "external-agents"
        outside.mkdir()
        canary = outside / "keep.txt"
        canary.write_text("External bytes\n")
        (self.target / ".agents").symlink_to(outside, target_is_directory=True)
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Symlink", result.stderr)
        self.assertEqual(list(outside.iterdir()), [canary])
        self.assertEqual(canary.read_text(), "External bytes\n")

    def test_symlinked_upstream_root_is_rejected_without_copying_external_data(self):
        outside = self.work / "outside-source"
        (outside / "skills/unsafe").mkdir(parents=True)
        (outside / "skills/unsafe/SKILL.md").write_text("External bytes\n")
        shutil.rmtree(self.pstack / "pstack")
        (self.pstack / "pstack").symlink_to(outside, target_is_directory=True)
        git(self.pstack, "add", ".")
        git(self.pstack, "commit", "-m", "unsafe symlink root")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue("Source root" in result.stderr or "not a directory" in result.stderr, result.stderr)
        self.assertFalse((self.target / "vendor").exists())
        self.assertEqual((outside / "skills/unsafe/SKILL.md").read_text(), "External bytes\n")

    def test_symlinked_local_skill_root_is_rejected(self):
        outside = self.work / "outside-skill"
        outside.mkdir()
        (outside / "SKILL.md").write_text("External bytes\n")
        (self.target / "skills/external").symlink_to(outside, target_is_directory=True)
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("symlink", result.stderr)
        self.assertFalse((self.target / "vendor").exists())

    def test_move_then_interruption_preserves_originals(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        for fault in ("after-backup-vendor", "after-backup-skills", "after-backup-lock",
                      "after-install-vendor", "after-install-skills", "after-install-lock",
                      "install-lock+after-restore-vendor", "install-lock+after-restore-skills",
                      "install-lock+after-restore-lock"):
            with self.subTest(fault=fault):
                result = self.run_fault(fault)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(any(part in result.stderr for part in fault.split("+")), result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_unmanaged_nested_metadata_is_preserved_byte_for_byte(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        metadata = self.target / ".agents/skills/unrelated/.git/config"
        metadata.parent.mkdir(parents=True)
        metadata.write_text("User metadata, not a fetched repository\n")
        result = self.run_tool("install", "--approve-update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(metadata.read_text(), "User metadata, not a fetched repository\n")

    def test_initial_install_failures_leave_no_targets_or_empty_agents_parent(self):
        for fault in ("install-vendor", "install-skills", "install-lock", "after-install-vendor", "after-install-lock"):
            with self.subTest(fault=fault):
                result = self.run_fault(fault)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), {})
                self.assertFalse((self.target / ".agents").exists())
                self.assertFalse(list(self.target.glob(".assimilation-*")))

    def test_stale_unapproved_and_malformed_plans_cannot_mutate_installation(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        old = json.loads((self.target / "sources.lock.json").read_text())["sources"]
        good = {"schema": 1, "sources": {name: {"from_sha": entry["sha"], "to_sha": entry["sha"]}
                                            for name, entry in old.items()}}
        path = self.target / "sources.update.json"
        path.write_text(json.dumps(good))
        before = self.snapshot()
        unapproved = self.run_tool("install", "--update-plan", str(path))
        self.assertEqual(unapproved.returncode, 1)
        self.assertIn("--approve-update", unapproved.stderr)
        self.assertEqual(self.snapshot(), before)
        variants = [[], {"schema": 1, "sources": {}},
                    {"schema": 1, "sources": {**good["sources"], "matt": {"from_sha": "0" * 40, "to_sha": "1" * 40}}},
                    {"schema": 1, "sources": {**good["sources"], "matt": {"from_sha": old["matt"]["sha"], "to_sha": "main"}}}]
        for plan in variants:
            with self.subTest(plan=plan):
                path.write_text(json.dumps(plan))
                result = self.run_tool("install", "--approve-update", "--update-plan", str(path))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_invalid_lock_cannot_be_treated_as_initial_install(self):
        path = self.target / "sources.lock.json"
        for data in ([], {"schema": 1, "sources": {}}, {"schema": 1, "sources": {"matt": {"sha": "0" * 40}}}):
            with self.subTest(data=data):
                path.write_text(json.dumps(data))
                before = self.snapshot()
                for command in (("check",), ("install",), ("install", "--approve-update")):
                    result = self.run_tool(*command)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(self.snapshot(), before)

    def test_dangling_target_marker_links_and_special_files_fail_closed(self):
        for name in ("vendor", ".agents/skills", "sources.lock.json"):
            with self.subTest(name=name):
                path = self.target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(self.work / "does-not-exist")
                result = self.run_tool("install")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertTrue(path.is_symlink())
                path.unlink()
        self.assertEqual(self.run_tool("install").returncode, 0)
        marker = self.target / ".agents/skills/.assimilation-managed.json"
        original = marker.read_bytes()
        marker.unlink()
        marker.symlink_to(self.work / "does-not-exist")
        result = self.run_tool("install", "--approve-update")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(marker.is_symlink())
        marker.unlink()
        marker.write_bytes(original)
        if hasattr(os, "mkfifo"):
            fifo = self.target / ".agents/skills/private-pipe"
            os.mkfifo(fifo)
            result = self.run_tool("install", "--approve-update")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("special file", result.stderr)

    def test_upstream_descendant_symlink_is_rejected_without_reading_target(self):
        canary = self.work / "external-secret.txt"
        canary.write_text("External bytes\n")
        link = self.matt / "skills/engineering/wayfinder/link.txt"
        link.symlink_to(canary)
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "unsafe linked reference")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("symlink", result.stderr)
        self.assertFalse((self.target / "vendor").exists())
        self.assertEqual(canary.read_text(), "External bytes\n")


if __name__ == "__main__":
    unittest.main()
