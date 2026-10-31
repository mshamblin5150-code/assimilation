import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import organizer as o

class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "practice"; self.root.mkdir()
        (self.root / "garden.txt").write_text("Plant basil Saturday", encoding="utf-8")
        (self.root / "unknown.bin").write_bytes(b"synthetic")
        self.log = self.base / "actions.jsonl"
        self.plan = o.preview(self.root)
    def apply(self):
        o.apply(self.plan, self.plan["id"], self.log)
    def test_preview_is_exact_and_read_only(self):
        self.assertEqual(o.preview(self.root), self.plan)
        self.assertEqual(len(list(self.root.iterdir())), 2)
        self.assertEqual(self.plan["files"][0]["destination"], "Text/garden.txt")
        self.assertIsNone(self.plan["files"][1]["destination"])
    def test_wrong_approval(self):
        with self.assertRaises(ValueError): o.apply(self.plan, "yes", self.log)
        self.assertFalse(self.log.exists())
    def test_tampered_preview(self):
        self.plan["files"][0]["destination"] = "../escape.txt"
        with self.assertRaises(ValueError): self.apply()
    def test_changed_after_preview(self):
        (self.root / "garden.txt").write_text("Changed")
        with self.assertRaises(ValueError): self.apply()
        self.assertFalse(self.log.exists())
    def test_added_after_preview(self):
        (self.root / "new.txt").write_text("Added")
        with self.assertRaises(ValueError): self.apply()
    def test_collision_preserves_both(self):
        (self.root / "Text").mkdir()
        dst = self.root / "Text/garden.txt"; dst.write_text("Existing")
        with self.assertRaises(FileExistsError): self.apply()
        self.assertEqual(dst.read_text(), "Existing")
        self.assertTrue((self.root / "garden.txt").exists())
    def test_move_and_repeatable_undo(self):
        self.apply(); self.assertTrue((self.root / "Text/garden.txt").exists())
        self.assertTrue((self.root / "unknown.bin").exists())
        o.undo(self.log); o.undo(self.log)
        self.assertEqual(o.preview(self.root), self.plan)
    def test_stop_preserves_inputs(self):
        o.apply(self.plan, self.plan["id"], self.log, stop=lambda: True)
        self.assertTrue((self.root / "garden.txt").exists())
        self.assertIn('stopped', self.log.read_text())
        o.undo(self.log)
    def test_interrupt_after_rename_before_ack(self):
        real = o.append
        def interrupt(log, record):
            if record["event"] == "moved": raise KeyboardInterrupt()
            real(log, record)
        with patch.object(o, "append", interrupt):
            with self.assertRaises(KeyboardInterrupt): self.apply()
        o.undo(self.log)
        self.assertTrue((self.root / "garden.txt").exists())
    def test_undo_conflict_preserves_files(self):
        self.apply()
        (self.root / "garden.txt").write_text("New original")
        with self.assertRaises(ValueError): o.undo(self.log)
        self.assertTrue((self.root / "Text/garden.txt").exists())
        self.assertEqual((self.root / "garden.txt").read_text(), "New original")
    def test_undo_changed_destination(self):
        self.apply(); (self.root / "Text/garden.txt").write_text("Edited")
        with self.assertRaises(ValueError): o.undo(self.log)
        self.assertEqual((self.root / "Text/garden.txt").read_text(), "Edited")
    def test_existing_journal_is_preserved(self):
        self.log.write_text("Keep")
        with self.assertRaises(FileExistsError): self.apply()
        self.assertEqual(self.log.read_text(), "Keep")
    def test_torn_tail_recovery_preserves_evidence(self):
        self.apply()
        with self.log.open("ab") as f: f.write(b'{"event":')
        original = self.log.read_bytes()
        recovered = self.base / "recovered.jsonl"
        o.recover_journal(self.log, recovered)
        o.undo(recovered)
        self.assertEqual(self.log.read_bytes(), original)
        self.assertTrue((self.root / "garden.txt").exists())
    def test_malformed_interior_recovery_refused(self):
        self.apply()
        self.log.write_bytes(self.log.read_bytes() + b'bad\npartial')
        with self.assertRaises(ValueError): o.recover_journal(self.log, self.base / "recovered")
    def test_collision_appearing_after_preflight(self):
        real = o.rename_new
        def collide(src, dst):
            dst.write_text("Racing file")
            real(src, dst)
        with patch.object(o, "rename_new", collide):
            with self.assertRaises(FileExistsError): self.apply()
        self.assertEqual((self.root / "Text/garden.txt").read_text(), "Racing file")
        self.assertTrue((self.root / "garden.txt").exists())
    def test_stop_after_first_move_then_undo(self):
        (self.root / "picnic.md").write_text("Bring sandwiches")
        self.plan = o.preview(self.root)
        calls = iter([False, True])
        o.apply(self.plan, self.plan["id"], self.log, stop=lambda: next(calls))
        self.assertTrue((self.root / "Text/garden.txt").exists())
        self.assertTrue((self.root / "picnic.md").exists())
        o.undo(self.log)
        self.assertEqual(o.preview(self.root), self.plan)
    def test_category_path_occupied_by_file_refuses_before_journal(self):
        (self.root / "Text").write_text("Preserve category blocker")
        self.plan = o.preview(self.root)
        with self.assertRaises(NotADirectoryError): self.apply()
        self.assertFalse(self.log.exists())
        self.assertEqual((self.root / "Text").read_text(), "Preserve category blocker")
        self.assertEqual((self.root / "garden.txt").read_text(), "Plant basil Saturday")
    def test_path_escape(self):
        with self.assertRaises(ValueError): o.safe(self.root, "../escape")

if __name__ == "__main__": unittest.main()
