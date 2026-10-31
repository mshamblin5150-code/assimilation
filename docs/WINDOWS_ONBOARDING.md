# Windows onboarding: observations before installation

This is a read-only prerequisite report for issue #9, separate from PR #8's
hardening and [issue-writing training](ISSUES.md). It does not install skills,
verify source snapshots, qualify a destination or grant permission to proceed.

Use an existing trusted Python 3.10+ interpreter. If one is unavailable, stop
and report that prerequisite; this document does not authorize installation.
Run from this checkout with the interpreter's known absolute path if needed:

```text
python -B scripts/windows_onboarding.py
python -B scripts/windows_onboarding.py --help
```

No alternate launcher, tool download, elevation, Developer Mode, PATH edit or
security change is required or performed by the report. Do not repeat a denied
operation or try another identity/transport to bypass it.

## What the report means

The JSON observes OS/runtime categories, numeric Python and Windows versions,
pointer width, Python prefix separation and the presence of two environment
markers. Environment markers may be stale or forged; neither they nor prefix
separation prove dependency availability. Values and absolute paths are omitted.

Git availability/version remain unverified: no PATH lookup, filesystem metadata
search or Git execution is performed. PATH lookup can reach UNC, mapped-drive
or reparse destinations and cause OS-level network effects outside Python's
socket audit events. Do not infer Git absence from a deliberately unprobed state.
Use existing trusted operator evidence if a later action needs Git; a new probe
requires its own bounded scope. Do not automatically repair PATH or install Git.
This report itself does not need Git. Runtime observation failure returns a
bounded error without exception text or fallback. Trusted Python/standard-library
startup is assumed.

The report does not read repository files, Git configuration, package contents,
ACLs, account identities, credentials or arbitrary environment values. It does
not list a directory, start a child process, open a socket or write a file.
It is not an OS sandbox and does not qualify paths, redirections or external tools.

The Python prerequisite explicitly reports minimum [3, 10] and satisfied or unsupported. An unsupported version gives a stop/use-existing-interpreter explanation; it never installs or admits installation. Version-injection tests are synthetic, not execution on an older interpreter.

Exit 0 means the observation completed, with status `observed-not-qualified`.
Exit 1 means observation was unavailable; exit 2 means invalid arguments.
Help performs no prerequisite discovery. Every successful report keeps
`source_verified`, `filesystem_verified` and `installation_admitted` false.
Do not use exit 0 or runtime identity as an installer admission gate.

## Native Windows and POSIX are different contracts

Native Windows source operations still refuse before source I/O or subprocesses.
POSIX identity is necessary for the existing source-operation contract, but does
not certify a particular filesystem or installation. Canonical Git modes,
literal link bytes and tree/blob proofs describe source identity; they do not
establish Windows ACLs, ownership or the objects physically on disk. Native
0666/0777 observations are not equivalent to canonical 0644/0755 permissions.

The first planned Windows representation is an explicitly verified generated
regular-file view, with canonical source/link proof retained and a separate
view identity. It is not a flattened-link workaround or current install support.
Native symbolic links remain a separately qualified option; do not enable them
by changing Developer Mode, elevation or privileges for this report.

| Installation boundary | Required evidence before a later installation |
| --- | --- |
| ACL and ownership | Reviewed native principal/rights/inheritance policy and actual observations; no automatic repair or legacy adoption |
| Reparse points, junctions and links | Qualified confinement and identity observations; unknown/unsupported forms refuse, no denied-operation replay |
| Source integrity | Independent canonical proof, captured payload and generated-view checks; verify staged bytes immediately before commit, including transient substitution controls |
| Collisions and private data | Refuse unmanaged or edited objects; inspect permitted metadata before any authorized managed-payload read, never read unexpected private content |
| Rollback and recovery | Authenticated ownership/request/baseline, bounded states and fault tests; preserve originals, ambiguous outcomes and human edits; no unproven atomicity/durability claim |
| Concurrent writers | Reviewed identity/handle/confinement contract plus actual race tests; before/after hashes alone are insufficient |
| Host activation | Separate authorization, quiescence and actual invocation enforcement; upstream utilities remain inactive |

These are required gates, not claims that the onboarding command implements or
qualifies them. ACLs, ownership, links, junctions, rollback, concurrency and MSYS
are explicitly `not-probed`. A full installer remains dependent work with its
own security contract, native acceptance and explicit installation approval.

## Existing MSYS denial

Earlier synthetic local fetch exited 128 after Git 2.54.0.windows.1's `sh.exe`
reported `NtCreateDirectoryObject` under `\\BaseNamedObjects\\msys-2.0S5-1888ae32e00d56aa`
with status `0xC0000022`. This is evidence of a local named-object failure,
not a GitHub API denial. Its enforcing cause is unresolved: the record does not
distinguish executor confinement, Windows ACLs or endpoint policy. This command
does not reproduce it. Supported provider/error evidence is needed to sharpen
the diagnosis; changing launchers, transports or settings is not a remedy.
See [preserved Windows limits](WINDOWS_VALIDATION.md).

## Verification and handoff

Tests use the public command/report boundary with actual running OS identity,
unprobed Git with an absent PATH and synthetic environment cases, safe argument/error handling and
scoped audit monitoring with positive controls. Synthetic failure injection is
labeled; it is not a native access-denial or ACL test. Monitoring begins after
trusted imports and cannot observe every OS metadata effect or enforce a sandbox.
The positive controls emit synthetic audit events: they verify hook response,
not capture of every real OS operation. Separate boundary patches make PATH
discovery, `stat` and `access` fail if default reporting attempts them.

Record the exact candidate, runtime, command, test counts, skips and remaining
limits using [the run record](templates/RUN_RECORD.md). Do not include private
environment values in public evidence. Link dependent work to [issue #9](https://github.com/mshamblin5150-code/assimilation/issues/9)
and use the [issue guide](ISSUES.md) for safe actionable tickets. Completing this
onboarding slice does not close the full installer outcome. Independent review
and explicit human merge approval remain required; no automatic approval/merge.

The CI-only tests/onboarding_clean_checkout.py harness runs report and help before other tests in both exact-head jobs. It compares Git status including ignored/untracked entries and a complete bounded worktree inventory (excluding root .git internals). Git and filesystem reads belong to that test harness, not the report. It does not qualify native installation.
