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
    "docs/CHAD-ISSUE-TO-MAIN.md",
    "examples/chad-issue-to-main/README.md",
    "examples/chad-issue-to-main/THREE-SLICE-EXAMPLE.md",
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

    def test_partial_slice_examples_reference_parent_without_closing_it(self):
        # Checks only these teaching drafts, not GitHub's complete parser or lifecycle.
        text = (ROOT / "examples/chad-issue-to-main/THREE-SLICE-EXAMPLE.md").read_text(encoding="utf-8")
        drafts = re.findall(r"```text\n(.*?)\n```", text, re.DOTALL)
        self.assertEqual(len(drafts), 3)
        closing_parent = re.compile(
            r"\b(?:close[sd]?|fix(?:es|ed)?|resolve[sd]?)\s*:?\s*"
            r"(?:mshamblin5150-code/assimilation)?#9\b", re.IGNORECASE)
        for number, draft in enumerate(drafts[:2], 1):
            with self.subTest(slice=number):
                self.assertTrue(draft.startswith(f"Title: Part {number} of issue #9"))
                self.assertNotRegex(draft, closing_parent)
                self.assertIn("Remaining:", draft)
                self.assertIn("expected parent state OPEN", draft)
        # Even the unaccepted final template must not contain an active directive.
        self.assertNotRegex(drafts[2], closing_parent)
        self.assertIn("NOT RUN / NOT ACCEPTED", drafts[2])

    def test_slice_example_is_reachable_from_lesson_and_local_worksheet(self):
        lesson = (ROOT / "docs/CHAD-ISSUE-TO-MAIN.md").read_text(encoding="utf-8")
        worksheet = (ROOT / "examples/chad-issue-to-main/README.md").read_text(encoding="utf-8")
        self.assertIn("../examples/chad-issue-to-main/THREE-SLICE-EXAMPLE.md", lesson)
        self.assertIn("THREE-SLICE-EXAMPLE.md", worksheet)


if __name__ == "__main__":
    unittest.main()
