# Growing-project architecture lab

Start with [the lesson](../../docs/CHAD-ARCHITECTURE-UPKEEP.md). This is a tiny,
fictional preview-only organizer, separate from `../chad-organizer/`. It creates
its own temporary synthetic files and proposes destinations. It never moves
those files. Temporary-fixture cleanup removes only the runner's own fixture.

Use an already available trusted Python 3.10+ interpreter. No dependency install,
account, network connection, OS change or real folder is needed. The examples
below run from the Assimilation repository root; use `python3` if that is the
verified interpreter on your machine.

```sh
python -B examples/chad-architecture-lab/demo.py --stage 03-tangled
python -B examples/chad-architecture-lab/demo.py --stage 03-tangled --scenario repeat
python -B examples/chad-architecture-lab/demo.py --stage 05-casefold --scenario repeat
python -B examples/chad-architecture-lab/demo.py --stage 05-casefold --scenario uppercase
python -B examples/chad-architecture-lab/verify_lab.py
```

The demo accepts only named stages and three fixed scenarios. It accepts no
folder to organize. `earlier_plan_stable: false` in the tangled repeat scenario
is the deliberately demonstrated bug, not a failure to run the demo. The
`input_files_preserved` observation covers the synthetic file names and bytes;
it is not a claim about every filesystem property.

## Read one small change at a time

| Stage | Observable contract and teaching purpose |
| --- | --- |
| [01-start](stages/01-start/preview.py) | `preview(folder)` returns `rows`; `.txt` is Text and unknown files are Keep. |
| [02-category](stages/02-category/preview.py) | Add `.jpg` as Images. Existing text/unknown and preservation checks survive. |
| [03-tangled](stages/03-tangled/preview.py) | Add `counts`. Deliberately seeded duplicate classification and shared result storage still pass four single-call checks. |
| [04-deepened](stages/04-deepened/preview.py) | Independent returned plans and one classification decision; counts derive from those rows. |
| [05-casefold](stages/05-casefold/preview.py) | Case-insensitive extensions work in both rows and counts. |

Rows contain `source`, `category` and `destination`; Keep has a `None` destination.
Only direct child files participate, ordered by name. From stage 03, `counts`
contains each category present in the plan and its count. A returned plan should
not change when another preview runs. Stage 03 intentionally violates that last
expectation. Neither dictionary mutability nor a real apply/undo operation is
part of the lesson's contract.

The initial stage and its characterization checks were authored together as a
starting fixture, not advertised as test-first. New category, summary, isolation
and uppercase expectations each have genuinely observed red/green output.
The summary was initially implemented simply; **the two bad shortcuts were
then inserted deliberately**. They are not attributed to TDD or to an unguided
model. See [the evidence chronology and limits](evidence/RESULTS.md).

## Pause for the two surveys

1. After stage 03, inspect [survey 1](reports/survey-01.html). First ask where
   the rule lives and what a later call can change. A green test suite did not
   answer those questions. The survey offers candidates, not a silent rewrite.
2. **Your choice:** explore result ownership, explore duplicated classification,
   or defer a structural change. An observed behavior bug still needs its own
   disposition. In a real project, the human owner decides; record significant
   design reasons using that project's ADR convention.
3. The supplied worked example fixes ownership first, then consolidates the
   summary during review. This is an authored teaching decision, not Chad's
   answer. One local result avoids a hidden ordering rule; deriving counts
   removes a second classification rule. A plug-in hierarchy is deferred because
   no second implementation or configuration requirement exists.
4. After stage 05, inspect [survey 2](reports/survey-02.html). It recommends no
   further architecture refactor for the current scope. More machinery would
   not create useful leverage.

The reports preserve two independent source-reading surveys. They use inline
CSS/SVG, without external assets, as an explicit adaptation of Matt's report
scaffold. These copies do not run a survey when opened. Static structure was
checked; browser rendering was blocked in the authoring executor, so visual
layout remains unverified. See [results](evidence/RESULTS.md).

## Replay an exact red, then green

These two commands run the same assertion against two implementations. The first
should exit **1** with the uppercase behavior assertion; the second should exit
**0**. An import error or a different assertion is not the intended red.

```sh
python -B examples/chad-architecture-lab/checks.py --stage 04-deepened --case test_uppercase_extensions_have_matching_rows_and_counts
python -B examples/chad-architecture-lab/checks.py --stage 05-casefold --case test_uppercase_extensions_have_matching_rows_and_counts
```

`verify_lab.py` replays all declared outcomes. It requires exactly the named
failures and matching behavioral messages, with no errors or skips. Unexpected
passes also fail verification: if someone repairs a deliberately broken stage,
the lesson must be updated rather than pretending it still demonstrates red.
It does not use `expectedFailure`, blanket skip rules or disabled assertions.

The verifier also makes a temporary source copy without case normalization,
checks that the uppercase test fails, discards that copy and reruns the unchanged
original. **The tracked final source is never mutated, so no restoration of that
file is needed.** This checks one defect's sensitivity, not a general mutation
score. Its literal mutation target must be reviewed if the implementation changes.

The same verifier is included in root offline tests through
[`test_chad_architecture_lab.py`](../../tests/test_chad_architecture_lab.py).
No existing organizer test or workflow is weakened.

## Scope and stopping point

The public `preview(folder)` seam is exercised only with disposable fixtures.
It can be imported by Python, but that is not authority to inspect personal
folders. The lab is not an OS sandbox and does not qualify symlinks, hostile
filesystem races, concurrent changes, permissions, large-directory performance,
Windows file moves, installation, clinical use, deployment or agent obedience.

Two rounds rehearse a manual architecture-review habit; they are not two elapsed
days and install no recurring job. Keep all existing product, clinical,
security/data and teardown holds. Stop when you can explain the behavior defect,
the structural friction, the chosen improvement and its evidence—not when a
dashboard reports a flattering score.
