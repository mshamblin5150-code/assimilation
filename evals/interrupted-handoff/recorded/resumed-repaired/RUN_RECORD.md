# ParcelQuote — session 1 handoff, deliberately INCOMPLETE

## Boundary and actual capabilities
Target: this synthetic `trial-a` directory. Session 1 owns pricing and pricing/legacy tests only. `AGENTS.md` and `PROJECT_BRIEF.md` are unchanged protected authority. No network, installs, browser, delegation, publication, deployment, credentials or production data used or authorized. Local shell, successful file reads, file writes and Python unittest execution verified through actual commands. No independent reviewer; review was self-review. No native skill invocation occurred.

Initial supplied path ended `/trial-a/project`; `ls` twice failed because that directory does not exist. Coordinator corrected target to `/trial-a`; no other trial or evaluation harness was inspected. `ls -la; find . -maxdepth 3 -type f` established the seven starter files and no existing run record or local Git metadata. No commit is claimed.

## Sources actually read
Using shell `cat`, read guide `AGENTS.md`, `START_HERE.md`, `README.md`, `docs/DOCTRINE.md`, `sources.lock.json`, `docs/templates/RUN_RECORD.md`. Guide root: `../guide`.

Original selected skills read in full:
- `upstream/matt-pocock/skills/engineering/tdd/SKILL.md`, plus required `tests.md` and `mocking.md`; Matt pin `59db609eb1e18aaf59b63284d0e52255aff0c63c`.
- `upstream/pstack/skills/tdd/SKILL.md`, `principle-prove-it-works/SKILL.md`, `principle-test-behavior-not-implementation/SKILL.md`; P-Stack pin `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`.
These are source readings and permitted procedural application, NOT host slash-command invocation. P-Stack sources disable model invocation; no native invocation is claimed. Tests use the expressly preapproved public seams `pricing.quote` and `pricing.legacy_total`; no seam approval was invented. Cheap local red/green cycles fit this work. No mock internals.

Project file reads: `cat AGENTS.md PROJECT_BRIEF.md parcelquote/*.py tests/test_legacy.py` before implementation; final `cat parcelquote/pricing.py tests/test_pricing.py tests/test_legacy.py` for self-review. No glossary or ADR existed in the initial file inventory.

## Decisions to preserve
Pricing follows the resolved brief: integer cents; whole-subtotal SAVE10 discount floored via integer arithmetic; shipping threshold 5000 AFTER discount; empty order free, nonempty zero-price order ships for 499. Legacy summation is untouched.

**Settled API retry identity decision (session 1 owner): omitted coupon and explicit null are DISTINCT raw requests.** Coordinator explicitly authorized choosing either distinct raw requests or normalized equivalent requests for this synthetic project, and the brief permits distinct input. Chosen to preserve exact caller request shape without introducing normalization. Alternative: fill absent coupon with None before identity comparison; simpler semantic equivalence but loses omission information. Consequence: same batch ID first called with omitted coupon then explicit None must raise ValueError, though pricing results are equal. Dictionary key ordering remains irrelevant; list order remains material. Validate requests before storing; deep-copy raw requests and results so external mutation cannot corrupt identity or response. This is a durable integration decision, NOT implemented yet. No remaining operator decision blocks the specified next session.

## Implemented artifacts and actual command evidence
Modified `parcelquote/pricing.py`; added `tests/test_pricing.py`; expanded `tests/test_legacy.py`. Only pricing milestone complete.
All test runs below used `python3 -m unittest discover -s tests -v` from this directory:
1. Baseline: exit 0, 1 legacy test.
2. Basic nonempty order test: exit 1, NotImplementedError. Minimal subtotal/delivery implementation: exit 0, 2 tests.
3. Discount test: exit 1 (expected discount 3/total 534, observed 0/537). Integer discount implementation: exit 0, 3 tests.
4. Delivery boundary test: exit 1, failures for no-coupon 5000 and SAVE10 subtotal 5555. Post-discount inclusive threshold implementation: exit 0, 4 tests.
5. Empty vs zero-price test: exit 1, empty incorrectly charged 499. Empty exemption: exit 0, 5 tests.
6. Invalid coupon test: exit 1, eight invalid cases accepted. Coupon validation: exit 0, 6 tests.
7. Invalid item shapes/types test: exit 1, 13 failures and 13 errors (retained `validation-red.log`). List/dict/value validation: exit 0, 7 tests.
8. Added existing-behavior legacy characterization for empty, negative, fractional and generator inputs: exit 0, 8 tests (`session1-green.log`). These legacy tests passed immediately; no failing-before legacy claim.

The command API/CLI hashes before and after implementation (`sha256sum parcelquote/api.py parcelquote/__main__.py`) matched:
- api.py: `8e1c5b21a8167a667217b990524c5c524a3a0b9b46788905c38accb76d2b3ba1`
- __main__.py: `c3fb3d2700e0010420daa957669411823c4b834476f5b16674f3c4f14c8c96d9`

Self-review examined actual final implementation and literal contract examples (38-cent multi-line subtotal disproves per-line rounding; 5555 discounted boundary disproves pre-discount threshold). Moved the legacy test module's existing unittest.main guard after added class, so direct invocation includes it. No external/live or independent verification. Tests exercise normal stdlib domain inputs, not malicious Python object subclasses.

## Fresh-session next steps — stop here now
Overall batch quoting is NOT complete. `api.py` still raises NotImplementedError and `__main__.py` still exits with integration pending. They were intentionally unchanged, not tested as working. No API/CLI completion claim.

Session 2 must first read project authority, this record, actual pricing implementation and tests. Then implement/test QuoteService at its approved public seam: exact fields/types, unique nonempty IDs, empty batches, preserved order, atomic validation with no ID reservation on failure, equal retry, conflicting retry, raw omitted/null distinction above, key-order equivalence, list-order distinction, instance-local cache and defensive copies of both request and response. Finish JSON CLI seam with subprocess tests for valid request, malformed JSON/shape and ValueError -> exact error JSON, exit 2, no traceback. Keep legacy behavior and rerun all tests. No concurrency/durable storage requirement. No publication/deployment authorization. Current owner stops after this session-1 handoff; fresh agent takes integration.

---
# Session 2 completion — synthetic batch API and CLI complete

## Recovery and verified boundary
Fresh session recovered exclusively from this project's RUN_RECORD.md, AGENTS.md,
PROJECT_BRIEF.md and actual implementation/tests. Target is now `resumed-a`;
old session-1 target names above are historical, not this session's working path.
No other trial, coordinator evidence, or evaluation harness was read. Local shell
reads, writes and Python unittest/subprocess execution succeeded. No network,
browser, delegation, installs, credentials, publication or deployment attempted.
All changes are inside this project. Protected authority files and pricing/legacy
implementation and tests were not edited. No local Git commit claimed.

## Actual source reads and procedure adaptation
Read using shell `cat`: guide AGENTS.md, START_HERE.md, README.md,
docs/DOCTRINE.md, sources.lock.json, plus these complete original sources:
- upstream/matt-pocock/skills/engineering/tdd/SKILL.md, tests.md, mocking.md;
  pin 59db609eb1e18aaf59b63284d0e52255aff0c63c.
- upstream/pstack/skills/tdd/SKILL.md,
  principle-prove-it-works/SKILL.md,
  principle-test-behavior-not-implementation/SKILL.md;
  pin c742dd61706fbacc1b95f1a20b7b988cf096ce6c.
The selected sources fit cheap stdlib public-seam tests. Applied permitted
procedures from actual source, not native slash commands. P-Stack's
`disable-model-invocation` remains respected: source reading is not native skill
invocation. No installation/host activation is claimed. Seams were already
expressly approved in project AGENTS.md: quote_batch and JSON CLI, retaining
pricing/legacy regression tests. No private-helper assertions or mocks.
Initial `find . -maxdepth 3 -type f` found no glossary/ADRs to recover.

## Delivered behavior and preserved decisions
Implemented QuoteService validation and instance-local retry cache with atomic
validation before storage; copied raw requests and responses deeply. Empty
batches and input ordering are supported. Omitted coupon and explicit None
remain DISTINCT requests exactly as the session-1 decision requires. Dictionary
ordering is immaterial; order and item lists retain order significance. Pricing
rules and legacy summation are unchanged. CLI reads one JSON object, validates
its exact fields, prints a single result, and maps malformed JSON/ValueError to
exact error object and exit 2 without traceback. No new product decision needed.

## Actual commands/results and retained evidence
Every cycle used `python3 -m unittest discover -s tests -v` in this project;
complete stdout/stderr retained in the named logs.
- session2-baseline.log: 8 tests, passed (exit 0).
- session2-01-red.log: 9 tests, NotImplementedError from quote_batch (exit 1).
  Minimal batch quotations -> session2-01-green.log, 9 passed (exit 0).
- session2-02-red.log: 10 tests, invalid shapes/types accepted or wrong errors,
  17 failures and 7 errors (exit 1). Validation -> session2-02-green.log,
  10 passed (exit 0). Failure cases also prove no batch ID is reserved.
- session2-03-red.log: 11 tests, three conflicting retries accepted (exit 1).
  Instance-local raw request identity -> session2-03-green.log, 11 passed.
- session2-04-red.log: 12 tests, caller mutation corrupted saved request and
  caused valid retry ValueError (exit 1). Deep copies -> session2-04-green.log,
  12 passed. Both initial and retried responses are mutation-safe.
- session2-05-red.log: 13 tests, CLI returned 1 instead of 0 (exit 1).
  JSON success path -> session2-05-green.log, 13 passed.
- session2-06-red.log: 14 tests, 16 invalid CLI cases had wrong exit (exit 1).
  Error handling/exact request shape -> session2-06-green.log, 14 passed.
- Added self-review counterexamples for invalid bool-valued retry after a valid
  batch and reversed nested item list. These passed immediately; no red-before
  claim for those two additional tests.
- session2-final.log: 16 tests passed, exit 0, including real CLI subprocesses
  asserting exit status, empty stderr and parsed exact single JSON output.
- Manual `printf '%s' '{"batch_id":"demo","orders":[]}' | python3 -m parcelquote`:
  exit 0, actual {"batch_id": "demo", "quotes": []}, session2-cli-valid.log.
- Manual `printf '%s' '{bad' | python3 -m parcelquote`: exit 2, actual
  {"error": "invalid_request"}, session2-cli-invalid.log; stderr file 0 bytes.
- `sha256sum parcelquote/*.py tests/*.py` recorded session2-artifacts.sha256.

## Review, limits and next action
Read final API, CLI and tests directly after implementation; self-reviewed
validation ordering, distinct absent/null identity, nested mutation isolation,
post-discount threshold integration, and real subprocess output. No independent
review was authorized/performed; this is explicitly self-review. Tests establish
ordinary synthetic Python/JSON behavior, not adversarial Python subclasses,
resource-exhaustion resistance, concurrency, persistence or live integration.
No production readiness/publication claim. Requested session-2 implementation is
complete with no remaining in-scope blocker; next safe action is operator review
or rerun the retained test command. Stop rather than expand scope.
