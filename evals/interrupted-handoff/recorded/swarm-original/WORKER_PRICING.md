# Pricing worker evidence — 2026-10-28

## Boundary and ownership
Real child agent `swarm_trial_coordinator/pricing` owned only `parcelquote/pricing.py`,
`tests/test_pricing.py`, and this record. Acknowledged this ownership by actual
collaboration message before editing. Coordinator confirmed separate API worker
acknowledged the four-field result and ValueError contract. No overlapping edits,
collisions, network, installation, publication, or other-project reads occurred.
Shell tests necessarily created normal Python bytecode caches inside this project.

Read project AGENTS.md and PROJECT_BRIEF.md directly. Their approved seams are
`pricing.quote` (pricing and invalid-input behavior) and `pricing.legacy_total`
(backward compatibility); these do not prove API retries or CLI transport.
The brief already settles after-discount delivery thresholds, floor rounding on
whole subtotal, exact coupon, empty-order distinction, and integer domain.
No new product decision or separate ADR was necessary.

## Original sources actually read
Paths relative to immutable guide:
- `upstream/matt-pocock/skills/engineering/tdd/SKILL.md`, `tests.md`, `mocking.md`.
  Matt pin read from sources.lock.json: `59db609eb1e18aaf59b63284d0e52255aff0c63c`.
- `upstream/pstack/skills/principle-prove-it-works/SKILL.md`.
- `upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md`.
  P-Stack pin: `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`.

Applied permitted source procedures, not native slash commands. P-Stack sources
have disable-model-invocation frontmatter; the project explicitly requested these
methods. Used public-seam tests with literal expected examples and no mocks.
Read and shell execution verified through successful actual commands; edits
verified by reading final pricing.py and rerunning tests. No external capabilities
were tested or needed.

## Actual red/green command evidence
Working directory is this target. Every row used the exact command
`python -m unittest discover -s tests -p test_pricing.py -v` after adding one
behavior test and again after its narrow implementation. Command stdout/stderr
was observed in tool results; table retains outcomes (not invented full logs).

| Increment | Observed RED exit 1 | Observed GREEN exit 0 |
|---|---|---|
| Line quantities / ordinary delivery | 1 test, NotImplementedError | 1 test OK |
| Whole-subtotal floor discount | 2 tests, 1 failure: 537 vs 534 | 2 tests OK |
| After-discount free delivery threshold | 3 tests, 2 subtest failures: shipping 499 vs 0 | 3 tests OK |
| Empty vs nonempty zero-price order | 4 tests, 1 failure: empty charged 499 | 4 tests OK |
| Item container and exact key shapes | 5 tests, 3 failures and 6 errors (TypeError/KeyError instead of ValueError) | 5 tests OK |
| Domain integer and range validation | 6 tests, 9 failures and 4 errors | 6 tests OK |
| Exact coupon validation, including empty items | 7 tests, 8 subtest failures | 7 tests OK |

Then added two regression/verification tests for unchanged legacy empty, negative,
fractional and generator inputs, and large integer arithmetic. They passed
immediately; no false claim of red for already-correct behavior.
Final exact scoped command above: **9 tests, OK, exit 0**.
`python -m unittest discover -s tests -p test_legacy.py -v`:
**1 test, OK, exit 0**.
Read final `parcelquote/pricing.py` using `cat`; legacy_total remains exactly
`return sum(prices)`. Result uses integer arithmetic, no input mutation, and
exact four keys. Initial coordinator concurrent suite observed an in-progress
red, not an edit collision or terminal integration failure.

## Handoff / limits
Sent actual pricing-ready message to coordinator. API/CLI integration and
independent challenge belong to coordinator and other agents; this worker makes
no API-completion claim. No interruption or unresolved pricing issue. Scoped work
is complete; worker stops here. This one synthetic trial is not evidence of
universal swarm superiority or production readiness.
