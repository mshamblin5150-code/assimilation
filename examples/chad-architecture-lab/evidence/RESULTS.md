# Observed teaching evidence — 2026-10-31

These are finite synthetic observations, not a productivity experiment or a
claim that TDD guarantees architecture, safety or agent obedience. No existing
organizer code, upstream source, product, permission or automation was changed.

## What actually happened

The five stage files were authored for this exercise in one session. They are
not commits from a project that aged over several days. Stage 01 and its two
initial characterization checks were supplied as a baseline; no test-first
claim is made for that starting fixture.

Each subsequent feature/regression expectation below was added and run against
the earlier implementation **before** its repair was written. The failure was
an actual assertion about the intended behavior, not a missing module or test
discovery error. Historical text logs retain those runs; only the local lab
path in tracebacks is normalized to `<lab>`. Helper additions later changed
line numbers. Current repeatable evidence is `verify_lab.py`, not an inference
from an old log.

| Step | Actual observation |
| --- | --- |
| [Baseline](01-baseline.txt) | Two starting behavior/preservation checks passed. |
| Category [red](02-category-red.txt) → [green](02-category-green.txt) | JPG was Keep; after adding the category, all three checks passed. |
| Summary [red](03-summary-red.txt) → [green](03-summary-green.txt) | Counts were absent; the [minimal summary implementation](03-summary-minimal.py.txt) passed four checks. |
| Deliberate seeding | Shared result storage and a second classification rule were inserted into stage 03 **after** the summary green. [All four single-call checks still passed](03-tangled-green.txt). This is intentional fixture construction, not prescribed TDD practice. |
| Isolation [red](04-isolation-red.txt) → [green](04-isolation-green.txt) | A second preview changed the earlier returned rows. [The minimal repair](04-isolation-minimal.py.txt) used local result storage; five checks passed. |
| [Review-stage cleanup](04-refactor-green.txt) | Counts were derived from classified rows. The same five behavior checks passed without assertion changes. |
| Uppercase [red](05-casefold-red.txt) → [green](05-casefold-green.txt) | Uppercase files were Keep; one classification edit made all six checks pass. |

## Rerunnable verification

```sh
python -B examples/chad-architecture-lab/verify_lab.py
python -B -m unittest discover -s tests -p test_chad_architecture_lab.py -v
```

The captured [verification JSON](verification.json) reports **31 check executions**:
26 passes, exactly four intended staged failures and one intended mutant failure,
with zero errors or skips. This is not 31 distinct behaviors. The final stage
and unchanged-original-source rerun each pass six checks. The root integration
checks also exercise the demo's visible shared-state bug and rejection of a
user-folder argument.

The mutant is a real temporary source copy with case normalization removed, not
a mocked internal collaborator. The uppercase assertion must fail with its
expected behavioral message. The verifier checks that the tracked final source
bytes did not change, discards the temporary mutant and reruns that original.
No tracked-source restore operation is claimed. A crash, unexpected failure,
missing assertion, skipped check or unexpected pass fails the verifier.

## Independent architecture observations

A separate source-reading agent performed both bounded surveys using the actual
Matt architecture workflow's exploration step, adapted to the available host.
This was not a native registered slash command, a multi-vendor panel, or a claim
that every host-specific workflow step ran.

- Survey 1 independently reran all four baseline checks successfully, then
  reproduced two-folder aliasing: the first returned plan's rows changed while
  its counts did not. Original synthetic file bytes were preserved. It identified
  result ownership and duplicate classification as Strong candidates.
- Survey 2 independently reran the full verifier: 31 executions, the five
  specifically expected failures, no errors/skips, and final six-check passes.
  It found no worthwhile further architecture refactor within the agreed scope.

Source inspection supports these modest, per-implementation measurements:

| Observation | Tangled stage | Deepened/final stage |
| --- | --- | --- |
| Separate category-decision locations | 2 | 1 |
| Shared mutable returned-row containers | 1 | 0 |
| Directory traversals for rows plus counts | 2 | 1 |

The final uppercase change edits one semantic production rule. Tests, docs and
evidence are additional edits. These counts are not measured speedups, universal
complexity scores or counts across all retained historical teaching stages.

The two offline HTML reports were generated first in the OS temporary directory,
then preserved under `reports/` as teaching copies. Static HTML structure,
inline diagrams and absence of external scripts/assets were checked. A headless
Chromium render attempt stopped before page load because the executor refused
process-singleton socket creation (`Operation not permitted`). It was not
retried or worked around with permission changes. **Visual rendering remains
unverified**; source checks are not claimed as browser QA.

## What remains outside the evidence

The preview tests observe returned results and synthetic file names/bytes. They
do not establish hostile-link/race confinement, live filesystem stability,
native Windows moves, installation, agent instruction-following or safety on
personal folders. The manual every-couple-days habit was not experimentally
validated. No scheduler or reminder was created.

The original practice organizer retains its own separate evidence and limits.
The lesson's worked design selection is an authored example approved for the
lesson, not a recorded decision by Chad about his real project.
