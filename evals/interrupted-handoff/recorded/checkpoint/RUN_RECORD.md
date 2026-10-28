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
