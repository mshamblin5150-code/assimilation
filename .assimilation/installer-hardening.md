# Assimilation installer-boundary candidate

Owner: existing Vox cloud worker; no duplicate implementation owner.
Date: 2026-10-29. Base main: `4f7d072a2bdf54142306c17246f1a5efea30f0e5`.
Local branch: `hardening/installer-boundaries`. **Publication is now explicitly
authorized** through the normal branch/PR route; merge and installation remain
held. Earlier no-publication entries below preserve the historical task scope,
not a current approval barrier.

## Intake and static triage

This reviews Chad's supplied summary plus independent source evidence. The full
audit was not available for this investigation; parent now has a separate reader
retrieving/verifying the subsequently supplied link. Do not duplicate retrieval.
The three claims and static verdicts are preserved in
`security-summary-triage.json` using `triage-finding/v0`, in supplied input order.
No original severity, attacker model or audit revision was invented.

1. Inherited installer Git configuration: `needs_review` for an exploitable
   security finding because the actor/trust preconditions are unspecified.
   The execution mechanism is present at base `scripts/skills.py:48-69` and
   `108-123`. A harmless marker-helper fixture subsequently reproduced execution
   through a synthetic global URL rewrite. This supports scoped hardening but
   does not establish compromise of Chad's or Matt's machine.
2. Bundled deleting script: `not_actionable` as a supported Assimilation install
   path. Base `upstream/matt-pocock/scripts/link-skills.sh:55-59` deletes existing
   non-symlink targets when separately run. It labels itself maintainer-only.
   Matt installer sparse scope also excludes its top-level scripts directory.
   No first-party call was found; root authority declares it inert reference
   material. Preserve original bytes and add an explicit first-party warning.
3. Bridge invocation restrictions: `confirmed` defect. Base `scripts/skills.py:374-384`
   emits name/description only. Source restrictions therefore disappear before
   host discovery; a later prose instruction cannot restore that host policy.
   Source examples include Matt implement and its paired Codex policy, plus
   P-Stack explicit-only skills. Actual host execution remains untested.

No root or scoped SECURITY.md applies. Read AGENTS.md, README.md,
docs/DOCTRINE.md, docs/SAFETY.md and original invocation instructions instead.
Used the security triage skill inline/read-only, then the authorized fix workflow
and Matt TDD/testing references plus P-Stack behavior-testing principle.
Shared security-skill reference assets (policy resolver/guidance/storage) were
unavailable through their supplied resource locators; no resolver run is claimed.
Manual scoped policy lookup and existing repository run-record conventions were
used, with this limitation disclosed rather than inventing tool evidence.

## Patch boundary and compatibility

Installer Git now strips inherited overrides/config and execution helpers, limits
transports without widening a caller restriction, disables hooks/templates and
credentials, and performs remote operations in fresh repositories. The source
comparison is isolated too. The shared Git helper is also used for first-party
publication validation; those callers must remain covered by the full suite.
Explicit local mirrors and exact lock/update-plan workflows remain supported.
No host settings are edited. Proxy/credential-helper/SSH-dependent access is not
claimed supported; a trusted Python/Git executable and OS remain assumptions.

Bridge generation preserves supported invocation, visibility, tool and path
restrictions. Either explicit-only source representation generates both supported
host controls. Unknown/ambiguous/contradictory policy refuses before replacement.
Only invocation policy is generated in host sidecars; source dependencies and
executable configuration are never activated. The bounded metadata reader is not
a general YAML loader. Source snapshots, licenses and source bytes stay intact.
Read-only metadata inspection accepted all 78 currently exposed pinned source
skills, 68 of which declare explicit-only restrictions. No live install was run.

Existing ownership/fingerprint checks, collisions, guards, concurrent-change
checks, same-filesystem staging, rollback and retained recovery backups are
preserved. Their integration tests remain required. No upstream script is edited.
No patient corpus, account material, live credentials, Windows computer, printer,
network/security setting or manufacturing action is involved.

## Verification sequence

Observed red/green: synthetic global Git rewrite executed its marker on the base,
then stopped doing so while ordinary local-source installation succeeded on the
candidate. The bridge test first failed on omitted restrictions, then passed with
policy carried into generated metadata. Regression cases also cover environment
repository redirection, caller config, template hooks, smudge filters, protocol
narrowing, cross-host policy, malformed/duplicate/aliased metadata, failure
atomicity, and inert synthetic upstream scripts. All executions use temporary,
synthetic local repositories, never a live installation or real upstream script.

Initial candidate `5536b9316f19d1d20b0d5ab63a968244ae65fa45` passed all 44 focused
installer tests and all 146 repository tests (43.430s) using standard umask 022.
Independent pre-patch read-only investigator completed source/caller/compatibility
review. Fresh independent bypass/regression reviewer ran 44 installer and 22
publication tests and found one real regression: `GIT_PROTOCOL_FROM_USER=0` was
stripped and its file-transport denial widened. The revised candidate preserves
that denial. Parent worker independently reproduced BOM-prefixed frontmatter
being treated as plain text; metadata-only UTF-8 BOM normalization now preserves
its restrictions while original source bytes remain untouched. Both new
regressions failed before their fixes and passed after, with legitimate controls.
The same reviewer will verify these focused deltas within the original review
cycle. A final full run is required on the revised committed candidate before
reporting verification complete; exact hash/results are returned to parent.
Logs: `/tmp/assimilation-hardening-focused.log`,
`/tmp/assimilation-hardening-full.log`, and final revised
`/tmp/assimilation-hardening-final.log`. No live installation is involved.
Parent owns full-audit reconciliation and publication decisions.

Bambu H2C is context for future CAD work only. This patch establishes neither
Windows/harness compatibility nor printer safety, material suitability, load
capacity, manufacturing acceptance or authority to control equipment.


## Full report continuation

The original candidate and receipt at `3b374928df1bbda642573f7d5d1b2a076b26b1b6`
are preserved without amendment. Parent verified the uploaded ZIP/hash/manifest
and relayed all three report documents as untrusted data after this worker's
Library transfer returned `download failed` without a local archive. Report
source commit is unverified and 11 exported outputs were truncated; no audit
code or proposed patch was executed. Current source was checked independently.
See docs/AUDIT_RECONCILIATION.md for all 11 dispositions, proposal decisions,
positive safeguards and explicit Windows/live-host limitations.

The independent read-only investigator verified optional-tool claims and found
no first-party installer activation path. A fresh delta investigator identified
shared Git policy drift, source/acquisition distinction, raw error leakage and
reparse-check gaps. Sole implementation owner prepared the bounded delta with
synthetic failing-before/passing-after fixtures. Upstream bytes/licenses,
existing root license, pinned manifest and lock remain unchanged. No live
installer, private corpus, user home, credentials, host setting or equipment was
accessed or modified.

Operator subsequently explicitly authorized GitHub upload through normal branch
and PR review. This supersedes only the historical publication hold above.
Do not merge, install on Windows, change settings/credentials or operate equipment.
The final exact candidate must receive independent delta review and full tests,
then remote-byte and hosted-check verification before final parent delivery.
Current local focused results: 50 installer tests and 24 snapshot tests passed.
The published receipt will distinguish these observations from untested native
Windows/host enforcement and optional-upstream execution.


Full-audit review continuation: independent source/disposition review accounted
for all 11 findings with no false closure. Fresh code reviewer independently ran
50 installer, 24 snapshot and 22 publication tests on `98c62b9` and identified a
remaining descendant-reparse/copy-before-validation gap. Parent reproduced it,
added failing regressions, checked source trees before copying, and refused
reparse metadata in snapshot walks and file reads. Both focused regressions now
pass. That is a synthetic metadata boundary check, not native Windows evidence.
The full 155-test run on `98c62b9` passed in 46.061s; final revised-candidate
validation and independent finding closure must precede GitHub publication.


Current focused corrected-state checks: 51 installer tests and 25 snapshot tests
passed. Syntax, snapshot integrity and spelling checks passed. The final commit
will be independently checked for closure of the descendant-reparse finding and
run through the full suite before the already-authorized branch/PR upload. No
publication attempt, denial or uncertain remote mutation has occurred yet.
