"""Synthetic name-only tests; no Windows filesystem qualification or install."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from windows_view_names import validate_view_names


class WindowsViewNamesTests(unittest.TestCase):
    def test_valid_names_and_normalized_keys(self):
        self.assertEqual(validate_view_names(["docs/Readme.txt", "src/tool-1.py"]),
                         ("docs/readme.txt", "src/tool-1.py"))

    def test_refuse_case_insensitive_collision(self):
        with self.assertRaisesRegex(ValueError, "casefold-collision"):
            validate_view_names(["Docs/File.txt", "docs/file.TXT"])

    def test_refuse_file_directory_conflict_in_either_order(self):
        for paths in (["a", "a/b.txt"], ["A/B.txt", "a"]):
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, "file-directory-collision"):
                validate_view_names(paths)

    def test_refuse_unsafe_components(self):
        bad = ("../secret", "/root", "a//b", "a/./b", "a/../b",
               "CON", "con.txt", "LPT1.log", "COM9", "NUL", "AUX",
               "foo.", "a:b", "a\\b", "a?b", "a*b", "a|b",
               "a<b", 'a"b', "a>b", "a b", "é.txt", "x\x00y")
        for path in bad:
            with self.subTest(path=repr(path)), self.assertRaises(ValueError):
                validate_view_names([path])

    def test_refuse_invalid_and_oversized_manifest(self):
        for paths in (None, "a.txt", [None], [""], ["a" * 121],
                      ["a/" * 65 + "b"], ["x"] * 20001):
            with self.subTest(kind=str(type(paths))), self.assertRaises(ValueError):
                validate_view_names(paths)

    def test_does_not_touch_filesystem(self):
        from unittest.mock import patch
        with patch("os.stat", side_effect=AssertionError("no filesystem")), \
             patch("os.listdir", side_effect=AssertionError("no filesystem")):
            self.assertEqual(validate_view_names(["Safe/file.txt"]),
                             ("safe/file.txt",))


if __name__ == "__main__":
    unittest.main()
