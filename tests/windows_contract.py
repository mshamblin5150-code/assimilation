"""Native Windows refusal contract only; never run source acquisition or installation."""
import argparse
import contextlib
import gettext
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "scripts/skills.py", "scripts/snapshot_sources.py", "scripts/git_runtime.py",
    "scripts/propose_update.py", "scripts/publish_update.py", "tests/windows_contract.py",
)
ACTIVE = False
ATTEMPTS = []
IDENTITY = {}
LOCALE_ROOT = Path(gettext._default_localedir).absolute()


def runtime_locale(path):
    """Argparse's stdlib catalog lookup is runtime housekeeping, not source input."""
    if not isinstance(path, (str, bytes, os.PathLike)):
        return False
    candidate = Path(os.fsdecode(path)).absolute()
    return (".." not in candidate.parts and candidate.name == "messages.mo"
            and candidate.parent.name == "LC_MESSAGES" and candidate.is_relative_to(LOCALE_ROOT)
            and not candidate.is_relative_to(ROOT))


def denied(event, *args, **kwargs):
    ATTEMPTS.append(event)
    raise AssertionError("Contract attempted filesystem I/O or process creation: " + event)


def audit(event, args):
    if event == "open" and args[1] == "r" and runtime_locale(args[0]):
        return
    if ACTIVE and (event == "open" or event.startswith(("subprocess.", "os.spawn", "os.exec"))
                   or event in {"os.system", "os.listdir", "os.scandir", "os.mkdir", "os.rmdir",
                                "os.remove", "os.rename", "os.link", "os.symlink", "os.chmod"}):
        denied(event)


@contextlib.contextmanager
def no_source_io():
    global ACTIVE
    real_stat = os.stat

    def stat_probe(path, *args, **kwargs):
        if runtime_locale(path):
            return real_stat(path, *args, **kwargs)
        return denied("os.stat")
    # Audit hooks cover builtins/io/os opens and process launches. Path metadata
    # queries lack audit events, so reject those separately. Runtime identity is real.
    with patch.object(Path, "stat", side_effect=lambda *a, **k: denied("Path.stat")), \
            patch.object(Path, "lstat", side_effect=lambda *a, **k: denied("Path.lstat")), \
            patch.object(os, "stat", side_effect=stat_probe), \
            patch.object(os, "lstat", side_effect=lambda *a, **k: denied("os.lstat")), \
            patch.object(os, "access", side_effect=lambda *a, **k: denied("os.access")):
        ACTIVE = True
        try:
            yield
        finally:
            ACTIVE = False


class NativeWindowsContractTests(unittest.TestCase):
    def test_actual_native_identity_and_exact_materialized_sources(self):
        self.assertEqual(sys.platform, "win32")
        self.assertEqual(os.name, "nt")
        self.assertEqual(platform.system(), "Windows")
        self.assertTrue(callable(getattr(sys, "getwindowsversion", None)))
        self.assertIs(skills.os, os)
        self.assertEqual(IDENTITY["checkout_head"], IDENTITY["expected_head"])
        self.assertEqual(len(IDENTITY["source_sha256"]), len(SOURCE_FILES))
        self.assertTrue(sys.dont_write_bytecode)

    def test_actual_public_apis_refuse_before_source_io_or_processes(self):
        output = ROOT / ".windows-contract-unused-output"
        operations = {
            "install": lambda: skills.install(False, locked=True),
            "check": skills.check, "read-lock": skills.read_lock,
            "verify": lambda: snapshot_sources.verify(ROOT),
            "read-pins": lambda: snapshot_sources.read_pins(ROOT),
            "refresh": lambda: snapshot_sources.refresh(False),
            "prepare": lambda: snapshot_sources.prepare(ROOT / "unused-plan", output),
            "snapshot-package": lambda: snapshot_sources.package_files(ROOT),
            "propose": lambda: propose_update.propose(output),
            "proposal-package": lambda: propose_update.proposal_files(output),
            "publish": lambda: publish_update.publish(output, None),
        }
        for name, operation in operations.items():
            with self.subTest(operation=name), no_source_io():
                with self.assertRaisesRegex(RuntimeError, "Unsupported runtime.*POSIX"):
                    operation()
        self.assertEqual(ATTEMPTS, [])

    def test_actual_cli_entrypoints_return_nonzero_before_source_io_or_processes(self):
        commands = ((skills, ["skills.py", "install", "--locked"]),
                    (skills, ["skills.py", "check"]),
                    (snapshot_sources, ["snapshot_sources.py", "verify"]),
                    (snapshot_sources, ["snapshot_sources.py", "refresh"]),
                    (snapshot_sources, ["snapshot_sources.py", "prepare", "--update-plan", "unused", "--output-dir", "unused"]),
                    (propose_update, ["propose_update.py", "--output-dir", "unused"]),
                    (publish_update, ["publish_update.py", "--proposal-dir", "unused"]))
        for module, argv in commands:
            error = io.StringIO()
            with self.subTest(command=argv), patch.object(sys, "argv", argv):
                with contextlib.redirect_stderr(error), no_source_io():
                    self.assertEqual(module.main(), 1)
                self.assertIn("Unsupported runtime", error.getvalue())
                self.assertIn("POSIX", error.getvalue())
        self.assertEqual(ATTEMPTS, [])

    def test_actual_help_remains_available_without_source_io_or_processes(self):
        for module in (skills, snapshot_sources, propose_update, publish_update):
            with self.subTest(module=module.__name__), patch.object(sys, "argv", [module.__name__, "--help"]):
                with contextlib.redirect_stdout(io.StringIO()), no_source_io():
                    with self.assertRaises(SystemExit) as result:
                        module.main()
                self.assertEqual(result.exception.code, 0)
        self.assertEqual(ATTEMPTS, [])


def main():
    global skills, snapshot_sources, propose_update, publish_update
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    # Fail rather than skip or simulate away the native claim.
    if sys.platform != "win32" or os.name != "nt" or platform.system() != "Windows":
        print("Native Windows contract requires actual Windows; no native checks ran.", file=sys.stderr)
        return 1
    if not sys.dont_write_bytecode:
        parser.error("Run with python -B to prohibit bytecode writes")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_sha):
        parser.error("Expected exact PR head SHA")
    # Trusted checkout/test bootstrap reads occur before monitored operations.
    # Require exact bytes, not only a checkout SHA or normalized line endings.
    head = (ROOT / ".git/HEAD").read_text(encoding="ascii").strip()
    if head != args.expected_sha:
        parser.error("Checkout must be detached at the exact expected PR head")
    expected = json.loads(os.environ["CONTRACT_SOURCE_SHA256"])
    if set(expected) != set(SOURCE_FILES):
        parser.error("Incomplete contract source identity")
    actual = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}
    if actual != expected:
        parser.error("Materialized contract/source bytes differ from reviewed bytes")
    IDENTITY.update(expected_head=args.expected_sha, checkout_head=head, source_sha256=actual,
                    sys_platform=sys.platform, os_name=os.name, system=platform.system(),
                    windows_version=list(sys.getwindowsversion()), python=sys.version,
                    machine=platform.machine(), executable=sys.executable)
    print("WINDOWS_CONTRACT_IDENTITY " + json.dumps(IDENTITY, sort_keys=True), flush=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    skills, snapshot_sources, propose_update, publish_update = (
        importlib.import_module(name) for name in ("skills", "snapshot_sources", "propose_update", "publish_update"))
    sys.addaudithook(audit)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeWindowsContractTests))
    print("WINDOWS_CONTRACT_RESULT " + json.dumps({
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "io_or_process_attempts": ATTEMPTS,
        "limits": "Refusal/help only. Installer, MSYS fetch, ACLs, junctions, link roundtrip, races and live enforcement untested.",
    }, sort_keys=True), flush=True)
    return 0 if result.wasSuccessful() and not result.skipped and result.testsRun == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
