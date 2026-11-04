"""Injected metadata only; no real fixture observations or native APIs."""
import sys
import stat
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import windows_fixture_observer as observer

class InjectedObserverTests(unittest.TestCase):
    def chain(self):
        return [SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0),
                SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0),
                SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0)]

    def observe(self, records):
        # Construct paths before the synthetic runtime branch; never touch them.
        root = Path("synthetic-owned-root")
        with patch.object(Path, "lstat", side_effect=records), patch.object(observer.sys, "platform", "win32"):
            return observer.observe_regular_chain(root, ("folder", "leaf.txt"))

    def test_missing_attributes_refuse_at_root_ancestor_and_leaf(self):
        for index in range(3):
            records = self.chain()
            del records[index].st_file_attributes
            with self.subTest(position=index), self.assertRaises(observer.Refused):
                self.observe(records)

    def test_known_regular_chain_remains_observable(self):
        self.assertIs(self.observe(self.chain()), True)

    def test_reparse_refuses_at_each_position(self):
        for index in range(3):
            records = self.chain()
            records[index].st_file_attributes = stat.FILE_ATTRIBUTE_REPARSE_POINT
            with self.subTest(position=index), self.assertRaisesRegex(observer.Refused, "reparse-point"):
                self.observe(records)

    def test_access_denied_refuses_at_each_position(self):
        for index in range(3):
            records = self.chain()
            records[index] = PermissionError("synthetic-denial")
            with self.subTest(position=index), self.assertRaisesRegex(observer.Refused, "unobservable-path"):
                self.observe(records)

    def test_nonwindows_refuses_before_observation(self):
        root = Path("synthetic-owned-root")
        with patch.object(observer.sys, "platform", "linux"), patch.object(Path, "lstat", side_effect=AssertionError("real observation forbidden")):
            with self.assertRaisesRegex(observer.Refused, "windows-only"):
                observer.observe_regular_chain(root, ("folder", "leaf.txt"))

if __name__ == "__main__":
    unittest.main()
