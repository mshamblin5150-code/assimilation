# ADR 0008: exact approval and recoverable practice moves

- Status: Accepted for the bounded tutorial implementation; operator acceptance pending
- Date: 2026-10-31
- Owner: Chad tutorial implementation, under the operator's approved build request

## Context
Chad needs a complete nonclinical example connecting a skill to useful code and tests. Moving personal files would exceed the approved demonstration. Preview changes can become stale and interrupted moves can leave partial work.

## Decision
Use deterministic extension categories and fingerprints, a separate read-only preview phase, explicit approval of that exact preview ID, fresh input comparison, exclusive journal creation, intent-before-move records and conservative undo. Bound the exercise to small local Windows practice folders; reject links/junctions. Keep optional PDF content extraction separate from classification. No installer or onboarding changes.

## Alternatives considered
An AI-only prose plan cannot enforce fingerprints. Unconditional rename risks overwrite on POSIX. Copy/delete recovery introduces duplicate ownership and partial-copy states. A production transaction engine and cross-platform locking add complexity before the beginner understands approval. These are deferred rather than claimed solved.

## Consequences
The baseline needs no third-party package, is inspectable, and keeps operator choices visible. Windows-only apply/undo and a quiet local folder are deliberate limits. Partial moves require journal inspection and undo; empty directories remain. Malformed journals stop recovery rather than guessing. This is not a guarantee against power loss or concurrent hostile changes.

## Verification and references
See `examples/chad-organizer/test_organizer.py` and the run record `examples/chad-organizer/RESULTS.md` for observed checks. Tutorial links current primary PyMuPDF Office documentation. Independent review is recorded separately from author testing.
