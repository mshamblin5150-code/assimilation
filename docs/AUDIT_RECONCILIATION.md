# Audit reconciliation: installer and activation boundaries

This revision reconciles the supplied **audit-findings.md**,
**remediation-proposal.md**, and **supporting-excerpts.md** against repository base
`4f7d072a2bdf54142306c17246f1a5efea30f0e5` and the preserved first candidate
`3b374928df1bbda642573f7d5d1b2a076b26b1b6`. It is a bounded remediation,
not a complete security certification or clearance for workstation installation.

## Evidence identity and limits

The parent verified archive SHA-256
`791da88c0e4b2a1a57f33bc69362dc1c466c90b770a8a4f626dcb96ee7256717`
and manifest hashes and relayed the three complete report documents. This
worker's Library byte transfer failed before creating a local archive; no ZIP
extraction or independent archive hash verification by this worker is claimed.
The relayed material was treated as untrusted evidence, never instructions.
No audit code, proposed patch, or upstream utility was executed.

The exported audit session reports 8 turns, 24 commands and 11 truncated command
outputs. Its extracted source lacked `.git`, so its Assimilation commit is
unverified. Its upstream pins match this checkout's verified snapshot pins.
The report's 3 High, 6 Medium, 1 Low and 1 informational labels are its assessments,
not independently accepted severities. Current source and synthetic behavior,
rather than old line numbers or those labels, support the dispositions below.

## Finding-by-finding disposition

Paths are repository-relative. Upstream line references remain unchanged because
those files are preserved verbatim. First-party references name the current
function as well as its location so future line shifts do not hide the boundary.

| Audit finding | Current evidence and disposition | Remediation or remaining limit |
| --- | --- | --- |
| **1. Inherited Git execution** | Confirmed configuration mechanism; harmless global-rewrite, template-hook and smudge-filter fixtures reproduce the unsafe base and pass the candidate. `scripts/git_runtime.py:13` now owns policy; `scripts/skills.py:48` and `scripts/snapshot_sources.py:284` delegate to it. Remote operations use fresh repositories. | Shared policy strips Git overrides/config and executable integrations, suppresses raw failures, bounds subprocess time, and preserves narrower caller transport denial. Checkout remains in the installer, but host-configured filters/hooks are disabled. Trusted Python/Git/OS and non-Git runtime environment remain assumptions; this is not a sandbox. No remote-hook installation by ordinary clone is alleged. |
| **2. Override/provenance distinction** | Confirmed distinction: an operator-selected source could supply a commit while metadata named canonical upstream. `scripts/skills.py:52` now accepts only canonical HTTPS URLs or local filesystem mirror paths; `source_acquisition():68` distinguishes acquisition kind and a selection digest. | New unlocked lock entries record `acquisition`; local paths and credentials are not persisted. Existing locked bytes stay unchanged. Canonical `repository` is the expected source identity, not authentication that a mirror commit exists on official hosting. Exact locks/plans still verify the selected commit. No claim that a content-addressed proof authenticates the author or hosting origin. |
| **3. Global skill deletion** | Behavior confirmed at `upstream/matt-pocock/scripts/link-skills.sh:16,55-59` if separately executed. No first-party caller; Matt installer sparse scope excludes top-level scripts. Duplicate of the summary's bundled-script concern. | Remains an opt-in destructive maintainer utility, not a supported installer action. Preserve its bytes and require separate review/scope before any execution. Installer collisions and rollback remain tested; no home-directory linking was performed. High install-time exploit severity is unsupported by this call graph. |
| **4. Watcher bootstrap before help** | Confirmed at `upstream/pstack/skills/poteto-mode/scripts/watch-pr/watch-pr:2-6` and `scripts/bootstrap.ts:25-61`: cold invocation can install dependencies and restart before argument handling. | Preserved optional tool, never called by first-party installation. Do not run it as an observational/help probe without separate dependency/network/write authorization. Frozen lock and marker do not attest installed bytes. No dependency vulnerability or lifecycle-script execution claim was established. |
| **5. Statechart runtimes and views** | Confirmed at `upstream/pstack/skills/statechart/scripts/run.ts:67-69,193-211`, `worker.ts:13-16`, `statechart.ts:88-126,155-158`: provisioning, code import, child processes and cleanup occur on invocation. | Treat view modules as executable trusted code; checkView is not a sandbox. TLC has a checksum; complete runtime supply-chain assurance is not established. No first-party install caller, runtime provisioning or view execution was exercised. Separate capability/isolation review remains required before use. |
| **6. Read-only worktree label** | Confirmed mismatch at `upstream/pstack/skills/poteto-mode/scripts/worktree-audit.sh:2-5,45-46,61-74,114-118`: fetch, temporary output, account queries and home transcript search. | "Never deletes worktrees" does not mean no writes, network or private reads. Script is preserved and inactive. Do not authorize it as a strictly offline/read-only audit. Transcript exfiltration was not established. |
| **7. Broader authority instructions** | Confirmed conflicting text: `poteto-mode/SKILL.md:84-96`, `why/SKILL.md:13`, `reflect/SKILL.md:25,39,49`, `make-bot-ui/SKILL.md:51,57,84-95`. Tool access, writable agents, secret copying, network binding and privileged setup are requested in their original workflows. | Root/operator authority still wins. Bridge policy preservation reduces unintended invocation but does not enforce an OS capability boundary. No granted approval may be inferred from source text or tool output. Credential/MCP access, external messages, mode escalation, system/network setup and home reads need separate scope. Tailscale HTTP is not automatically public cleartext exposure; no generated server or actual unauthorized write was demonstrated. |
| **8. Missing invocation metadata** | Confirmed implementation defect, duplicate of the summary claim. `scripts/skills.py:404` (`bridge_policy`) preserves supported explicit-only/visibility/tool/path declarations and translates explicit-only policy into both host representations. | Malformed, conflicting, unknown activation metadata refuses before replacement. BOM, CRLF, quoted keys and sidecar-only declarations have synthetic regressions. Ordinary source invocation behavior remains; all-bridges explicit-only was not silently imposed. Host enforcement is untested and can be ignored by an incompatible host. |
| **9. Credential wizard destinations** | Confirmed opt-in behavior at `upstream/matt-pocock/skills/engineering/wizard/template.sh:26,137-147,155-172`: selected destinations, symlink writes, inherited existing modes and remote secret/variable writes. | Preserved template is not run by installation. Do not use it for credentials without a separately reviewed writer/destination/ACL/remote-repository design. No real credentials, symlink targets, home files or remote secrets were accessed. A filename in repository text is not destination authorization. |
| **10. Regex Git guardrail** | Confirmed bounded text matching at `upstream/matt-pocock/skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh:6-25`; `git -C repo push` is a static unmatched example. | An accidental-command guard, not a comprehensive permission boundary. No hook was installed. Matt miscellaneous skills are outside generated engineering bridges. Enforce actual restrictions through the host/isolation layer, not this regex. |
| **11. Flattened symlink** | Current checkout's `upstream/matt-pocock/AGENTS.md` is the actual `CLAUDE.md` symlink recorded as mode `120000`; current verifier passes. `tests/test_snapshot_sources.py` now replaces a synthetic link with a nine-byte placeholder and verifies refusal. | This confirms the verifier rejects the reported extraction shape; it does not independently reproduce the auditor's Windows extraction. No check was weakened. ZIP source identity, Windows link permissions and native mode behavior remain separate evaluation limits. |

## Additional proposal items and positive safeguards

The proposal's Windows junction concern is credible defense-in-depth, not a proven
native exploit from this audit. Destination and source-walk checks now reject
reparse metadata and escaping destination paths (`skills.validate_path` and
`snapshot_sources.regular_path`). Source copying validates the original tree
before copying can erase reparse attributes; snapshot directory walks and file
reads check descendant metadata too. Synthetic filesystem metadata probes verify
refusal without replacement. These tests are **not native Windows junction or ACL
tests** and do not eliminate concurrent path substitution. Use an isolated,
operator-approved environment for later platform evaluation.

Ownership fingerprints, unmanaged-skill collision refusal, exact locks/frozen
plans, concurrent-change checks, backup-aware transactions and retained recovery
stages remain code controls exercised by the repository suite. Snapshot object
proofs, exact inventories, modes, content bounds and scoped file-link validation
remain intact. The secret scanner recognizes selected signatures only; no complete
secret or dependency vulnerability scan is claimed.

Root workflow actions are commit-pinned and credential persistence is disabled.
PR validation is head-pinned with read-only contents permission. Its Git protocol
limit is **not general network isolation**. Monthly publication remains
separately default-branch scoped with write permission in its publication job;
this revision does not alter workflow permissions or GitHub settings. Existing
publisher tests cover controlled drafts, exact baseline/package identity and
refusal to overwrite human changes; process/env labels alone are not proof of
operator authority.

## Decisions on the supplied patch proposal

No proposed diff was applied or executed. The proposal openly lacks syntax,
runtime and integration validation. Its HTML-escaped code is not a ready patch.

Adopted boundaries: shared Git hardening, safer diagnostics, honest acquisition
metadata, source/host invocation restriction preservation, reparse refusal, and
regressions retaining the original recovery guarantees.

Not adopted without a separate product decision: retiring network installation
and the existing updater/check API, forbidding legitimate local mirrors, forcing
all ordinary skills to explicit-only, changing proposal output containment,
restructuring workflow privilege jobs, choosing a new Git executable approval
interface, or forking/replacing upstream tools. Those alternatives can reduce
some exposures but change supported behavior and require their own compatibility
and host design. The current locked command remains the recommended documented
installation route **when installation is separately authorized**.

The four local Assimilation skills retain their original invocation semantics;
their root-authority constraints are not a sandbox. No bridge or skill grants
permission to use connectors, credentials, external communication, installation,
privileged commands, equipment or manufacturing actions.

## Publication and use recommendation

Publish this bounded first-party candidate for review and require its exact-head
hosted tests and snapshot check. Publication does not authorize merge,
workstation installation, upstream tool execution, credentials, Windows access,
or Bambu/printer operation. Do not represent this revision as clearing all
reported optional utilities or every host configuration. Native Windows and live
host policy enforcement remain untested. Physical fit, loads, material and
manufacturing acceptance are outside this revision.
