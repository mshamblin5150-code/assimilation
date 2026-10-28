# API / CLI worker record

## Scope and authority
Actual child `/root/complete_visible_skills/swarm_trial_coordinator/api_cli` owns only
`parcelquote/api.py`, `parcelquote/__main__.py`, `tests/test_api.py`, `tests/test_cli.py`,
and this record. Parent owns integration and RUN_RECORD. Pricing sibling owns
pricing and its tests. Read AGENTS.md and PROJECT_BRIEF.md; protected files unchanged.
Only local stdlib Python and filesystem used. No network, install, credentials,
publication, deployments, or other trial reads. Filesystem edits and test execution
verified by actual shell calls. No glossary/ADR was present in initial file inventory.

Ownership acknowledgement sent to coordinator before edits: public dependency
`pricing.quote(items, coupon=None)` returns exactly four integer fields or ValueError;
no pricing edits or internal mocking. Coordinator later confirmed pricing readiness.
Live dependency already passed when first nonempty API test was implemented.
No overlapping file edits, collisions, failed tool calls or retry-after-uncertain-write.

## Original skills actually read
From immutable guide:
- `upstream/matt-pocock/skills/engineering/tdd/SKILL.md`, `tests.md`, `mocking.md`.
  Matt revision `59db609eb1e18aaf59b63284d0e52255aff0c63c`.
- `upstream/pstack/skills/principle-prove-it-works/SKILL.md` and
  `upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md`.
  P-Stack revision `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`.
- Read `sources.lock.json` directly to obtain these revisions.

Procedures applied as source-reference guidance, not a claimed native slash-command
invocation. P-Stack frontmatter disables model invocation; project explicitly asks
for these methods. Public seams are preauthorized by project AGENTS, so no redundant
user confirmation. Tests use real QuoteService and subprocess CLI, no private helpers
or internal collaborator mocks. Expected numerical outputs are worked brief examples.

## Settled implementation choices
Validate every full batch before cache lookup/commit: rejects bool/float inputs even
when Python equality would otherwise equate them to an earlier integer request;
failed validation reserves no ID. Store deep-copied request and response snapshots;
return fresh copy on retries. Dictionary equality ignores key order, list order stays
material. Omitted coupon and null remain distinct as permitted. Cache instance-local.
No durable/concurrent storage (explicitly out of scope). CLI catches ValueError
(including JSON decode errors), validates exact top-level keys, prints contract error
and exits 2 without traceback. Only stdlib dependencies.

## Actual red/green commands and results
All commands run from trial-b. `python -m unittest discover -s tests -p test_api.py -v`:
1. Empty batch test: exit 1 / 1 error (NotImplementedError); minimal return implemented;
   exit 0 / 1 passed.
2. Batch shapes test: exit 1 / 6 subtest failures (ValueError not raised); validate ID
   and list; exit 0 / 2 tests passed.
3. Order shapes/IDs test: exit 1 / 6 failures; validate exact keys/nonempty unique IDs;
   exit 0 / 3 tests passed.
4. Ordered quote results: exit 1 / 1 failure (empty quotes); call live pricing.quote;
   exit 0 / 4 tests passed, including SAVE10 5555 subtotal -> 5000 total/free delivery.
5. Equal retry / changed list order rejection: exit 1 / 1 failure (no rejection);
   add instance-local batch cache after validation; exit 0 / 5 tests passed.
6. Nested input/output mutation isolation: exit 1 / 1 error (mutated cached request
   caused ValueError); add deepcopy at storage and retry; exit 0 / 6 tests passed.
7. Additional atomic-failure and cache-isolation/bool/float retry checks: already
   green, exit 0 / 8 tests passed. No invented red phase or code change for these.

`python -m unittest discover -s tests -p test_cli.py -v`:
8. Successful JSON request: exit 1 / 1 failure (CLI exit 1); implement JSON adapter;
   exit 0 / 1 passed, exact output verified including 699 total.
9. Invalid JSON/request matrix: exit 1 / 8 subtest failures (exit 1, or extra-key
   request incorrectly exit 0); implement top-level validation + ValueError response;
   exit 0 / 2 tests passed. All subprocess stderr empty, exact JSON error and exit 2.

Final integration run `python -m unittest discover -s tests -v`: exit 0,
20 tests passed in 0.227s. This includes pricing sibling's 9 tests plus original
legacy test, 8 API tests and 2 CLI tests. Read both produced source modules after run.
No claim of external deployment, concurrency, persistence, performance, adversarial
unbounded-input robustness, or independent review. Coordinator arranges independent
challenge; my owned implementation is complete and I stop editing here.
