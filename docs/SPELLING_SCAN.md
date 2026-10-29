# Listed spelling regression check

`python3 scripts/spelling_scan.py --all` reports listed forms in tracked,
maintained Assimilation writing. With no arguments it reports added staged
lines and staged filenames, using index bytes rather than unstaged edits.
Explicit paths select maintained files/directories, including untracked files;
relative paths are resolved from the Assimilation checkout root.
`--commit-message <file>` reports only the supplied UTF-8 message.
`--quiet` suppresses an empty report.

The command is advisory: findings exit **0**. Unreadable input, links,
invalid UTF-8, NUL text, ambiguous Python mention declarations, or unavailable
Git populations exit **2**, with no complete clean result. No hooks are installed.
The original Clinical command returned 1 for findings; its hooks made that advisory
with `|| true`. This adaptation makes report-only behavior explicit in the CLI.

The ordinary test suite includes
`MaintainedWritingRegression.test_tracked_maintained_writing_has_no_listed_uses`.
It fails on findings in the bounded maintained population. Existing PR and monthly
workflows already discover this test through
`python3 -m unittest discover -s tests -v`; no new permissions or hook are needed.
This repeatable CI regression check implements Matt's clarified request to prevent
listed forms returning to Assimilation-owned writing.

## Ownership boundary

Enforcement reads tracked `.md` and `.py` contents and filenames under `docs/`,
`skills/`, `scripts/`, and `tests/`, plus root Markdown files. Non-Markdown/Python
contents are not read, though their filenames within those areas are checked.
Root license/notice files are excluded, including `THIRD_PARTY_NOTICES.md`.
License/notice basenames at any depth are excluded. Directories named `upstream`,
`vendor`, `node_modules`, `generated`, `dist`, `build`, `.git`, `.agents`, `.claude`,
`.venv`, `venv`, and `__pycache__` are excluded at any depth.

All `evals/` material is excluded from enforcement, including immutable fixtures,
recorded outputs and their historical summaries. Other root/configuration areas,
including `.github/`, lock files and snapshot manifests, are outside the owned
text population. Expanding this positive boundary requires a deliberate code and
test change. No snapshot, license, generated vendor file, or evaluation artifact
is edited by this tool. It never rewrites files.

`--record` is a separate, explicitly selected report of tracked `.md`/`.py`
evaluation contents and evaluation filenames. Its occurrences are historical
evidence, never findings, and it always exits 0 for readable inputs. It does not
assert that preserved output should be corrected. Record tallies change if the
instrument's vocabulary changes even while artifact bytes stay fixed.

`--all` reads working-tree bytes for tracked paths; staged mode checks added lines
and filenames from the index. Untracked files are outside both populations.
Explicit directory scans prune excluded directories before opening them. An
explicit excluded target is refused rather than presented as a clean scan.
Selected symlinks and junctions are refused, not followed. The filesystem walk is
a momentary read, not an atomic snapshot against concurrent replacement.

## Mentions, identifiers and vocabulary limits

In Markdown a same-line backtick span names a form without using it. This supports
quoted spellings, legitimate external identifiers and examples. Fenced block
contents remain scanned; they do not exempt a whole paragraph or file.
In Python, backticks have no exemption. A standalone
`# spelling-scan: mentions N` immediately above exactly one AST statement exempts
only that statement, and only when its listed occurrences equal positive `N`.
This supports exact intentional identifiers and test strings without exempting
neighboring code. Stale, detached and ambiguous declarations refuse the scan.
There is no blanket filename exemption for a maintained path.

The inherited vocabulary has **31 table entries, 3 stem changes, and 3 drug-name
forms**, with the inherited bounded suffix alternatives `ally|ing|es|ed|al|ly|s|d`.
It does not infer whole spelling families, detect every British form, validate
grammar, parse all Markdown quoting/link syntax, or check tickets and PR prose.
A clean result means no listed use on the selected surfaces. For example,
`organisation` is outside this list and is an intentional false-negative test.
Forms inside longer alphanumeric words are not matched; underscores and hyphens
retain the source's word separation behavior.

Findings print only repository paths, line numbers, and canonical table entries
with their replacements. They never print matched source lines or parser error
payloads. This is not a privacy scanner and does not authorize reading private data.

## Source and authorization

This is a port of actual source from
[`mshamblin5150-code/clinical-skills`](https://github.com/mshamblin5150-code/clinical-skills),
commit `5f5be786eedca65a5c1a74bdf409b59bf6085b34`, not an independently authored
replacement. `tools/spelling_scan.py` is Git blob
`093d374364c1459c7b0a84d5318a53ca6d0db71c`.
The table, regexes, matching, Markdown handling, Python token/AST mention handling,
and finding rendering were copied from that exact file. The source's named
helper responsibilities were folded into this self-contained standard-library
script: console UTF-8 setup, NUL-delimited Git path reading, and refusal to enter
links/reparse points. The portable Python floor is the existing Assimilation 3.10+.
Helper source blobs at that commit are `abeba2bf47f0b7d195a93f86159a2f68c5296de6`
(`console_codec.py`), `87eab5fd541c4f47052c5b6175c8b4d27b6aae61`
(`git_paths.py`), and `f7838fa52c65df87a2c06b40444469d669bbb888`
(`tree_walk.py`). The inspected source test blob is
`0605550941347d0c507b7077b3127d607522325f`.
Clinical repository hooks, patient/run selection, fixture paths and historical
commentary were removed. Strict input refusal, positive ownership selection,
per-path staged diff parsing, and explicit report-only CLI status are adaptations.

Synthetic tests were written here after inspecting source
`tools/test_spelling_scan.py` at the same commit, preserving its matching,
mention, staged, reporting and unreadable-input behavior seams. No Clinical
fixtures, patient corpus, reference databases, or account material were copied.

Matt Shamblin explicitly requested copying the file from Clinical Skills to
Assimilation, then approved a self-contained adaptation retaining its rules and
behavior and scoped repeatable CI enforcement. This authorization is recorded
from the delegated task on 2026-10-29. Inspection of the complete source commit's
tracked tree found no license file. Copy authorization is not an upstream public
license grant. The copied/derived scanner is **not silently relicensed** by
Assimilation's root MIT notice; authorship and redistribution terms for these
source-derived portions remain governed by the source owner's rights and explicit
authorization. A broader public redistribution license grant remains unresolved
and should be settled by the owner before public release. Existing upstream
snapshots and their licenses remain unchanged.
