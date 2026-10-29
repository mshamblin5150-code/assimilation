# Clinical spelling scanner port handoff

Current continuation (2026-10-29): parent opened existing PR #7 after exact
approval; parent reports hosted run `40878902649` passed 136 tests and snapshots.
Matt subsequently granted the narrow MIT licensing decision as recorded in
[the current provenance document](../docs/SPELLING_SCAN.md#source-and-authorization).
The initial hold, denial, and proposed body below are historical evidence, not
current instructions to reopen or duplicate the PR. This worker must not merge.

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
choices. The reviewed branch was successfully pushed and verified at
`1b02682109266f08704bacdc6e654223dd76de2d` before this final publication-status
record. No code changed after independent review.

Draft PR creation was **denied**, not pending or uncertain, by automatic approval
review through the GitHub connector. Target: public repository
`mshamblin5150-code/assimilation`, base `main`, head
`port/clinical-spelling-scan`, title “Port Clinical spelling scanner with scoped
owned-writing regression checks”. The rejection stated that public draft PR
publication and its detailed body lacked explicit user authorization. The parent
mission packet did authorize a draft PR, but auto-review did not accept that as
sufficient. No retry or alternate publication route was attempted; no PR is
claimed created. Obtain explicit authorization from Matt for the public draft PR
and its body before any retry. Branch push itself succeeded and was not denied.
The proposed PR description is retained below so approval can be concrete.


## Proposed draft PR body (not published)

## Summary

Port the actual Matt-authorized Clinical scanner from `5f5be786eedca65a5c1a74bdf409b59bf6085b34` (`093d374364c1459c7b0a84d5318a53ca6d0db71c`) as a self-contained standard-library tool. Preserve its 31 table entries, 3 stem changes, 3 drug forms, bounded inflections, and exact mention semantics.

```text
maintained first-party text → bounded matcher → advisory CLI report
                                           → normal unittest regression → existing CI
upstream / licenses / generated vendor / evals → excluded from enforcement
```

Provenance and precise coverage: `docs/SPELLING_SCAN.md`. No hooks installed or snapshot/license bytes changed. `--record` reports evaluation evidence separately.

## Evidence

- Before: no repeatable owned-writing spelling regression. Synthetic injected prose now fails the actual regression test while the CLI still returns 0 for findings.
- After: 15 focused tests pass; source AST comparison confirms copied matching/mention code and vocabulary. Separate Standards and Spec reviewers found a filename-only symlink gap; it was fixed and independently rechecked with no remaining findings on either axis.
- Full suite: **136 tests passed** with standard umask 022 and offline fixture isolation. Snapshot verification passes both pinned upstream trees. Privacy-safe refusal and scope/false-positive/false-negative cases are covered by synthetic tests; no Clinical fixtures or patient corpus were used.

## Merge Danger

**Door:** two-way

**Blast Radius:** maintenance

The normal CI suite will refuse listed uses only in the documented tracked maintained population; the command remains advisory. This finite vocabulary cannot detect every British spelling. Explicit copy permission is recorded, but the source contains no license file: no blanket MIT grant is claimed for copied/derived portions. Broader downstream redistribution licensing remains an owner decision. Draft only; no merge authorized.


## Licensing continuation — 2026-10-29

Parent instructed continuation of the same PR #7 and branch from
`274708e3400774e158fe1d8497361abd5c09c487`, with Matt's explicit grant answering
the ownership-conditional MIT question. The initial licensing hold above is now
resolved for the copied/derived portions of `scripts/spelling_scan.py` only,
including the incorporated helper adaptations. This does not extend to unrelated
Clinical files or change preserved upstream licenses. Existing root MIT text is
unchanged; source attribution, commit/blob pins and AI-assisted provenance remain.

Inspected scanner and source-test path histories and helper histories at source
commit `5f5be786eedca65a5c1a74bdf409b59bf6085b34`. Also inspected creation diffs
for console_codec (`a8c3b300`), git_paths (`aee97aaa`), tree_walk (`a2c08899`),
and scanner creation metadata (`89a0665f`). Histories identify Matt Shamblin or
his account identity and include Claude coauthor trailers; no conflicting
third-party attribution or imported-source notice was found in the inspected
source/history. No rights were inferred merely from repository ownership, and
no sole-authorship claim was added. Clinical working files remain unchanged.

Changed files: scanner header, docs/SPELLING_SCAN.md, THIRD_PARTY_NOTICES.md,
and this handoff. Runtime behavior and test code are unchanged.
Full revalidation and independent review of this narrow change are pending.
Parent retains final hosted verification and merge. No new PR will be created.
