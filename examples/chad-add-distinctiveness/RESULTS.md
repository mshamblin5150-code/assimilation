# Distinctiveness lesson verification

This integration ran on Linux with Python 3.12.14. The exercise is standard-library-only and designed for Python 3.12+ on Linux or Windows. A fresh Windows execution of this exercise is untested. Supplied author logs report Python 3.13.5; they are retained unchanged and are not this worker's execution.

## Source custody

The 20,290-byte starting ZIP has SHA256 `1bfd8508884fd60106dd4b8b85d08b8862ce560063a9291e1e38e0ce2d445fa4`. [Original file hashes](evidence/supplied-author/SHA256.json) and [evidence provenance](evidence/README.md) distinguish source-author, integration and learner evidence.

At base `fd94df89107cc065442e2cd1c47bd014864a16e3`, the previous synthetic APK hashes to `5e96f0867ef17d5c975ecb4e4718a6fb11d4c18ca516c15df4c918b054f2dbc8`, matching [its manifest](../chad-reverse-engineering/fixtures/SHA256SUMS). The prior [author results](../chad-reverse-engineering/RESULTS.md), [instructor key](../chad-reverse-engineering/instructor/README.md), and synthetic [Java source](../chad-reverse-engineering/instructor/android/RetryPolicy.java) agree on 2 seconds below attempt 3 and 10 seconds at or above 3. This pass read those records and hashed the APK; it did not decompile or execute the APK.

## Actual runs and reproducible commands

Run these from the repository root, using `python` instead of `python3` where appropriate:

```text
python3 -B -m unittest discover -s examples/chad-add-distinctiveness/starter -p test_readiness.py -v
python3 -B -m unittest discover -s examples/chad-add-distinctiveness/instructor -p test_readiness.py -v
python3 -B -m unittest discover -s tests -p test_chad_distinctiveness.py -v
```

- Supplied learner rerun: 8 tests,1 failure and7 NotImplementedError errors, exit 1. [RED](evidence/starter-red.txt). Supplied instructor:8 passed, exit 0. [Original GREEN](evidence/original-instructor-green.txt). These existing suites were supplied, not newly developed test-first here.
- An added public `Sequence` witness reproduced a sixth read with a 5-check budget. The 9-test suite failed, exit 1. [Budget RED](evidence/budget-red.txt). Bounded indexing corrected that failure; 9 passed, exit 0. [Budget GREEN](evidence/budget-green.txt). The witness observes reads made on the caller's input, not a private helper.
- Expanded invalid-status checks exposed unhashable list/dictionary values raising `TypeError`. [Input RED](evidence/input-red.txt), exit 1. The boundary now consistently raises `ValueError` for unknown status values; all 15 tests pass, exit 0. [Final GREEN](evidence/final-green.txt).
- The integrated learner intentionally remains unfinished: 15 tests,25 failures and19 NotImplementedError errors, exit 1. [Learner RED](evidence/expanded-starter-red.txt). Matching test files are identical, while learner and instructor implementations remain separate.
- A controlled disposable learner-copy replay ran the same 15 tests before and after substituting the known corrected reference: exit 1 then 0. [Replay identities](evidence/replay.json), [RED](evidence/replay-red.txt), [GREEN](evidence/replay-green.txt). This verifies the teaching fixture; it is not Chad's independent implementation or a claimed historical test-first sequence. Reproduce by copying the starter directory into a temporary practice directory, running its tests, then replacing only its `readiness.py` with the instructor reference and rerunning the same command. Preserve your own work separately.
- The 15-test suite rejected each of six deliberately wrong implementations, exit 1 each: wrong threshold, missing early stop, budget over-read, invalid statuses accepted, false exhaustion and final trailing delay. [Exact mutations](evidence/mutation-results.json) and matching logs preserve those controls. Each ran in an isolated temporary copy; the checked-in instructor remains the restored good version.

Source inspection finds only dataclasses and typing imports in the assessor. A guarded execution of all 15 tests also passed with socket creation, process creation, sleeps and file writes refused. That bounded check supports this pure fixture; it is not an operating-system sandbox or permission to execute arbitrary inputs. These checks used no printer, network, credentials, patient data, real waits, production integration, or installation. Repository retrieval and publication use their separately authorized network tools; the exercise itself stays offline.

The root test invokes the actual instructor suite in a separate interpreter, rejects zero discovered tests and skips, and is discovered by existing offline PR validation. The intentionally incomplete learner is not represented as a passing implementation. Existing Windows CI covers its configured checks; it does not automatically run this new lab unless the observed job actually invokes it.

Independent review, exact-head hosted CI and publication/merge are separate records. Neither supplied logs nor local passes prove those events. PR #12's draft/merge hold, Issue #11's operator-approval requirement and all other installer, security/data, native and acceptance boundaries remain unchanged.

## Integrated repository checks and independent review

- `python3 -B -m unittest discover -s tests -v`: exit 0, 310 root tests passed on Linux. The root wrapper executes the fifteen instructor tests; these counts are nested and must not be added as unique tests. [Root output](evidence/root-suite.txt).
- `python3 -B scripts/snapshot_sources.py verify`: exit 0, both pinned sources verified without executing upstream code. [Output](evidence/snapshots.txt).
- `python3 -B examples/chad-add-distinctiveness/evidence/check_effects.py`: exit 0, fifteen tests passed with the stated external effects blocked after imports. [Output](evidence/guarded-effects.txt). This is a bounded regression check, not a general security boundary.
- Local reader links, Markdown fences, unchanged original author logs, identical learner/instructor tests, and Git whitespace checks passed.
- Independent Spec review found no remaining requirement or correctness finding. Its separate Linux execution passed the fifteen tests, root wrapper, a 4,372-case public-contract sweep and six mutation controls. Independent Standards/provenance review found no remaining standard or material smell finding. It verified original bytes, the APK hash, links and the actual root wrapper. Both corrected an evidence wording overstatement before clearance.

The reviewers examined the actual artifacts and source identities, not just this summary. [Implementation hashes](evidence/IMPLEMENTATION-SHA256.json) identify the reviewed public interfaces and tests. The independent sweep is reviewer execution evidence, not an execution by Chad or a new APK decompilation. Hosted runs, PR/head and any merge result must be verified separately at publication time.
