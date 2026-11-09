# ADR 0013: Tribble Sniffer — explicit passive operation receipts and bounded triage

- Status: Accepted direction for bounded implementation; publication and live adoption are separate
- Date: 2026-11-09
- Owner: Operator; implementing coordinator owns the bounded delivery

## Context

The operator requested a practical way to notice operational denial and evidence
problems when no live listener is established. Existing [fleet recovery guidance](../FLEET_RESET_RECOVERY.md)
separates planned actions, submission, returned outcomes, independent readback,
unknown execution and retries. [PR coordination](../PR_COORDINATION.md) requires
scoped evidence rather than assuming a refusal was wrong. ADR 0011 covers a
structural handoff checker, not receipt ingestion, redaction or triage.

## Decision

Implement **Tribble Sniffer**, a small standard-library aid, [operation_receipts.py](../../scripts/operation_receipts.py),
explicitly invoked by a caller at an existing worker result boundary. The accepted
scope is caller-supplied exposed metadata and synthetic validation. Nothing is
intercepted, subscribed to, polled or automatically installed. No action-review
internals, protected logs, credentials, raw payloads or private rule contents are
read or captured. This adds no execution or permission gate.

Use a bounded JSON batch and fixed allowlisted enums, timestamps and sequence
numbers. Identifier and reference strings become SHA-256 fingerprints before
output; arbitrary text and unrecognized fields, including their names, are
omitted. Fingerprints are pseudonymous comparison aids, not anonymity, authentic
execution traces, resolvable source locators or proof of consent. Do not supply
secrets. Keep necessary original locators and scope in the existing private task
record, not in public evidence or this artifact.

Preserve every arrival and its provenance. Correlate only exact supplied source,
operation and distinct-attempt identities, plus item identity when supplied.
Mark duplicates only with an exposed delivery identity and identical typed JSON;
never discard receipts or collapse unknown identities. Preserve separate retries,
per-item partial writes, time/sequence evidence, unknowns and conflicting claims.
Readback describes later observed state, not the earlier review's inputs or the
cause of that state. Known plan provenance cannot establish an observed denial or
terminal action result. Invalid optional fields become unknown without losing
other valid receipts.

Derive fixed triage leads from sanitized records only, with event and attempt
indices: observed denial, supplied-authority-reference scope comparison, unknown
or partial execution, inconsistent metadata including delivery-identity collisions,
conflicting returned results or readbacks, and returned-result/readback scope
comparison. A denial plus a supplied
reference calls for comparing its actual scope; it proves neither a valid grant
nor an erroneous refusal. A success result containing denial wording is not a
denial. Missing phases, identities or sequence evidence are informational
visibility limits, separate from anomaly leads. An ordinary result-only success
must not become a suspected failure merely because other stages were not supplied.

Default to dry-run. Optional persistence creates a new artifact only at an
explicitly selected private destination with an existing owner-only POSIX parent.
Refuse existing files, symlinks and nonprivate destinations without overwriting or
creating directories. Verify written bytes locally. Do not modify the existing
task record or upload anything; its owner may reference the verified artifact
through already authorized custody procedures. Windows private-file persistence
is unqualified and does not write.

Capture errors return capture-health data and retain any uncertain partial local
write. They never execute, replay or change another operation or its arguments,
authority, permissions or holds. Callers must not gate operations on this aid;
handled CLI capture errors return zero rather than an action failure signal.

## Alternatives considered

- Live hooks, event subscriptions or telemetry exporters: no verified attachment
  to the current managed task; excluded from this change.
- Raw output logging or text-based denial guessing: risks private-content leakage
  and false positives. Fixed metadata omits detail deliberately.
- A general logger, automatic investigation or retry controller: unnecessary scope
  and would couple observation to authority or action execution.
- Receipt archiving without triage: preserves evidence but makes useful review
  leads harder to notice. Separate informational gaps from actual review leads.

## Consequences

The tool helps compare supplied receipts; it cannot observe omitted events, prove
caller assertions, reconstruct reviewer inputs, diagnose review causality or
establish complete coverage. Each invocation sees only its batch. Include earlier
exposed metadata when reconciling a late result, or compare the preserved
fingerprints through the existing private record. Same-user filesystem control,
host failures and remote durability remain outside the local sink's guarantees.

Live use requires an actual explicit worker invocation and an observed result.
Repository publication, passing tests and reading this ADR establish no adoption.
Existing ownership, original deadlines, denial/retry restrictions, product,
clinical, security/data, persistence, native and teardown holds remain unchanged.
Retire the optional aid when a supported mechanism covers these needs, without
deleting existing receipts or weakening those controls.

## Verification and references

- [Synthetic tests](../../tests/test_operation_receipts.py) exercise the public
  ingest and CLI boundaries, not protected systems or live actions.
- Initial independent challenge reproduced optional timestamp overflow,
  unencodable identifiers and plan-provenance misclassification. Regression tests
  were run failing before correction and passed afterward.
- The expanded focused suite passed 25 tests locally on Linux with Python 3.12.
  Exact final hashes, aggregate checks and independent-review disposition belong
  to the accompanying delivery evidence, not a claim of hosted or live success.
- Reproduce locally with `python -B -m unittest discover -s tests -p test_operation_receipts.py -v`.
  The repository aggregate command is `python -B -m unittest discover -s tests -v`
  with the existing offline Git fixture environment.
- Native Windows persistence, live event delivery, remote custody and deployment
  were not qualified by these synthetic checks.
