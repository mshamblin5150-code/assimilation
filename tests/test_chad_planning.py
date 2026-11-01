"""Reader-facing documentation integrity, not agent/runtime safety proof."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / 'docs' / 'CHAD-PLANNING.md'


def headings(markdown):
    """Slugs for the plain-text headings used by this lesson's linked sections."""
    result = set()
    for heading in re.findall(r'^#{1,6}\s+(.+)$', markdown, re.MULTILINE):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        result.add(slug)
    return result


class PlanningLessonTests(unittest.TestCase):
    def test_reader_can_open_lesson_and_follow_local_references(self):
        self.assertTrue(LESSON.is_file(), 'The planning lesson must be readable.')
        lesson = LESSON.read_text(encoding='utf-8')
        links = re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', lesson)
        self.assertTrue(links, 'Readers need links to the actual source skills.')
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (LESSON.parent / unquote(parsed.path)).resolve() if parsed.path else LESSON
            with self.subTest(link=link):
                self.assertTrue(target.is_relative_to(ROOT), 'Local link leaves the repository.')
                self.assertTrue(target.exists(), f'Broken reader link: {link}')
                if parsed.fragment:
                    self.assertIn(unquote(parsed.fragment), headings(target.read_text(encoding='utf-8')))

    def test_readiness_answer_key_keeps_three_gates_separate(self):
        lesson = LESSON.read_text(encoding='utf-8')
        rows = {}
        for line in lesson.splitlines():
            if line.startswith('| '):
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                rows[cells[0]] = cells[1:]
        # Independent answers derived from the approved three-gate lesson scope.
        expected = {
            'Unanswered product choice': ['No', 'Unknown', 'Yes', 'No'],
            'Ready but dependency-blocked': ['Yes', 'No', 'Yes', 'No'],
            'Ready but permission-held': ['Yes', 'Yes', 'No', 'No'],
            'Ready and eligible': ['Yes', 'Yes', 'Yes', 'Yes'],
            'Blocker closed as duplicate; outcome unknown': ['Yes', 'Unknown', 'Yes', 'No'],
            'Human-only manual verification': ['Yes', 'Yes', 'Human only', 'No'],
            'Wayfinder decision question': ['Not a build ticket', 'N/A', 'No', 'No'],
        }
        for case, answers in expected.items():
            with self.subTest(case=case):
                self.assertIn(case, rows, 'The reader needs this readiness counterexample.')
                self.assertEqual(rows[case], answers)

    def test_workflow_reader_can_find_planning_lesson(self):
        workflow = (ROOT / 'docs' / 'WORKFLOW.md').read_text(encoding='utf-8')
        links = re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', workflow)
        self.assertIn('CHAD-PLANNING.md', links)


if __name__ == '__main__':
    unittest.main()
