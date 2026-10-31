"""Read-only native Windows fixture observations; never installs or changes ACLs.

Tests operate exclusively on a temporary directory created by unittest.
They do not prove junction/reparse confinement or secure activation.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "win32", "native Windows fixture only")
class WindowsDisposableFixtureTests(unittest.TestCase):
    def test_owned_temporary_regular_file_identity_and_bytes(self):
        with tempfile.TemporaryDirectory(prefix="assimilation-windows-fixture-") as root:
            base = Path(root)
            file = base / "sentinel.bin"
            file.write_bytes(b"synthetic fixture only")
            before = file.stat()
            self.assertTrue(file.is_file())
            self.assertEqual(file.read_bytes(), b"synthetic fixture only")
            after = file.stat()
            self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
            self.assertEqual(before.st_size, after.st_size)

    def test_unmanaged_sentinel_is_not_touched_by_name_preflight(self):
        with tempfile.TemporaryDirectory(prefix="assimilation-windows-fixture-") as root:
            sentinel = Path(root) / "unmanaged.bin"
            sentinel.write_bytes(b"private fixture sentinel")
            before = sentinel.stat()
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
            from windows_view_names import validate_view_names
            with self.assertRaises(ValueError):
                validate_view_names(["CON.txt"])
            self.assertEqual(sentinel.read_bytes(), b"private fixture sentinel")
            after = sentinel.stat()
            self.assertEqual((before.st_dev, before.st_ino, before.st_size),
                             (after.st_dev, after.st_ino, after.st_size))


if __name__ == "__main__":
    unittest.main()
