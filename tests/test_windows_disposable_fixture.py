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

    def test_symlink_reparse_attribute_observed_without_following(self):
        with tempfile.TemporaryDirectory(prefix="assimilation-windows-fixture-") as root:
            base = Path(root)
            target = base / "target.txt"
            target.write_bytes(b"test-owned target")
            link = base / "link.txt"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("test runner cannot create a file symlink: " + type(exc).__name__)
            info = link.lstat()
            self.assertTrue(info.st_file_attributes & 0x400, "symlink must carry reparse-point flag")
            self.assertTrue(link.is_symlink())
            self.assertNotEqual((info.st_dev, info.st_ino),
                                (target.stat().st_dev, target.stat().st_ino))
            self.assertEqual(target.read_bytes(), b"test-owned target")

    def test_regular_fixture_is_not_a_reparse_point(self):
        with tempfile.TemporaryDirectory(prefix="assimilation-windows-fixture-") as root:
            regular = Path(root) / "regular.bin"
            regular.write_bytes(b"test-owned regular")
            self.assertEqual(regular.lstat().st_file_attributes & 0x400, 0)

    def test_observer_accepts_regular_chain_and_refuses_reparse_leaf(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from windows_fixture_observer import observe_regular_chain, Refused
        with tempfile.TemporaryDirectory(prefix="assimilation-windows-fixture-") as root:
            base = Path(root)
            (base / "folder").mkdir()
            (base / "folder" / "normal.txt").write_bytes(b"synthetic")
            self.assertTrue(observe_regular_chain(base, ("folder", "normal.txt")))
            (base / "folder" / "target.txt").write_bytes(b"synthetic target")
            link = base / "folder" / "link.txt"
            try:
                link.symlink_to(base / "folder" / "target.txt")
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlink unavailable: " + type(exc).__name__)
            with self.assertRaisesRegex(Refused, "reparse-point"):
                observe_regular_chain(base, ("folder", "link.txt"))

    def test_observer_refuses_reparse_ancestor_and_missing_leaf(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from windows_fixture_observer import observe_regular_chain, Refused
        with tempfile.TemporaryDirectory(prefix="assimilation-windows-fixture-") as root:
            base = Path(root)
            real = base / "real"
            real.mkdir()
            (real / "file.txt").write_bytes(b"synthetic")
            with self.assertRaisesRegex(Refused, "unobservable-path"):
                observe_regular_chain(base, ("missing", "file.txt"))
            link = base / "linked"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("directory symlink unavailable: " + type(exc).__name__)
            with self.assertRaisesRegex(Refused, "reparse-point"):
                observe_regular_chain(base, ("linked", "file.txt"))


if __name__ == "__main__":
    unittest.main()
