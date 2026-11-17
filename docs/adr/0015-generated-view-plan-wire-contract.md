# ADR 0015: proposed generated-view and plan wire boundary

- Status: Proposed
- Date: 2026-11-17
- Owner: Chad for issue 11; engineering proposal, not an owner decision

## Context

PR 12 has name-preflight and synthetic transaction prototypes, but no concrete
wire contract connecting canonical source, regular-file view and an exact plan.
[ADR 0014](0014-local-exact-plan-installation-consent.md) records local single-attempt consent. Data validation cannot establish
native identity, managed ownership, authenticated recovery or that consent.

## Decision

No production schema decision is accepted by this ADR. Propose the bounded
[wire contract](../WINDOWS_GENERATED_VIEW_SCHEMA.md) for independent review:
strict versioned JSON; separate view/plan digests; unchanged regular source
files; create-only proposal effects; explicit unqualified native bindings.
This moves exact data-format questions into review without granting a parser
the authority of a future native installer.

## Alternatives considered

- Accept arbitrary mappings and opaque native identity strings now. Less
  initial schema work, but obscures missing provenance and qualification.
- Require the entire native installer contract before specifying any data.
  Avoids temporary format limits, but postpones useful independent review.
- Specify a deliberately limited proposal format first (recommended).
  It permits bounded validation work; a future production version must add
  reviewed transformation, baseline, native custody and recovery contracts.

## Consequences

This draft does not cover the full intended installer payload or upgrades.
Executable files, links, generated wrappers, replacements and deletions remain
out of scope for initial parsing. Review must decide whether those restrictions
make the first slice useful and confirm the proposed resource/digest encoding.
No caller or installer is migrated. Rollback is removal of proposal documents.

## Verification and references

The source, name and transaction prototypes and
[issue 11's local-only decision](https://github.com/mshamblin5150-code/assimilation/issues/11#issuecomment-6607225033)
were read. The contract lists worked rejection requirements, not test
passes. New parser tests await an agreed public seam; no native test, installer,
consent mechanism or security-setting change ran for this documentation slice.
Independent review of these documents is required before publication. Whole-PR
acceptance, exact-head hosted checks and native qualification remain distinct.
