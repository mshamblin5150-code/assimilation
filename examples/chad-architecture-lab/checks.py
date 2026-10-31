"""Behavior checks at preview(folder); no mocks of internal implementation."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys

sys.dont_write_bytecode = True

STAGES = ("01-start", "02-category", "03-tangled", "04-deepened", "05-casefold")
ROOT = Path(__file__).resolve().parent


def load_stage(stage):
    if stage not in STAGES:
        raise ValueError("Choose a named teaching stage")
    return load_source(ROOT / "stages" / stage / "preview.py")


def load_source(path):
    spec = importlib.util.spec_from_file_location("teaching_preview", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreviewContract(unittest.TestCase):
    stage = "01-start"
    preview_module = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="architecture-lab-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "garden.txt").write_bytes(b"Plant basil Saturday\n")
        (self.folder / "unknown.bin").write_bytes(b"synthetic bytes\x00")
        self.preview = (self.preview_module or load_stage(self.stage)).preview

    def test_text_and_unknown_plan(self):
        self.assertEqual(self.preview(self.folder)["rows"], [
            {"source": "garden.txt", "category": "Text", "destination": "Text/garden.txt"},
            {"source": "unknown.bin", "category": "Keep", "destination": None},
        ])

    def test_preview_preserves_files_and_ignores_directories(self):
        (self.folder / "nested").mkdir()
        (self.folder / "nested" / "inside.txt").write_bytes(b"Leave nested file\n")
        self.assertEqual(self.preview(self.folder)["rows"], [
            {"source": "garden.txt", "category": "Text", "destination": "Text/garden.txt"},
            {"source": "unknown.bin", "category": "Keep", "destination": None},
        ])
        self.assertEqual(sorted(p.relative_to(self.folder).as_posix()
                                for p in self.folder.rglob("*")),
                         ["garden.txt", "nested", "nested/inside.txt", "unknown.bin"])
        self.assertEqual((self.folder / "garden.txt").read_bytes(), b"Plant basil Saturday\n")
        self.assertEqual((self.folder / "unknown.bin").read_bytes(), b"synthetic bytes\x00")
        self.assertEqual((self.folder / "nested/inside.txt").read_bytes(), b"Leave nested file\n")

    def test_jpg_has_an_image_destination(self):
        (self.folder / "photo.jpg").write_bytes(b"invented image")
        self.assertEqual(self.preview(self.folder)["rows"], [
            {"source": "garden.txt", "category": "Text", "destination": "Text/garden.txt"},
            {"source": "photo.jpg", "category": "Images", "destination": "Images/photo.jpg"},
            {"source": "unknown.bin", "category": "Keep", "destination": None},
        ], "JPG category is part of the proposed plan")

    def test_summary_counts_match_the_plan(self):
        (self.folder / "photo.jpg").write_bytes(b"invented image")
        result = self.preview(self.folder)
        self.assertEqual(result.get("counts"), {"Images": 1, "Keep": 1, "Text": 1},
                         "Summary counts describe the proposed plan")

    def test_later_preview_does_not_change_an_earlier_plan(self):
        first = self.preview(self.folder)
        other = self.folder / "other"
        other.mkdir()
        (other / "drawing.jpg").write_bytes(b"different synthetic image")
        self.assertEqual(self.preview(other), {"rows": [
            {"source": "drawing.jpg", "category": "Images", "destination": "Images/drawing.jpg"},
        ], "counts": {"Images": 1}})
        self.assertEqual(first, {"rows": [
            {"source": "garden.txt", "category": "Text", "destination": "Text/garden.txt"},
            {"source": "unknown.bin", "category": "Keep", "destination": None},
        ], "counts": {"Text": 1, "Keep": 1}}, "Earlier preview remains a stable plan")

    def test_uppercase_extensions_have_matching_rows_and_counts(self):
        (self.folder / "NOTES.TXT").write_bytes(b"Synthetic uppercase note")
        (self.folder / "PIC.JPG").write_bytes(b"Synthetic uppercase photo")
        self.assertEqual(self.preview(self.folder), {"rows": [
            {"source": "NOTES.TXT", "category": "Text", "destination": "Text/NOTES.TXT"},
            {"source": "PIC.JPG", "category": "Images", "destination": "Images/PIC.JPG"},
            {"source": "garden.txt", "category": "Text", "destination": "Text/garden.txt"},
            {"source": "unknown.bin", "category": "Keep", "destination": None},
        ], "counts": {"Text": 2, "Images": 1, "Keep": 1}},
            "Uppercase extensions agree in rows and summary")


def suite(stage, names, preview_module=None):
    case = type("StageContract", (PreviewContract,), {
        "stage": stage, "preview_module": preview_module})
    allowed = unittest.defaultTestLoader.getTestCaseNames(case)
    if not names or any(name not in allowed for name in names):
        raise ValueError("Choose exact existing test names")
    return unittest.TestSuite(case(name) for name in names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--case", action="append", required=True,
                        help="Exact test name; repeat for multiple checks")
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(suite(args.stage, args.case))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
