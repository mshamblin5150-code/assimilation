# Clinical spelling scanner port handoff

Task received 2026-10-29; bounded cloud worker for Vox/Assimilation.
Target: `mshamblin5150-code/assimilation`, base main
`3a4fca9b5bcc998f97e30af7701db50deac7918c`.
Branch: `port/clinical-spelling-scan`. Never merge without parent confirmation.

## Authorized specification

Matt requested copying the actual Clinical Skills `tools/spelling_scan.py` from
commit `5f5be786eedca65a5c1a74bdf409b59bf6085b34`, blob
`093d374364c1459c7b0a84d5318a53ca6d0db71c`.
He subsequently approved self-contained dependency adaptation and repeatable,
scoped tests/CI preventing listed British forms in Assimilation-owned writing.
Preserve table/stem/drug vocabulary, bounded matching, Markdown mentions,
counted Python declarations, safe diagnostics and unreadable-input refusal.
Keep reports/hooks advisory. Exclude verbatim upstream sources, licenses,
generated vendor content and immutable evaluation evidence from enforcement.
Copy no Clinical fixtures/PHI and do not alter Clinical working files. Branch
push and draft PR are authorized, subject to tool approval; merging is not.

## Capability and source evidence

Normal supported cloud Git clone succeeded. Target origin/default branch and
main SHA verified; connected GitHub account is `mshamblin5150-code`, matching
repository owner, with push permission. No local machine access was used.
Clinical working tree was clean at `3280549862a1adbfad21c8f999e5aff4bff166cb`.
Fetched the exact source commit into Clinical Git metadata without checking it
out or changing its working files. Read only named tooling/tests, repository
instructions and relevant spelling skill section; no patient corpus read and
no Clinical workflow/hook installed or run.

Read target AGENTS.md, README.md, START_HERE.md, docs/DOCTRINE.md,
docs/SWARMS.md, and original implement/code-review skills under
`upstream/matt-pocock/skills/engineering/`. No `.agents/skills` installation or
`docs/agents/issue-tracker.md` exists. This bounded request supplies the spec;
no tracker setup or issue publication was needed. The review skill is applied
procedurally using actual review agents rather than an unavailable Skill tool.

## Implementation and licensing

Files: `scripts/spelling_scan.py`, `tests/test_spelling_scan.py`,
`docs/SPELLING_SCAN.md`, README link, THIRD_PARTY_NOTICES addition, this handoff.
Actual matching/mention source copied, helper responsibilities adapted into one
stdlib script. CLI findings exit 0, refusal exits 2; scoped normal unittest
regression is the enforcement surface. No workflow permission change or hook.

Full provenance/helper blob IDs and exact scope are in docs/SPELLING_SCAN.md.
Source tree contained no license file. Matt's explicit copying authorization is
recorded; no public upstream license grant or new authorship is invented.
Broader downstream redistribution licensing remains unresolved and must be
settled by the source owner before treating the derived scanner as MIT licensed.
Existing snapshots/licenses remain byte-identical.

## Verification status

Focused scanner tests: 15 passed after tracked-file regression included the new
files. Covers all 37 entries/counterparts, bounded and deliberately missed forms,
mentions, counts, staged vs unstaged bytes, quoted filenames, scope pruning,
evidence separation, unreadable/invalid/NUL inputs, links, and safe diagnostics.
`python scripts/spelling_scan.py --all`: exit 0, no listed maintained uses,
46 text files read, 914 paths excluded after adding this handoff.
`python scripts/snapshot_sources.py verify`: passed both upstream snapshots.
The cloud checkout initially used 0600/0700 permissions due to its umask; restored
Git-recorded 0644/0755 checkout modes for the pre-existing snapshot verifier.
No upstream content changes were made.

The first full-suite attempt (135 tests) failed because temporary checkout
fixtures inherited cloud umask 077. Rerun with standard umask 022 passed all
135 tests. Final full-suite rerun after the review fix: **136 passed in 41.500s**.
Command (with umask 022):
`GIT_ALLOW_PROTOCOL=file GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null python -m unittest discover -s tests -v`.
Full local log: `/tmp/assimilation-tests-final.log`.
`--record`: exit 0, 97 evaluation text files read, no listed historical forms.
Default staged command and `--all`: exit 0; final snapshot verification passed.

## Independent review

Standards reviewer: `/root/standards_review`. Spec reviewer: `/root/spec_review`.
Both independently found filename-only symlinks bypassed regular-file checks.
Commit `c2d53879dd8df703a125bb68c21b713c49c48fa8` validates every selected path's
working-tree or index metadata before selecting contents, including `.txt`.
Each reviewer independently reran the 15-test focused suite and confirmed the
finding closed with no remaining findings on its own axis. No reviewers edited
files or published anything. The injected-owned-prose test now invokes the actual
CI regression test and observes its failure while the advisory CLI returns 0.

Source equivalence: independent Spec review verified all nine vocabulary/pattern
assignments and seven matching/mention/rendering AST definitions match the pinned
Clinical source exactly. No private corpus was used.

## Next safe action

Implementation and verification are complete. Authorized publication is one
reviewed branch push and one draft PR, with results/URL delivered to parent.
The implementation reviewed by both agents is `c2d53879dd8df703a125bb68c21b713c49c48fa8`;
subsequent changes only finalize this handoff's evidence.
No merge; licensing grant and final candidate eligibility remain parent/owner
choices. No denied or uncertain remote mutation has occurred.
