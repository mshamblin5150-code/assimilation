"""Advisory scan of Assimilation-owned writing for a bounded spelling list.

Derived from Clinical Skills tools/spelling_scan.py, commit
5f5be786eedca65a5c1a74bdf409b59bf6085b34, blob
093d374364c1459c7b0a84d5318a53ca6d0db71c, copied with Matt Shamblin's
explicit authorization. See docs/SPELLING_SCAN.md for provenance, scope,
license limits, and the separate CI regression check. No hooks are installed.
"""
from __future__ import annotations

import argparse
import ast
import io
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tokenize
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# spelling-scan: mentions 31
TABLE = {
    "dyspnoea": "dyspnea",
    "apnoea": "apnea",
    "anaemia": "anemia",
    "haemoglobin": "hemoglobin",
    "oedema": "edema",
    "diarrhoea": "diarrhea",
    "paediatric": "pediatric",
    "caesarean": "cesarean",
    "sulphate": "sulfate",
    "nebuliser": "nebulizer",
    "catheterise": "catheterize",
    "millilitre": "milliliter",
    "centimetre": "centimeter",
    "litre": "liter",
    "fibre": "fiber",
    "grey": "gray",
    "behaviour": "behavior",
    "favour": "favor",
    "colour": "color",
    "tumour": "tumor",
    "labelled": "labeled",
    "programme": "program",
    "licence": "license",
    "neighbour": "neighbor",
    "judgement": "judgment",
    "manoeuvre": "maneuver",
    "counselling": "counseling",
    "millimetre": "millimeter",
    "hypoxaemia": "hypoxemia",
    "immobilisation": "immobilization",
    "cancelled": "canceled",
}


# spelling-scan: mentions 3
STEM_CHANGES = {
    "labelling": "labeling",
    "catheterisation": "catheterization",
    "hypoxaemic": "hypoxemic",
}


FORMS = {**TABLE, **STEM_CHANGES}


# spelling-scan: mentions 3
DRUGS = {
    "paracetamol": "acetaminophen",
    "adrenaline": "epinephrine",
    "salbutamol": "albuterol",
}


ALL_FORMS = {**FORMS, **DRUGS}


_SUFFIX = r"(?:ally|ing|es|ed|al|ly|s|d)?"


_PATTERNS = tuple(
    (form, american, re.compile(
        r"(?<![A-Za-z0-9])" + re.escape(form) + _SUFFIX + r"(?![A-Za-z0-9])",
        re.I,
    ))
    for form, american in ALL_FORMS.items()
)


_CODE_SPAN = re.compile(r"`+[^`\n]*`+")


_PYTHON_MENTION = re.compile(r"#\s*spelling-scan:\s*mentions\s+(\d+)\s*$")


class Finding(NamedTuple):
    path: str
    line: int
    form: str
    american: str

    def render(self) -> str:
        if self.line == 0:
            return f"  {self.path}  {self.form} -> {self.american}"
        return f"  {self.path}:{self.line}  {self.form} -> {self.american}"


def strip_code_spans(line: str) -> str:
    """The line with every backticked span blanked out.

    Replaced with a space rather than removed, so two spans cannot be spliced
    into a word that was never written.
    """
    return _CODE_SPAN.sub(" ", line)


# spelling-scan: mentions 2
def _matches(line: str) -> list[tuple[str, str]]:
    """``(form, american)`` for the line, in the order they are written.

    Overlapping matches keep the longer, which is what stops a form that
    contains another from being reported twice. Nothing in the table does today
    -- ``litre`` inside ``millilitre`` is excluded by the word boundary -- and
    the guard is here because the table grows.
    """
    found = []
    for form, american, pattern in _PATTERNS:
        for match in pattern.finditer(line):
            found.append((match.start(), match.end(), form, american))

    found.sort(key=lambda item: (item[0], -item[1]))
    kept: list[tuple[str, str]] = []
    reach = -1
    for start, end, form, american in found:
        if start < reach:
            continue
        kept.append((form, american))
        reach = end
    return kept


def _scan_text(text: str, path: str, mentions: bool) -> list[Finding]:
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        scanned = strip_code_spans(line) if mentions else line
        for form, american in _matches(scanned):
            findings.append(Finding(path, number, form, american))
    return findings


def scan_text(text: str, path: str) -> list[Finding]:
    """Scan Markdown-style text, where backticks distinguish a mention."""
    return _scan_text(text, path, mentions=True)


class MentionDeclarationError(ValueError):
    """A Python mention declaration is detached, ambiguous, or miscounted."""


def scan_python_text(text: str, path: str) -> list[Finding]:
    """Scan Python while honoring counted declarations on exact AST statements."""
    findings = _scan_text(text, path, mentions=False)
    source_lines = text.splitlines()
    declarations = [
        (token.start[0], matched)
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type == tokenize.COMMENT
        if not source_lines[token.start[0] - 1][:token.start[1]].strip()
        for matched in [_PYTHON_MENTION.fullmatch(token.string)]
        if matched
    ]
    if not declarations:
        return findings

    tree = ast.parse(text, filename=path)
    statements: dict[int, list[ast.stmt]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            statements.setdefault(node.lineno, []).append(node)

    exempt_lines: set[int] = set()
    declared_statements: set[tuple[int, int]] = set()
    for declaration_line, declaration in declarations:
        candidates = statements.get(declaration_line + 1, [])
        if len(candidates) != 1:
            raise MentionDeclarationError(
                f"{path}:{declaration_line}: mention declaration must be directly "
                "above exactly one Python statement"
            )
        statement = candidates[0]
        end_line = getattr(statement, "end_lineno", statement.lineno)
        declared = int(declaration.group(1))
        if declared < 1:
            raise MentionDeclarationError(
                f"{path}:{declaration_line}: mention declaration count must be positive"
            )
        statement_span = (statement.lineno, end_line)
        if statement_span in declared_statements:
            raise MentionDeclarationError(
                f"{path}:{declaration_line}: statement already has a mention declaration"
            )
        declared_statements.add(statement_span)
        covered = [f for f in findings if statement.lineno <= f.line <= end_line]
        if len(covered) != declared:
            raise MentionDeclarationError(
                f"{path}:{declaration_line}: declares {declared} mentions but "
                f"the statement contains {len(covered)}"
            )
        exempt_lines.update(range(statement.lineno, end_line + 1))

    return [finding for finding in findings if finding.line not in exempt_lines]



class InputError(ValueError):
    """The selected population could not be read unambiguously."""


class Report(NamedTuple):
    findings: list[Finding]
    evidence: list[Finding]
    files_read: int
    excluded: int


# Positive ownership boundary. New top-level areas require a deliberate decision.
MAINTAINED_ROOTS = {"docs", "skills", "scripts", "tests"}
EXCLUDED_PARTS = {
    ".git", ".agents", ".claude", "upstream", "vendor", "node_modules",
    "__pycache__", ".venv", "venv", "generated", "dist", "build",
}
# spelling-scan: mentions 1
LICENSE_NAMES = {"license", "licence", "copying", "notice", "third_party_notices"}


def repository_path(path: str | Path) -> str:
    """Normalize lexically without following a link or leaving the checkout."""
    candidate = Path(os.path.abspath(REPO_ROOT / path))
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError:
        raise InputError("explicit path is outside the checkout") from None
    if any(0xD800 <= ord(char) <= 0xDFFF or ord(char) < 32 for char in str(relative)):
        raise InputError("path has ambiguous or control-character bytes")
    return relative.as_posix()


def is_evidence(path: str) -> bool:
    return Path(path).parts[:1] == ("evals",)


def is_maintained(path: str) -> bool:
    parts = Path(path).parts
    if not parts or any(part in EXCLUDED_PARTS for part in parts):
        return False
    if Path(path).stem.lower() in LICENSE_NAMES or re.match(
        r"^(?:licen[sc]e|copying|notice)[._-]", Path(path).name.lower()
    ):
        return False
    return (len(parts) == 1 and Path(path).suffix.lower() == ".md") or (
        parts[0] in MAINTAINED_ROOTS
    )


def is_scannable_source(path: str) -> bool:
    return Path(path).suffix.lower() in {".md", ".py"}


def git_bytes(*args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args], capture_output=True, check=False,
        )
    except OSError:
        raise InputError("Git could not be started; population unread") from None
    if result.returncode:
        raise InputError("Git could not read the selected population")
    return result.stdout


def decode_text(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise InputError("input is not unambiguous UTF-8; population unread") from None
    if "\0" in text:
        raise InputError("NUL in text input; population unread")
    return text


def git_paths(*args: str) -> list[str]:
    # Adapted from Clinical tools/git_paths.py: split NUL records before decoding.
    data = git_bytes(*args)
    if data and not data.endswith(b"\0"):
        raise InputError("Git returned an incomplete path population")
    return [repository_path(decode_text(item)) for item in data.split(b"\0") if item]


def tracked_files() -> list[str]:
    return git_paths("ls-files", "-z")


def staged_paths() -> list[str]:
    return git_paths("diff", "--cached", "-z", "--name-only", "--diff-filter=ACMR")


def check_no_links(path: str):
    # Adapted from Clinical tools/tree_walk.py's symlink/reparse-point boundary.
    full = REPO_ROOT
    info = full.lstat()
    for part in Path(path).parts:
        full /= part
        try:
            info = full.lstat()
        except OSError:
            raise InputError("selected input is unreadable; population incomplete") from None
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise InputError("selected input reaches a link or junction; population incomplete")
    return info


def check_ordinary_path(path: str) -> None:
    info = check_no_links(path)
    if not stat.S_ISREG(info.st_mode):
        raise InputError("selected input is not an ordinary file")


def read_file(path: str) -> str:
    check_ordinary_path(path)
    try:
        return decode_text((REPO_ROOT / path).read_bytes())
    except OSError:
        raise InputError("selected input is unreadable; population incomplete") from None


def read_staged(path: str) -> str:
    metadata = git_bytes("ls-files", "--stage", "-z", "--", path)
    if not metadata.startswith(b"100644 ") and not metadata.startswith(b"100755 "):
        raise InputError("selected index input is not an ordinary unambiguous file")
    if len(metadata.split(b"\0")) != 2:
        raise InputError("selected index input is ambiguous")
    return decode_text(git_bytes("show", f":{path}"))


def path_findings(path: str, text: str | None) -> list[Finding]:
    findings = [Finding(path, 0, form, american) for form, american in _matches(path)]
    if text is not None:
        try:
            scanner = scan_python_text if path.lower().endswith(".py") else scan_text
            findings.extend(scanner(text, path))
        except (SyntaxError, tokenize.TokenError, MentionDeclarationError, ValueError):
            # Parser exceptions can contain source lines. Never echo their payload.
            raise InputError(f"{path}: Python input or mention declaration is ambiguous; not graded") from None
    return findings


def scan(paths, read=read_file, *, records: bool = False, added_lines=None) -> Report:
    findings, evidence = [], []
    read_count = excluded = 0
    for raw_path in sorted(set(paths)):
        path = repository_path(raw_path)
        selected = is_evidence(path) if records else is_maintained(path)
        if not selected:
            excluded += 1
            continue
        text = read(path) if is_scannable_source(path) else None
        if text is not None:
            read_count += 1
        hits = path_findings(path, text)
        if records:
            evidence.extend(hits)
        else:
            findings.extend(hit for hit in hits if (
                added_lines is None or hit.line == 0 or hit.line in added_lines.get(path, set())
            ))
    return Report(findings, evidence, read_count, excluded)


def staged_additions(paths: list[str]) -> dict[str, set[int]]:
    """Keep source added-line semantics; per-path diffs avoid quoted-name parsing."""
    additions = {}
    for path in paths:
        if not is_maintained(path) or not is_scannable_source(path):
            continue
        diff = decode_text(git_bytes(
            "diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color",
            "--unified=0", "--", path,
        ))
        additions[path] = set()
        for line in diff.splitlines():
            if line.startswith("@@"):
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
                if not match:
                    raise InputError("ambiguous staged diff; population unread")
                start, count = int(match[1]), int(match[2] or 1)
                additions[path].update(range(start, start + count))
    return additions


def scan_staged() -> Report:
    paths = staged_paths()
    return scan(paths, read_staged, added_lines=staged_additions(paths))


def files_under(targets: list[Path]) -> list[str]:
    """Walk only owned roots, pruning excluded material before opening it."""
    found = []
    pending = [repository_path(path) for path in targets]
    while pending:
        path = pending.pop()
        if path != "." and not is_maintained(path):
            raise InputError("explicit target is outside maintained writing scope")
        full = REPO_ROOT / path
        info = check_no_links(path)
        if stat.S_ISDIR(info.st_mode):
            try:
                with os.scandir(full) as entries:
                    children = [repository_path(entry.path) for entry in entries]
            except OSError:
                raise InputError("directory unreadable; population incomplete") from None
            pending.extend(child for child in children if is_maintained(child))
        else:
            check_ordinary_path(path)
            found.append(path)
    return found


def vocabulary_covered() -> str:
    return (
        f"spelling-scan: checked {len(_PATTERNS)} listed forms and bounded inflections "
        f"({len(TABLE)} table rows, {len(STEM_CHANGES)} stem changes, {len(DRUGS)} drug names). "
        "Unlisted forms are not detected."
    )


def render(report: Report, quiet: bool, mode: str) -> list[str]:
    if quiet and not report.findings and not report.evidence:
        return []
    lines = ["spelling-scan: report only; findings do not fail this command."]
    lines.extend(finding.render() for finding in report.findings)
    if report.evidence:
        lines.append(f"spelling-scan: {len(report.evidence)} historical occurrences; evidence only, never findings.")
        lines.extend(finding.render() for finding in report.evidence)
    elif not report.findings:
        lines.append("spelling-scan: no listed form found in the selected population.")
    lines.append(
        f"spelling-scan: {mode}; {report.files_read} text files read; "
        f"{report.excluded} paths excluded. See docs/SPELLING_SCAN.md for the ownership boundary."
    )
    lines.append(vocabulary_covered())
    return lines


def _main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--all", action="store_true", help="tracked maintained writing, working-tree bytes")
    modes.add_argument("--record", action="store_true", help="report tracked evaluation evidence separately")
    modes.add_argument("--commit-message", type=Path, help="report on an explicitly supplied UTF-8 message")
    parser.add_argument("--quiet", action="store_true", help="suppress an empty report")
    args = parser.parse_args(argv)
    if args.paths and (args.all or args.record or args.commit_message):
        parser.error("paths cannot be combined with another population")
    if args.commit_message:
        path = repository_path(args.commit_message)
        report = Report(scan_text(read_file(path), path), [], 1, 0)
        mode = "supplied commit message only"
    elif args.paths:
        report = scan(files_under(args.paths))
        mode = "explicit maintained paths; .md/.py contents and filenames"
    elif args.all or args.record:
        report = scan(tracked_files(), records=args.record)
        mode = "tracked evaluation evidence only" if args.record else "tracked maintained .md/.py contents and filenames; untracked files unread"
    else:
        report = scan_staged()
        mode = "staged maintained .md/.py added lines and filenames; unstaged/untracked bytes unread"
    for line in render(report, args.quiet, mode):
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except InputError as exc:
        print(f"spelling-scan: {exc}. No complete result.", file=sys.stderr)
        return 2


def use_utf8() -> None:
    """Adapted from Clinical console_codec.use_utf8; command path only."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError, LookupError):
                try:
                    reconfigure(errors="replace")
                except (ValueError, OSError, LookupError):
                    pass


if __name__ == "__main__":
    use_utf8()
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr)
        sys.exit(2)
    sys.exit(main())
