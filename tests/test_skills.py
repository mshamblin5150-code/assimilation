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
                        ("symlink", os.readlink(path)) if path.is_symlink() else
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
sys.path.insert(0, str(root / 'scripts'))
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

    def test_inherited_global_git_config_cannot_execute_external_transport(self):
        marker = self.work / "external-helper-ran"
        helper = self.work / "external-helper.py"
        helper.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('ran')\n")
        config = self.work / "hostile.gitconfig"
        git(self.work, "config", "--file", str(config),
            "url.ext::" + sys.executable + " " + str(helper) + ".insteadOf", str(self.matt))
        self.env["GIT_CONFIG_GLOBAL"] = str(config)
        self.env["GIT_ALLOW_PROTOCOL"] = "file:ext"
        result = self.run_tool("install")
        self.assertFalse(marker.exists(), "inherited Git configuration executed a transport helper")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / ".agents/skills/matt-wayfinder/SKILL.md").exists())

    def test_inherited_git_environment_cannot_redirect_repositories(self):
        redirected = self.work / "not-a-repository"
        self.env.update(GIT_DIR=str(redirected), GIT_WORK_TREE=str(self.work),
                        GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="url.ext::false.insteadOf",
                        GIT_CONFIG_VALUE_0=str(self.matt))
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(redirected.exists())
        self.assertEqual(self.run_tool("check").returncode, 0)

    def test_caller_repository_url_rewrites_do_not_redirect_sources(self):
        git(self.target, "init", "--initial-branch=main")
        git(self.target, "config", "url.file:///nonexistent-mirror.insteadOf", str(self.matt))
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_tool("check").returncode, 0)

    def test_inherited_template_hooks_and_smudge_filters_are_not_executed(self):
        marker = self.work / "git-execution-ran"
        helper = self.work / "marker.py"
        helper.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('ran')\n")
        template = self.work / "template"
        hook = template / "hooks/post-checkout"
        hook.parent.mkdir(parents=True)
        hook.write_text("#!/bin/sh\n" + sys.executable + " " + str(helper) + "\n")
        hook.chmod(0o755)
        config = self.work / "hostile.gitconfig"
        git(self.work, "config", "--file", str(config), "init.templateDir", str(template))
        git(self.work, "config", "--file", str(config), "filter.marker.smudge", sys.executable + " " + str(helper))
        attrs = self.matt / ".gitattributes"
        attrs.write_text("* filter=marker\n")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "synthetic attributes")
        self.env.update(GIT_CONFIG_GLOBAL=str(config), GIT_TEMPLATE_DIR=str(template))
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_caller_protocol_restrictions_are_not_broadened(self):
        self.env["GIT_ALLOW_PROTOCOL"] = "https"
        result = self.run_tool("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.target / "vendor").exists())
        self.assertFalse((self.target / ".agents/skills").exists())

    def test_bridge_preserves_invocation_restrictions_for_both_hosts(self):
        original = ("---\nname: wayfinder\ndescription: Synthetic\n"
                    "disable-model-invocation: true\nuser-invocable: false\n"
                    "allowed-tools:\n  - Read\n  - Grep\n---\nOriginal content\n")
        source = self.matt / "skills/engineering/wayfinder/SKILL.md"
        source.write_text(original)
        policy = source.parent / "agents/openai.yaml"
        policy.parent.mkdir()
        policy.write_text("interface:\n  display_name: Synthetic\npolicy:\n  allow_implicit_invocation: false\n")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "restricted synthetic skill")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        bridge = self.target / ".agents/skills/matt-wayfinder"
        wrapper = (bridge / "SKILL.md").read_text()
        self.assertIn("disable-model-invocation: true", wrapper)
        self.assertIn("user-invocable: false", wrapper)
        self.assertIn('allowed-tools:\n  - "Read"\n  - "Grep"\n', wrapper)
        self.assertEqual((bridge / "agents/openai.yaml").read_text(),
                         "policy:\n  allow_implicit_invocation: false\n")
        self.assertEqual((self.target / "vendor/matt/skills/engineering/wayfinder/SKILL.md").read_text(), original)
        ordinary = (self.target / ".agents/skills/matt-grill-with-docs/SKILL.md").read_text()
        self.assertNotIn("disable-model-invocation", ordinary)
        self.assertFalse((self.target / ".agents/skills/matt-grill-with-docs/agents/openai.yaml").exists())

    def test_sidecar_only_and_frontmatter_only_restrictions_cross_host_boundary(self):
        source = self.matt / "skills/engineering/wayfinder/SKILL.md"
        policy = source.parent / "agents/openai.yaml"
        policy.parent.mkdir()
        policy.write_text("policy:\n  allow_implicit_invocation: false # human only\n")
        pstack = self.pstack / "pstack/skills/how/SKILL.md"
        pstack.write_bytes(b"---\r\nname: how\r\ndescription: Synthetic\r\n"
                          b"'disable-model-invocation': true # explicit\r\n"
                          b"allowed-tools: 'Read, Grep'\r\npaths: [\"**/*.ts\"]\r\n---\r\nOriginal\r\n")
        for repo in (self.matt, self.pstack):
            git(repo, "add", ".")
            git(repo, "commit", "-m", "synthetic cross-host restrictions")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("matt-wayfinder", "pstack-how"):
            bridge = self.target / ".agents/skills" / name
            self.assertIn("disable-model-invocation: true", (bridge / "SKILL.md").read_text())
            self.assertEqual((bridge / "agents/openai.yaml").read_text(),
                             "policy:\n  allow_implicit_invocation: false\n")
        self.assertIn('allowed-tools: "Read, Grep"',
                      (self.target / ".agents/skills/pstack-how/SKILL.md").read_text())

    def test_ambiguous_or_unsupported_restrictions_refuse_before_replacement(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        source = self.matt / "skills/engineering/wayfinder/SKILL.md"
        for declaration in (
            "disable-model-invocation: true\ndisable-model-invocation: false",
            'disable-model-invocation: "true"',
            "disable-model-invocation: &alias true",
            "disable-model-invocation: *alias",
            "disable-model-invocation: [true]",
            "disable-model-invocation: yes",
            "  disable-model-invocation: true",
            "allowed-tools: {unexpected: mapping}",
            "allowed-tools: *tools",
            "allowed-tools: [*tools]",
            "allowed-tools: null",
            "allowed-tools: [true]",
            "hooks: {PostToolUse: executable}",
            "<<: *policy",
        ):
            with self.subTest(declaration=declaration):
                source.write_text("---\nname: wayfinder\ndescription: Synthetic\n" + declaration + "\n---\nSource\n")
                git(self.matt, "add", ".")
                git(self.matt, "commit", "-m", "ambiguous synthetic metadata")
                result = self.run_tool("install", "--approve-update")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), before)

    def test_conflicting_host_policy_and_dependency_configuration_refuse(self):
        source = self.matt / "skills/engineering/wayfinder/SKILL.md"
        source.write_text("---\nname: wayfinder\ndescription: Synthetic\n"
                          "disable-model-invocation: true\n---\nSource\n")
        sidecar = source.parent / "agents/openai.yaml"
        sidecar.parent.mkdir()
        for policy in ("policy:\n  allow_implicit_invocation: true\n",
                       "policy: {allow_implicit_invocation: false}\n",
                       "policy:\n  allow_implicit_invocation: false\n  unknown: false\n",
                       "dependencies:\n  tools: []\n"):
            with self.subTest(policy=policy):
                sidecar.write_text(policy)
                git(self.matt, "add", ".")
                git(self.matt, "commit", "-m", "unsupported synthetic host policy")
                result = self.run_tool("install")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.target / "vendor").exists())
                self.assertFalse((self.target / ".agents/skills").exists())

    def test_copied_upstream_scripts_are_preserved_but_never_executed(self):
        marker = self.work / "upstream-script-ran"
        script = self.pstack / "pstack/scripts/link-skills.sh"
        script.parent.mkdir()
        payload = "#!/bin/sh\nprintf ran > " + str(marker) + "\n"
        script.write_text(payload)
        script.chmod(0o755)
        git(self.pstack, "add", ".")
        git(self.pstack, "commit", "-m", "inert synthetic upstream script")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.target / "vendor/pstack/scripts/link-skills.sh").read_text(), payload)

    def test_git_protocol_from_user_denial_is_not_broadened(self):
        self.env.pop("GIT_ALLOW_PROTOCOL", None)
        self.env["GIT_PROTOCOL_FROM_USER"] = "0"
        control = subprocess.run(["git", "ls-remote", str(self.matt)],
                                 cwd=self.work, env=self.env, capture_output=True)
        self.assertNotEqual(control.returncode, 0)
        denied = self.run_tool("install")
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse((self.target / "vendor").exists())
        self.env.pop("GIT_PROTOCOL_FROM_USER")
        self.assertEqual(self.run_tool("install").returncode, 0)

    def test_utf8_bom_does_not_discard_invocation_policy(self):
        source = self.matt / "skills/engineering/wayfinder/SKILL.md"
        source.write_text("\ufeff---\nname: wayfinder\ndescription: Synthetic\n"
                          "disable-model-invocation: true\n---\nSource\n", encoding="utf-8")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "synthetic encoded frontmatter")
        installed = self.run_tool("install")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        wrapper = self.target / ".agents/skills/matt-wayfinder/SKILL.md"
        self.assertIn("disable-model-invocation: true", wrapper.read_text())
        source.write_text("---\nname: wayfinder\ndescription: Synthetic\n---\nSource\n")
        sidecar = source.parent / "agents/openai.yaml"
        sidecar.parent.mkdir()
        sidecar.write_text("\ufeffpolicy:\n  allow_implicit_invocation: false\n", encoding="utf-8")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "synthetic encoded host policy")
        updated = self.run_tool("install", "--approve-update")
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.assertIn("disable-model-invocation: true", wrapper.read_text())

    def test_mirror_acquisition_is_distinguished_from_canonical_upstream(self):
        installed = self.run_tool("install")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        lock = json.loads((self.target / "sources.lock.json").read_text())
        source = lock["sources"]["matt"]
        self.assertEqual(source["repository"], "https://github.com/mattpocock/skills.git")
        self.assertEqual(source["acquisition"]["kind"], "operator-local-mirror")
        self.assertEqual(len(source["acquisition"]["source_sha256"]), 64)
        self.assertNotIn(str(self.matt), (self.target / "sources.lock.json").read_text())

    def test_nonlocal_override_and_git_failure_do_not_echo_sensitive_input(self):
        sentinel = "SYNTHETIC-SENSITIVE-SOURCE"
        self.env["ASSIMILATION_MATT_SOURCE"] = "https://user:" + sentinel + "@example.invalid/repo.git"
        result = self.run_tool("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(sentinel, result.stdout + result.stderr)
        self.assertFalse((self.target / "vendor").exists())

    def test_destination_reparse_metadata_refuses_without_replacement(self):
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        launcher = r"""
import pathlib, runpy, sys, types
root = pathlib.Path(sys.argv[1])
original = pathlib.Path.lstat
def synthetic_reparse(path):
    info = original(path)
    if path == root / 'vendor':
        return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
    return info
pathlib.Path.lstat = synthetic_reparse
sys.path.insert(0, str(root / 'scripts'))
sys.argv = [str(root / 'scripts/skills.py'), 'install', '--approve-update']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        result = subprocess.run([sys.executable, "-c", launcher, str(self.target)],
                                cwd=self.target, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reparse", result.stderr.lower())
        self.assertEqual(self.snapshot(), before)

    def test_git_failure_suppresses_remote_stderr_and_arguments(self):
        launcher = r"""
import pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
import skills
subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 1, b'', b'SYNTHETIC-STDERR-SECRET')
try:
    skills.git('ls-remote', 'https://SYNTHETIC-URL-SECRET@example.invalid/repo')
except RuntimeError as error:
    print(error)
else:
    raise SystemExit('expected Git refusal')
"""
        result = subprocess.run([sys.executable, "-c", launcher, str(self.target)],
                                cwd=self.target, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("failed", result.stdout)
        self.assertNotIn("SYNTHETIC-STDERR-SECRET", result.stdout + result.stderr)
        self.assertNotIn("SYNTHETIC-URL-SECRET", result.stdout + result.stderr)

    def test_source_reparse_is_refused_before_copying_any_payload(self):
        launcher = r"""
import pathlib, sys, types
root, source = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sys.path.insert(0, str(root / 'scripts'))
import skills
original = pathlib.Path.lstat
def synthetic_reparse(path):
    info = original(path)
    if path == source / 'skills/engineering':
        return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
    return info
pathlib.Path.lstat = synthetic_reparse
try:
    skills.copy_source(source, root / 'unaccepted-copy', fetched=True)
except RuntimeError as error:
    print(error)
    raise SystemExit(1)
"""
        result = subprocess.run([sys.executable, "-c", launcher, str(self.target), str(self.matt)],
                                cwd=self.target, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reparse", result.stdout.lower())
        self.assertFalse((self.target / "unaccepted-copy").exists())

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

    def test_contained_upstream_file_link_is_preserved_and_updateable(self):
        (self.matt / "CLAUDE.md").write_text("Original upstream instructions\n")
        (self.matt / "AGENTS.md").symlink_to("CLAUDE.md")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "portable upstream instruction link")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        link = self.target / "vendor/matt/AGENTS.md"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "CLAUDE.md")
        self.assertEqual(link.read_text(), "Original upstream instructions\n")
        lock = json.loads((self.target / "sources.lock.json").read_text())
        self.assertEqual(lock["sources"]["matt"]["sha"], git(self.matt, "rev-parse", "HEAD"))
        updated = self.run_tool("install", "--approve-update")
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "CLAUDE.md")

    def test_contained_multihop_file_links_keep_literal_paths(self):
        (self.matt / "CLAUDE.md").write_text("Contained instruction file\n")
        (self.matt / "docs/guide.md").symlink_to("../CLAUDE.md")
        (self.matt / "AGENTS.md").symlink_to("docs/guide.md")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "contained file link chain")
        result = self.run_tool("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.target / "vendor/matt"
        self.assertEqual(os.readlink(root / "AGENTS.md"), "docs/guide.md")
        self.assertEqual(os.readlink(root / "docs/guide.md"), "../CLAUDE.md")
        self.assertEqual((root / "AGENTS.md").read_text(), "Contained instruction file\n")
        self.assertEqual(self.run_tool("install", "--approve-update").returncode, 0)

    def test_owned_link_spelling_and_target_edits_cannot_be_overwritten(self):
        (self.matt / "CLAUDE.md").write_text("Original instruction file\n")
        (self.matt / "AGENTS.md").symlink_to("CLAUDE.md")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "owned file link")
        self.assertEqual(self.run_tool("install").returncode, 0)
        root = self.target / "vendor/matt"
        link, target = root / "AGENTS.md", root / "CLAUDE.md"
        for edit in ("spelling", "target"):
            with self.subTest(edit=edit):
                if edit == "spelling":
                    link.unlink()
                    link.symlink_to("./CLAUDE.md")
                else:
                    target.write_text("User-edited instruction file\n")
                before = self.snapshot()
                result = self.run_tool("install", "--approve-update")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("Owned content changed", result.stderr)
                self.assertEqual(self.snapshot(), before)
                link.unlink()
                link.symlink_to("CLAUDE.md")
                target.write_text("Original instruction file\n")

    def test_unsafe_source_file_links_fail_without_mutation(self):
        outside = self.work / "external-data.txt"
        outside.write_text("Must remain external\n")
        (self.matt / "CLAUDE.md").write_text("Contained file\n")
        link = self.matt / "AGENTS.md"
        for spelling in (str(outside), "../external-data.txt", "../pstack/LICENSE", "missing.md", ".", "docs",
                         "AGENTS.md", "C:/outside.txt", "C:outside.txt", "\\\\host\\share\\file",
                         "docs\\guide.md", "CLAUDE.md/", "CLAUDE.md/../CLAUDE.md", "docs/../../escape"):
            with self.subTest(spelling=spelling):
                link.symlink_to(spelling)
                git(self.matt, "add", ".")
                git(self.matt, "commit", "-m", "untrusted source link")
                result = self.run_tool("install")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.snapshot(), {})
                self.assertFalse((self.target / ".agents").exists())
                self.assertEqual(outside.read_text(), "Must remain external\n")
                link.unlink()

    def test_cyclic_and_directory_component_links_fail_closed(self):
        agents = self.matt / "AGENTS.md"
        middle = self.matt / "CLAUDE.md"
        agents.symlink_to("CLAUDE.md")
        middle.symlink_to("AGENTS.md")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "cycle")
        cycle = self.run_tool("install")
        self.assertEqual(cycle.returncode, 1, cycle.stderr)
        self.assertIn("Cyclic", cycle.stderr)
        self.assertEqual(self.snapshot(), {})
        agents.unlink()
        middle.unlink()
        (self.matt / "linked-docs").symlink_to("docs", target_is_directory=True)
        agents.symlink_to("linked-docs/engineering/wayfinder.md")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "directory component link")
        directory = self.run_tool("install")
        self.assertEqual(directory.returncode, 1, directory.stderr)
        self.assertEqual(self.snapshot(), {})

    def test_file_links_remain_disallowed_in_local_and_unmanaged_skills(self):
        local = self.target / "skills/assimilation-chief-of-staff"
        (local / "alias.md").symlink_to("SKILL.md")
        refused = self.run_tool("install")
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertEqual(self.snapshot(), {})
        (local / "alias.md").unlink()
        self.assertEqual(self.run_tool("install").returncode, 0)
        unknown = self.target / ".agents/skills/unrelated"
        unknown.mkdir()
        (unknown / "SKILL.md").write_text("User skill\n")
        (unknown / "alias.md").symlink_to("SKILL.md")
        before = self.snapshot()
        refused = self.run_tool("install", "--approve-update")
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_file_link_installation_preserves_transaction_rollback(self):
        (self.matt / "CLAUDE.md").write_text("Original instruction file\n")
        (self.matt / "AGENTS.md").symlink_to("CLAUDE.md")
        git(self.matt, "add", ".")
        git(self.matt, "commit", "-m", "contained file link")
        self.assertEqual(self.run_tool("install").returncode, 0)
        before = self.snapshot()
        for fault in ("install-lock", "after-backup-vendor", "after-install-vendor"):
            with self.subTest(fault=fault):
                failed = self.run_fault(fault)
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(os.readlink(self.target / "vendor/matt/AGENTS.md"), "CLAUDE.md")


if __name__ == "__main__":
    unittest.main()
