# Security, privacy, licensing, verification

Assimilation is intended for public sharing. It includes only **generalized** ideas from Open Brain, not Open Brain content dumps, live connectors, tokens, user-specific medical information, internal file paths, or the private DAVID 2 repository. Do not add such content later. Clinical Skills is a separately maintained public project; it illustrates the skill-document format but **is not a dependency** of this starter package.

**Before sharing:** inspect staged files with `git diff --cached`, verify `vendor/`, `.agents/`, `.assimilation-stage-*`, `.assimilation-snapshot-stage-*` (including under `upstream/`), and `.assimilation-install.lock` are ignored (except the optional curated local skills under `skills/`), check no private data, patient information, account IDs, keys, secrets or unlicensed material is included. Never assume scanners are complete. No workflow here grants authority to inspect private projects or post on anyone else's behalf.

**Trust of upstream sources:** `upstream/` contains complete, verbatim external reference data. Its nested agent instructions, workflows, plugins, hooks, and scripts do not override root/project/operator authority and must not be activated merely because they were copied. `install` and snapshot preparation fetch data from published GitHub repositories but do not run upstream setup scripts. Treat each changed source commit as an external dependency. Review its diff and licenses before using any newly changed executable tools or giving agents file/system permissions. Monthly automation **only proposes review**.

**Citations and attribution:** external works retain their own notices in visible and installed source trees. See [third-party notices](../THIRD_PARTY_NOTICES.md) for supplemental HumanLayer attribution. Matt Pocock's skills are MIT-licensed (copyright 2026 Matt Pocock); P-Stack is MIT-licensed (copyright 2026 Lauren Tan), based on inspected upstream license files. This starter package is independently written; do not represent it as official upstream documentation. **Public URLs or public licenses do not imply permission to expose private user data.**

**Engineering and physical risk:** no claim of physical strength, fitness for purpose, medical accuracy, or security is valid without appropriate testing and expert oversight. The claim-and-refutation review is an evidence check, not a guarantee. Real mechanical designs must consider load cases, print orientation, material strength, fasteners, temperature, and tolerances.

**Authority and verification:** a ZERO_BLOCKING_FOG declaration confirms no unresolved **known blocking design decisions** for a defined scope. It is not permission for commits, merges, external communications, releases, credential access, or deployment. Those follow operator and platform permissions separately.

**Stopped installations:** retained stages can contain the only original backups, private local skills, or fetched Git configuration. Never publish them or delete them merely to clear a guard. Follow [recovery without data loss](RECOVERY.md).

**Fetched source links:** the installer preserves relative links to regular files contained within each fetched collection, including Matt's `AGENTS.md` link to `CLAUDE.md`. It rejects escaping, absolute, dangling, cyclic, directory, and special-file links. Destination paths, generated skills, local skill copies, and unmanaged content remain link-free. Source preservation does not execute or endorse the linked instructions.

**Snapshot content checks:** exact license inventories and known private-key/GitHub-token signatures are checked before source publication. They are bounded checks, not a complete secret scanner, a code review, or permission to execute preserved files. Review changes independently.

**Native Windows source operations:** installation, source comparison, snapshot verification/refresh/preparation, proposal generation and publication require a POSIX runtime and otherwise refuse before source I/O, guards, staging or child processes. Native Windows permission metadata is not an equivalent ACL guarantee; neither a Git commit SHA nor a flattened link proves materialization. This eligibility check preserves all actual POSIX mode, content, type, link and ownership checks. It does not certify any POSIX filesystem, host or runtime. The [seven-item validation disposition](WINDOWS_VALIDATION.md) records the unresolved MSYS denial and separates native, Linux and simulated evidence. No workaround, settings change or Windows installation is approved by this documentation.

**Installer Git boundary:** source discovery and fetching use fresh repositories,
not the caller's repository configuration. Installer Git subprocesses discard
inherited `GIT_*` overrides, system/global config, askpass commands, hooks,
templates, credential helpers and filesystem monitors. Only HTTPS and local file
transports are permitted, intersected with a caller's narrower `GIT_ALLOW_PROTOCOL`
limit. `GIT_PROTOCOL_FROM_USER=0` also keeps local file transport disabled.
Explicit `ASSIMILATION_MATT_SOURCE` / `ASSIMILATION_PSTACK_SOURCE` overrides accept
local filesystem paths only (not alternate remote URLs or `file://` URLs). The
canonical official URL remains the expected source identity, while new unlocked
lock entries record acquisition kind and a SHA-256 selection fingerprint without
persisting private paths or credentials. That distinction is not official-host
attestation; exact locked commit checks verify content identity. Existing locked
bytes are preserved.
Installer and snapshot commands share `scripts/git_runtime.py`; raw Git failures
are suppressed and each Git subprocess has a timeout. This does not change host Git settings. It assumes a trusted Git executable,
Python runtime and operating system. Custom credential-helper, SSH, proxy or URL
rewrite configurations are not an installer compatibility promise; environments
that require them need a separately reviewed source-access design.

**Bridge invocation policy:** generated bridges preserve supported
`disable-model-invocation`, `user-invocable`, `allowed-tools`, and `paths`
restrictions. An explicit-only declaration in either source frontmatter or
`agents/openai.yaml` yields both the frontmatter restriction and
`policy.allow_implicit_invocation: false` in the generated sidecar. Sources with
neither restriction retain ordinary invocation behavior. Original source bytes
and source sidecars remain in `vendor/`; generated sidecars contain only invocation
policy, never upstream dependency/tool activation. These are host discovery
controls, not an operating-system sandbox, and host enforcement must be verified
for the actual agent being used.

The standard-library metadata reader accepts a bounded mapping form: simple or
quoted keys, UTF-8 BOM/CRLF input, explicit boolean values with optional comments, scalar/list tool
and path scopes, and the currently shipped source metadata. Aliases, merges,
tags, conflicting host policy, duplicate keys, unknown activation fields and
unsupported structures refuse before destination replacement. This intentionally
requires review when upstream adds a new control. Plain-text legacy skills with
no frontmatter remain supported and can still declare a sidecar policy. The
reader is not a general YAML implementation.

**Do not run upstream linking scripts as Assimilation setup.** In particular,
[`upstream/matt-pocock/scripts/link-skills.sh`](../upstream/matt-pocock/scripts/link-skills.sh)
is a preserved upstream maintainer script that deletes existing non-symlink
skill directories in user-level destinations before creating links. Assimilation
never calls it. Use only the reviewed first-party installer when installation is
authorized. Keeping this script verbatim preserves provenance; its presence is
not permission to execute it or to bypass collision/ownership checks.


**Full audit reconciliation:** [finding-by-finding dispositions](AUDIT_RECONCILIATION.md)
distinguish supported installer defects from preserved opt-in utility hazards.
Watcher bootstrap, statechart runtime/view execution, worktree transcript access,
credential wizards, broad permission instructions and regex guardrails remain
inactive reference material, not approved operations. Host capabilities must
constrain an explicitly selected workflow independently of its prose. Destination
and source checks reject reparse metadata; concurrent path substitution, native
Windows ACL/link behavior and live host enforcement still require separate tests.
