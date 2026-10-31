"""Reader navigation and fixture structure, not skill-install or AI-behavior proof."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    "docs/CHAD-BLANK-PROJECT.md",
    "docs/CHAD-ADVERSARIAL-REVIEW.md",
    "docs/CHAD-SKILLS-MAINTENANCE.md",
    "docs/CHAD-LESSON-SOURCES.md",
)
LAB = ROOT / "examples/chad-adversarial-review"


def local_headings(text):
    return {
        re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
    }


class ProjectLessonTests(unittest.TestCase):
    def test_learner_can_follow_every_local_reference(self):
        for name in DOCS:
            page = ROOT / name
            text = page.read_text(encoding="utf-8")
            self.assertEqual(text.count("```") % 2, 0, name)
            for link in re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", text):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc:
                    continue
                target = (page.parent / unquote(parsed.path)).resolve() if parsed.path else page
                with self.subTest(page=name, link=link):
                    self.assertTrue(target.is_relative_to(ROOT))
                    self.assertTrue(target.exists(), "Reader link is missing")
                    if parsed.fragment:
                        self.assertIn(unquote(parsed.fragment), local_headings(target.read_text(encoding="utf-8")))

    def test_orientation_and_handoff_expose_both_lessons_and_scope_choice(self):
        for index, prefix in [("README.md", "docs/"), ("docs/HANDOFF.md", "")]:
            text = (ROOT / index).read_text(encoding="utf-8")
            links = re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", text)
            for name in ["CHAD-BLANK-PROJECT.md", "CHAD-ADVERSARIAL-REVIEW.md", "CHAD-SKILLS-MAINTENANCE.md"]:
                with self.subTest(index=index, target=name):
                    self.assertIn(prefix + name, links)

    def test_blind_review_inputs_and_instructor_key_are_separate(self):
        packet = (LAB / "TRUTH-PACKET.md").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^### (T\d) —", packet, re.MULTILINE), ["T1", "T2", "T3", "T4", "T5"])
        for name in ["FAULTY-DRAFT.md", "CLEAN-CONTROL.md", "INSTRUCTOR-KEY.md"]:
            self.assertTrue((LAB / name).is_file(), name)
        self.assertNotIn("INSTRUCTOR-KEY.md", packet)
        self.assertNotEqual((LAB / "FAULTY-DRAFT.md").read_bytes(), (LAB / "CLEAN-CONTROL.md").read_bytes())

    def test_both_scope_tracks_have_their_matching_monthly_command(self):
        # These are documented command contracts, not executions of those commands.
        text = (ROOT / "docs/CHAD-SKILLS-MAINTENANCE.md").read_text(encoding="utf-8")
        self.assertIn("npx skills@latest add mattpocock/skills -a codex --copy", text)
        self.assertIn("npx skills@latest add mattpocock/skills -g -a codex -a claude-code --copy", text)
        self.assertIn("npx skills@latest update -p", text)
        self.assertIn("npx skills@latest update -g", text)


if __name__ == "__main__":
    unittest.main()
