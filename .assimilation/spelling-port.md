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

Focused scanner tests: 14 passed after tracked-file regression included the new
files. Covers all 37 entries/counterparts, bounded and deliberately missed forms,
mentions, counts, staged vs unstaged bytes, quoted filenames, scope pruning,
evidence separation, unreadable/invalid/NUL inputs, links, and safe diagnostics.
`python scripts/spelling_scan.py --all`: exit 0, no listed maintained uses,
46 text files read, 913 paths excluded at this point.
`python scripts/snapshot_sources.py verify`: passed both upstream snapshots.
The cloud checkout initially used 0600/0700 permissions due to its umask; restored
Git-recorded 0644/0755 checkout modes for the pre-existing snapshot verifier.
No upstream content changes were made.

Full suite and independent review are pending; update before delivery.
