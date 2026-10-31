# Windows generated-files-v1: proposed safety contract (draft)

Status: **design-only, not an implementation or authorization to install**. Tracks #11; depends on #9 and merged #10. Existing native Windows source-operation refusal remains in force.

## Trust and identity boundaries

- Inputs: independently verified canonical source tree, including blob contents, literal symlink targets, executable modes and source commit identity. A canonical source digest is not a native filesystem permission or object identity.
- Output proposal: generated **regular files** in an explicitly selected destination, with a separate versioned view manifest and digest. No direct symlink flattening without an approved, deterministic mapping and retained source-link provenance.
- A source verifier, a view generator, a native destination inspector, and a transaction/activation controller have distinct responsibilities. No observation or synthetic test alone grants installation authority.
- Trusted Python startup and trusted operator-supplied destination are prerequisites; neither automatically establishes safe Windows filesystem behavior.

## Fail-closed gates before any future implementation

| Gate | Required proof | Unknown/denied response |
| --- | --- | --- |
| Source | Exact canonical commit/tree/blob/link/mode proof independent of worktree bytes | Refuse; no installation |
| Mapping | Deterministic generated-files-v1 schema, collision-free Windows name normalization and separate view digest | Refuse |
| Destination | Native handle-based identity and confinement, ACL/owner/inheritance evidence; no reparse traversal or unreviewed link target | Refuse without retry or ACL change |
| Staging | Captured payload digest, private bounded staging, immediately-before-commit byte and identity revalidation | Refuse and preserve evidence |
| Collision | Proven managed object identity, unchanged baseline and no unexpected private-content reads | Refuse and preserve user data |
| Recovery | Authenticated transaction ownership, bounded journal states and documented interruption semantics | Quarantine ambiguity; do not overwrite |
| Concurrency | Reviewed native handle/locking contract and adversarial race tests, not only before/after hashes | Refuse |
| Activation | Separate human authorization, quiescence and invocation enforcement | Remain inactive |

## Negative-case test matrix (planned, not executed)

1. Case-fold and Unicode-name collisions; trailing dots/spaces, reserved device names and alternate data stream syntax.
2. Junction/reparse/symlink substitution at each ancestor and destination leaf; unknown tags and access-denied observations.
3. Staged bytes replaced after digest; parent or destination object identity swapped before commit.
4. Existing unmanaged object, edited managed file, stale manifest, and private payload that must not be opened.
5. Power loss or process interruption at each journal transition; recovery with missing, conflicting or edited artifacts.
6. Two writers racing on the same destination and a third-party writer changing parent/destination identity.
7. Invalid canonical source/link proof; mismatch between canonical digest and generated view digest.
8. Regression: Windows refusal/help, onboarding, clean-checkout preservation and Ubuntu source snapshots remain green.

## Evidence ladder

- **Level 1:** specification and source inspection (this document).
- **Level 2:** isolated synthetic/fault-injection tests (future PR revisions).
- **Level 3:** actual Windows native observation and adversarial filesystem tests on an approved disposable fixture (future separately reviewed work).
- **Level 4:** authorized staged installation and recovery qualification (future separate issue and approval).

Do not confuse levels. This draft establishes **no** native ACL, junction, rollback, race, durability or installation proof. The earlier MSYS named-object ACCESS_DENIED remains unresolved; no bypass or transport retry is authorized.

## Review gates

Independent security/spec review, precise source identity, explicit evidence of failed/blocked cases, exact-head Ubuntu and Windows CI, and explicit human merge approval are required. Do not change host PATH, ACLs, elevation, Developer Mode, dependencies, Git transport, or execute upstream tools. No patient data, secrets or private environment values in reports.

## Native Windows disposable-fixture test plan (not yet executed)

**Prerequisites:** separate review and approval for a dedicated temporary directory owned by the test runner; no operator home, installed tree, or user-selected destination. Use only harmless synthetic bytes. Do not change ACLs or privileges to make a test pass.

1. Establish baseline: record Windows volume type, filesystem semantics, absolute fixture root, canonical handle-derived identity and ACL/owner evidence. Fail closed on unsupported observations.
2. Ancestor confinement: create test-owned regular directory chains; reject a fixture path when an ancestor or leaf is replaced by a symlink, junction, or unexpected reparse point. Require handle-based revalidation, not string prefix matching.
3. Collision privacy: create an unmanaged sentinel with unique bytes. Assert a refused collision does not read, overwrite, rename, or delete that sentinel; observe operations via explicit instrumentation.
4. Staging integrity: stage known synthetic bytes, calculate independent expected SHA-256, mutate staged bytes before the commit gate, and assert no destination mutation.
5. Identity races: substitute a test-owned destination/parent between observation and commit, then require refusal without touching the replacement. Test two simultaneous writers and a third-party substitution.
6. Interruption/recovery: inject termination at each durable journal boundary; restart with authenticated fixture ownership and refuse ambiguous/missing/tampered journal states. Document fsync/durability limitations and whether rollback is actually possible.
7. Teardown: delete only objects whose identities remain proven test-owned; otherwise quarantine and report. Never follow unexpected reparse links during cleanup.

**Exit criteria:** record exact commit, runner image, native APIs used, fixture boundaries, instrumentation, failures and limits. A synthetic state-machine pass is not evidence for any of the native claims above. This plan is not an installer implementation or permission to run native adversarial tests.
