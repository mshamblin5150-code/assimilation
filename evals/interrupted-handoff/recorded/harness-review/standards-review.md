# Standards / adversarial harness review

Scope: new `evals/interrupted-handoff/` and `tests/test_interrupted_handoff.py` over checkout HEAD `16957ae87622ddf43c172defcdad5264167c6da2`. Original reviewed hashes: `standards-reviewed-sha256.txt`. No trial implementation was edited or graded by this reviewer.

Read: root AGENTS/README/DOCTRINE/SWARMS; original Matt TDD (including tests/mocking), code-review and handoff; original P-Stack swarm, prove-it-works and test-behavior-not-implementation. Approved public seams and synthetic-only authority are explicit. Local Python execution is not a security sandbox; documentation accurately distinguishes instruction scope, self-reported traces, actual delegation, and separate approval boundaries.

## Finding and correction

**P2, confirmed false positive:** original `probe.py` invalid-batch cases omitted a distinct valid first order followed by invalid pricing data. An implementation caching each successfully priced order, with duplicate-ID prevalidation, passed the entire original oracle but reserved a failed batch ID. Reproduction retained in `standards-atomicity-repro.py` and its original log. This violates the public atomicity contract and P-Stack's behavior-breaking mutation criterion.

Coordinator authorized a narrow correction after this finding: new late-invalid-order probe and calibration mutant. Also incorporated the independent trial challenger's large-output/deep-JSON discoveries as two further post-trial oracle amendments. These changes are **not preregistered probes** and do not alter the original manifests or erase original scores.

Three sequential test-first slices retained red/green logs: atomicity (16 tests), large CLI integer product (17), deep invalid JSON (18). Final calibration: **18/18 pass**, `standards-deep-cli-green.log`. Known-good calibration CLI now supports arbitrary integer serialization and handles RecursionError. Large-output expectations use tagged decimal integer tokens, not participant arithmetic or a lossy string/numeric comparison. Deep input uses 10,000 nesting levels: 1,200 levels parse successfully in the actual runtime, so the intermediate unsuccessful calibration is retained rather than concealed.

## Remaining limits

No known remaining blocking Standards violation or demonstrated false negative. Calibration is finite, not exhaustive correctness/security proof. The original oracle cannot validate real agent history, fresh-context isolation, red-before-green history, or delegation provenance; separate retained evidence must establish those claims. Grading with the amended harness is a post-trial re-evaluation. RESULTS/claim documentation was not available during this review and awaits a separate pass.

No product, clinical, security/data, publication, deployment, or teardown approval hold changed. No external actions, installs, network access, or upstream scripts executed.
