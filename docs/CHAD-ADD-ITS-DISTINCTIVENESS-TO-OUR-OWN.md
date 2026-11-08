# Add Its Distinctiveness to Our Own

**Chad's next Assimilation lesson: turn a verified discovery into an independent, useful capability.** The previous lab, [Assimilation Living Up to Its Name](CHAD-REVERSE-ENGINEERING.md), taught you to inspect a compiled program and demonstrate a behavior. This lesson teaches the next step: decide what is worth learning, translate the principle into a new design, implement it independently, and prove the result works.

> **The central rule:** Assimilate understanding, not somebody else's source code or permissions.

You can complete the offline exercise on Linux or Windows with Python 3.12+ and the included synthetic fixtures and tests. No printer, account, Android SDK, network connection, real patient data, or external software is needed. Use a disposable local practice checkout or worktree. The lab does not approve changes to a production project, connection to a real 3D printer, or publication on your behalf.

## What you should be able to do afterward

1. Distinguish **direct observation** of the old program from your interpretation of its behavior.
2. Identify a useful **general principle** without copying an implementation.
3. Decide how that principle should change to fit a different problem.
4. Specify and test the **new program's public behavior** before implementing it.
5. Produce evidence that another reader can reproduce, including unsuccessful checks and limitations.

Read the original [Diagnosing Bugs](../upstream/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md), [TDD](../upstream/matt-pocock/skills/engineering/tdd/SKILL.md), [Prove It Works](../upstream/pstack/skills/principle-prove-it-works/SKILL.md), and [Test Behavior, Not Implementation](../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md) sources. They provide methods, not automatic tool activation. The original [Teach](../upstream/matt-pocock/skills/productivity/teach/SKILL.md) skill is user-invoked; ask your agent explicitly to teach you if you want that experience. Use [Matt's operator method](OPERATOR_METHOD.md) for substantive choices, retaining Chad as the owner of Chad's projects.

## 1. Start with a verified observation

The preceding lab supplies `examples/chad-reverse-engineering/fixtures/assimilation-lab.apk`. Its [author-run results](../examples/chad-reverse-engineering/RESULTS.md) report that JADX recovered this behavior from `org.assimilation.lab.RetryPolicy`: for an attempt number **below 3**, delay is **2 seconds**; for an attempt number **3 or higher**, delay is **10 seconds**. Its [instructor key](../examples/chad-reverse-engineering/instructor/README.md) contains the expected original behavior. The APK is a synthetic lab artifact, not an actual printer application.

**Your checkpoint:** before looking at the instructor key, use the previous lesson's static-analysis steps on your own copy and save evidence of what you actually saw. If you cannot run them, mark this as **provided author evidence, not my observation**. The new exercise can still proceed as a learning exercise, but do not claim you personally decompiled anything.

Now separate these concepts:

| Category | This exercise's entry |
| --- | --- |
| Observation from the synthetic APK | Its retry delay changes at a particular attempt threshold (author-verified; independently confirm when possible). |
| General principle worth considering | Start with short waits; after repeated unsuccessful attempts, wait longer. |
| New problem | A simulated 3D-printer readiness check should not poll endlessly or constantly. |
| Our independent design | Make polling bounded, let the two wait lengths be configurable, distinguish lack of evidence from exhausting the limit, and never wait or contact a real printer during the lab. |
| Unsupported inference to avoid | A behavior that exists in an APK must automatically be safe or ideal for a real printer. |

**Checkpoint:** describe the principle in your own words without naming a function, address, variable name, or byte sequence from the APK. Decide what to keep and what to change; record your reasons. You may reject the principle if evidence shows it is unsuitable.

## 2. Choose the destination: a *simulated* print-job readiness check

Imagine a status reader for Chad's 3D-print workflow. For this lesson, it receives a supplied, stable sequence of **invented snapshots**: `READY`, `BUSY`, or `OFFLINE`. It does **not** control a printer, send a job, read local credentials, open a socket, or sleep. We are designing a planning function that reports what it would have done.

The agreed exercise contract is a **training fixture**, not approval for any live design:

- `assess(observations, policy)` returns `outcome`, `checks`, `scheduled_delays_seconds`, and `last_status`. Treat these as the public contract; implementation choices are yours.
- Default policy: a maximum of **5 checks**, a planned **2-second** delay after an unsuccessful check numbered 1 or 2, and a planned **10-second** delay after an unsuccessful check numbered 3 or later. Delays are recorded **only between checks actually observed**. No delay is recorded after the final check.
- `READY` ends the assessment immediately, even if later snapshots are supplied. `BUSY` and `OFFLINE` do not end it. Status values are case-sensitive; an unknown status is an error rather than a guessed success.
- If the check budget runs out without `READY`, outcome is `exhausted`. If supplied observations end before the budget without `READY`, outcome is `incomplete`. Empty observations are `incomplete`, never `ready`.
- Consume no observation after `READY` or beyond `max_checks`, including through a sequence that records reads.
- The policy parameters are positive integers; booleans, floats, and numeric strings are invalid. Unknown status values raise `ValueError`. A string or bytes object is not an observation sequence and raises `TypeError`. The policy can be configured for a different schedule; no hardware action is part of this interface.

Why these adaptations? **The threshold idea** comes from the observed training APK. **The check budget, synthetic statuses, incomplete/evidence distinction, policy configuration, and refusal of actual I/O** are new product decisions. The copied numbers are demonstration defaults, not an assertion that a real printer needs these timings. For any live device, Chad must own a fresh design decision and test it against the actual device/API and its terms.

## 3. Predict the results before you write code

| Synthetic observations | Expected outcome | Checks | Planned delays between checks |
| --- | --- | ---: | --- |
| `READY, BUSY` | `ready` | 1 | `[]` |
| `BUSY, OFFLINE, READY` | `ready` | 3 | `[2, 2]` |
| Five `BUSY` observations | `exhausted` | 5 | `[2, 2, 10, 10]` |
| Two `BUSY` observations | `incomplete` | 2 | `[2]` |
| No observations | `incomplete` | 0 | `[]` |

**Stop and explain the boundary:** after the second unsuccessful check, the next planned interval is still 2 seconds. After the third unsuccessful check, the following interval is 10 seconds. That refers to *completed checks*, not the APK's attempt index. If you cannot explain this without referring to code, reconsider the contract before implementing it.

## 4. Practice the transfer with actual red-green evidence

Use the learner files in [`examples/chad-add-distinctiveness/starter/`](../examples/chad-add-distinctiveness/starter/). The starter's `assess` method intentionally raises `NotImplementedError`. Its tests express observable outcomes, not a prescribed algorithm. The supplied package had eight tests; the integrated exercise has fifteen, including an input sequence that detects an extra read.

From the repository root, in a clean practice environment, first record your Python version:

```powershell
python --version
python -B -m unittest discover -s examples/chad-add-distinctiveness/starter -p test_readiness.py -v
```

**RED checkpoint:** tests should run and fail because the implementation is missing; retain the actual command, output and nonzero exit code. A missing interpreter, import failure, or zero discovered tests is **not** the intended red. Do not rewrite the initial record to make it look test-first if you started differently.

Then implement the public behavior in your copy of `starter/readiness.py` **from the agreed contract**, not by pasting decompiled Java, the instructor solution, or any source extracted from a third-party application. Work in small vertical slices: early success, boundary waits, budget exhausted, incomplete evidence, invalid inputs, configurable policy. Run the same tests and record results after each meaningful change.

**GREEN checkpoint:** every behavioral test passes; the complete command and output are retained. Verify that the implementation contains no `sleep`, HTTP, printer SDK call, filesystem mutation, credentials, or device connection. If you have not actually checked, do not claim the negative.

After your own attempt, open the separately labeled [`instructor/readiness.py`](../examples/chad-add-distinctiveness/instructor/readiness.py). Compare the decisions, *not the syntax*. The point is that two implementations can satisfy the same contract without sharing internal structure.

## 5. Inspect the author's independently written worked example

The instructor's reference implementation uses a frozen policy, stops when it sees `READY`, and reports how many synthetic checks were examined and what waits would have occurred **between those checks**. Its worked results are:

```text
assess(["BUSY", "OFFLINE", "READY"])
  outcome = ready
  checks = 3
  scheduled_delays_seconds = (2, 2)

assess(["BUSY"] * 5)
  outcome = exhausted
  checks = 5
  scheduled_delays_seconds = (2, 2, 10, 10)
```

The exercise does **not** demonstrate communication with a Bambu printer or any other manufacturer. It does not establish that 2/10-second polling is optimal, that network errors are retryable, or that the target device's interface permits this design. That work, if desired, requires new evidence and scope.

A reviewer can rerun the instructor tests from the repository root:

```powershell
python -B -m unittest discover -s examples/chad-add-distinctiveness/instructor -p test_readiness.py -v
```

The provided [`instructor/TEST-RESULTS.txt`](../examples/chad-add-distinctiveness/instructor/TEST-RESULTS.txt) records the original package authoring run. Those results **do not** prove a fresh Windows host passed, that Chad completed the lesson, or that another drone independently reviewed it. Re-run them and keep new results before claiming more.

## 6. Challenge the result before calling it assimilated

Act as an independent reviewer (or ask a genuinely separate agent to do so when available). Try to falsify these claims:

1. Does an early `READY` prevent later checks and delays?
2. Is the transition from short to long delays correct at the **third completed check**?
3. Is there never a wait after a final or nonexistent check?
4. Does stopping for lack of observations produce `incomplete` rather than pretending the budget was exhausted?
5. Are bad policy and unexpected status inputs refused rather than silently coerced?
6. Does an instrumented sequence prove that no observation beyond the budget is read? A correct returned count alone does not establish this.
7. Is the work a new, explainable implementation from a documented contract rather than extracted code copied into a project?

Check real test output and code. A green test suite is evidence for its covered assertions, **not** a universal proof. Label self-review as self-review. If tests fail, retain the original failure and the fix. If a reviewer cannot execute code, label the review static-only.

## 7. Deliver an assimilation record

Give Vox or your own project coordinator a short evidence package containing:

- **Source**. exact previous fixture and its hash; your own observations or the explicit author's-results limitation.
- **Principle**. one sentence describing the design idea independent of source code.
- **Selection**. what to adopt, what to reject, and why (including license, safety, and environmental fit).
- **New contract and ownership**. what the simulated tool does, what it must never do, and who approved the training-only scope.
- **Verification**. Python version, exact commands, original red/green results, relevant code revision, independent review status, and observed limitations.
- **Transfer**. one proposed real-world application, if any, explicitly marked **not approved or integrated** until the target project's owner decides and its own checks pass.

The [traceability worksheet](../examples/chad-add-distinctiveness/TRACEABILITY.md) is provided for this handoff. Once you have your own evidence, you can compare it to the author's example. Do not replace the learner's results with the instructor's.

**Pass:** Chad can explain the origin of the idea, make an independent design choice, produce a working offline feature, demonstrate its boundary and failure cases, and show reproducible evidence with truthful attribution. **Not established:** authority to reuse other software's source; permission to reverse engineer real third-party targets; real printer compatibility; production safety; or deployment approval.

**A final question for Chad:** If you removed the APK, the decompiler and the original tool names, could you still explain the new design and verify it from its public requirements? If yes, you have brought the useful *distinctiveness* into your own understanding rather than merely copied an artifact.

## Read the integration evidence separately

The [integration results](../examples/chad-add-distinctiveness/RESULTS.md) identify
which checks Vox ran on Linux and which claims remain supplied author evidence.
They preserve a real extra-read failure in the original instructor implementation,
its regression test, the repair, and deliberate wrong implementations rejected
by the tests. They do not claim Chad has completed the lesson or a fresh Windows
run has passed. Keep your own record separate.

## Final examination

When ready for independent assessment, continue to [Harnessing the Omega Particle](CHAD-HARNESSING-THE-OMEGA-PARTICLE.md). Public learner materials do not start an examination attempt; complete its admission intake, contract receipt and host calibration first.
