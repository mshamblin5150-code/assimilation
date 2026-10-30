# ADR 0007: fail closed without verified native source guarantees

- Status: Accepted, native compatibility remains unsupported
- Date: 2026-10-29
- Owner: Matt Shamblin, operator; scoped implementation by Vox

## Context

Native Windows validation of PR #8 head
`434de392f0fd57ea673e652177f8aae0c007fe64` reported metadata that does not satisfy
the existing exact POSIX-mode contract. Git checkout configuration also permits
flattened symlinks and newline conversion. Separate local-file fetch failed in
MSYS named-object creation with ACCESS_DENIED; its enforcing boundary remains
unidentified. Linux tests do not establish native ACL, junction or link behavior.

## Decision

Matt explicitly chose refusal where equivalent guarantees cannot be verified.
Source-operation entry points require `os.name == "posix"` before reading source
inputs, creating guards/stages/outputs or launching Git. This is runtime eligibility,
not filesystem certification. Existing exact POSIX modes, regular-file types,
reparse refusal, literal symlink/containment checks, bytes, object proofs,
inventories, ownership and transactional checks remain unchanged. Unsupported
operations return an explicit nonzero diagnostic. Help, source browsing and pure
validation helpers remain available.

## Alternatives considered

- Treat native 0666/0777 as canonical 0644/0755: rejected; this would invent
  permission equivalence and weaken executable-mode tamper detection.
- Accept placeholders, normalize untrusted link spellings, or change Git/ACL
  settings: rejected; these would change the integrity/security contract.
- Attribute MSYS ACCESS_DENIED to the product or bypass it: rejected; no enforcing
  boundary or supported product remedy has been established.
- Continue with incidental metadata failures after staging: replaced by an
  explicit unsupported-runtime diagnostic before source operations start.

## Consequences

Native Windows source operations remain unsupported, including offline snapshot
verification and automated source proposals. A supported POSIX runtime can still
fail actual integrity/capability checks. No WSL, alternate executor or native ACL
equivalence is asserted. A future native implementation needs separately reviewed
canonical Git-mode versus observable-metadata semantics and exact-candidate native
evidence; this decision does not authorize acquiring tools or changing a host.

## Verification and references

[Windows findings and evidence limits](../WINDOWS_VALIDATION.md) preserve all seven
dispositions. `tests/test_platform_contract.py` exercises public APIs and CLI
error exits with a simulated unsupported runtime, denying subprocesses and source
reads and checking unchanged output state. These simulations do not reproduce
native OS behavior. Existing POSIX executable-mode tamper, content, type, link,
reparse and recovery tests remain required.
