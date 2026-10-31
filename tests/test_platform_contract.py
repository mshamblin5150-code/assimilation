"""Unsupported-runtime refusal at public source-operation boundaries."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import skills
import snapshot_sources
import propose_update
import publish_update


class PlatformContractTests(unittest.TestCase):
    def test_unsupported_runtime_refuses_source_operations_before_io(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "proposal"
            # Replace only this module's os reference, preserving pathlib's host.
            unsupported = types.SimpleNamespace(name="nt")
            operations = {
                "install": lambda: skills.install(False, locked=True),
                "check": skills.check,
                "read-lock": skills.read_lock,
                "verify": lambda: snapshot_sources.verify(root),
                "read-pins": lambda: snapshot_sources.read_pins(root),
                "refresh": lambda: snapshot_sources.refresh(False),
                "prepare": lambda: snapshot_sources.prepare(root / "plan.json", output),
                "propose": lambda: propose_update.propose(output),
                "publish": lambda: publish_update.publish(output, None),
            }
            with patch.object(skills, "ROOT", root), patch.object(snapshot_sources, "ROOT", root), \
                    patch.object(skills, "os", unsupported), \
                    patch("subprocess.run", side_effect=AssertionError("No child process permitted")) as child, \
                    patch.object(Path, "read_bytes", side_effect=AssertionError("No source read permitted")), \
                    patch.object(Path, "read_text", side_effect=AssertionError("No source read permitted")):
                for name, operation in operations.items():
                    with self.subTest(operation=name):
                        with self.assertRaisesRegex(RuntimeError, "Unsupported runtime.*POSIX"):
                            operation()
                        self.assertEqual(list(root.iterdir()), [])
                child.assert_not_called()

    def test_unsupported_runtime_cli_returns_safe_error_before_io(self):
        commands = ((skills, ["skills.py", "install", "--locked"]),
                    (skills, ["skills.py", "check"]),
                    (snapshot_sources, ["snapshot_sources.py", "verify"]),
                    (snapshot_sources, ["snapshot_sources.py", "refresh"]),
                    (snapshot_sources, ["snapshot_sources.py", "prepare", "--update-plan", "plan", "--output-dir", "out"]),
                    (propose_update, ["propose_update.py", "--output-dir", "out"]),
                    (publish_update, ["publish_update.py", "--proposal-dir", "out"]))
        with patch.object(skills, "os", types.SimpleNamespace(name="nt")), \
                patch("subprocess.run", side_effect=AssertionError("No child process permitted")), \
                patch.object(Path, "mkdir", side_effect=AssertionError("No directory write permitted")), \
                patch.object(Path, "read_bytes", side_effect=AssertionError("No source read permitted")), \
                patch.object(Path, "read_text", side_effect=AssertionError("No source read permitted")):
            for module, argv in commands:
                with self.subTest(command=argv):
                    error = io.StringIO()
                    with patch.object(sys, "argv", argv), contextlib.redirect_stderr(error):
                        self.assertEqual(module.main(), 1)
                    self.assertIn("Unsupported runtime", error.getvalue())
                    self.assertIn("POSIX", error.getvalue())

    def test_help_remains_available_on_unsupported_runtime(self):
        with patch.object(skills, "os", types.SimpleNamespace(name="nt")):
            for module in (skills, snapshot_sources, propose_update, publish_update):
                with self.subTest(module=module.__name__), patch.object(sys, "argv", [module.__name__, "--help"]):
                    with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                        module.main()
                    self.assertEqual(result.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
