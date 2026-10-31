# Catch the tangle while your project grows

**Chad, the habit is simple: build a small change, test it, and periodically look
at whether the next change is getting harder.** Do not wait until the whole
project is a ball of mud before thinking about its design.

Tests and architecture reviews do different jobs:

- **TDD:** make one expected behavior fail in a test, implement it, then check
  that it passes. This gives you evidence about that behavior.
- **Architecture survey:** look for knowledge and state scattered across the
  code. Decide whether bringing them together would make future work easier.
- **Refactoring:** change the internal design while preserving agreed behavior.
  Keep the tests running while you do it.

Green tests are not a certificate of good architecture. A tidy design is not a
certificate that the program does the right thing. Use both, with review.

## Start with the small lab

Open the [preview-only architecture lab](../examples/chad-architecture-lab/README.md).
Its runner creates its own disposable synthetic files; it accepts no personal
folder to organize. It returns proposed rows and summary counts, never moves
files, and leaves the existing practice organizer unchanged. Follow the lab's
commands rather than pointing an example at Downloads or another real folder.

The deliberately tangled code is a teaching fixture, not production code and
not evidence that an unguided model necessarily writes bad software. The rounds
below are fictional development checkpoints, not a claim that days passed.

| Round | What changes | What to notice |
| --- | --- | --- |
| `01-start` | Preview text files; keep unknown files in place | One small behavior through `preview(folder)` |
| `02-category` | Add a picture category | Add one expectation before its implementation |
| `03-tangled` | Add summary counts, with deliberately duplicated classification and hidden mutable state | Existing single-call checks can be green while the design carries trouble |
| First survey | Inspect the code that just changed | Show the friction before choosing a repair |
| `04-deepened` | Keep classification in one place, derive counts from the plan, and isolate each preview's state | Preserve existing results; protect repeated calls with a behavior test |
| `05-casefold` | Recognize uppercase extensions too | One rule change should reach both rows and counts |
| Second survey | Inspect the new change and remaining design | Check whether the improvement helped; avoid inventing more work |

Before moving on, explain the expected preview in your own words. For example,
`garden.txt` belongs in the text category, while `unknown.bin` remains **Keep**.
The proposed destination is information, not an instruction to move the file.

## First survey: ask where change is spreading

Read Matt Pocock's actual
[`improve-codebase-architecture` skill](../upstream/matt-pocock/skills/engineering/improve-codebase-architecture/SKILL.md).
It is a **survey**, not an automatic refactoring tool. It reads the project's
domain vocabulary and relevant ADRs, then concentrates on a named area or on
paths that have changed recently. That avoids polishing dormant code merely
because it could look different.

In this lab, point it at `03-tangled`. Ask:

1. Where is the rule that decides a file's category?
2. How many places must agree when that rule changes?
3. Can an earlier preview affect a later preview?
4. Which behavior can a caller actually observe and test?

The survey presents candidates with affected files, a concrete problem, a
possible improvement, before/after diagrams, and a recommendation strength:
**Strong**, **Worth exploring**, or **Speculative**. It then stops for your choice.
It should not silently turn the first suggestion into a rewrite.

The worked example chooses one improvement: keep the preview's decisions and
state together behind the existing interface. That choice is part of this
authored exercise, **not a record of Chad choosing a design for his own project**.
On a real project, you can choose a candidate or defer it. Deferring a design
change does not excuse an independently demonstrated behavior bug.

Use the [one-decision working method](OPERATOR_METHOD.md) when choices need
discussion. Record significant decisions and reasons in the project's ADRs;
use its existing glossary. Assimilation's canonical glossary is
[`CONTEXT.md`](../CONTEXT.md), not a second `GLOSSARY.md` created by this lesson.

**Checkpoint:** you can name the friction, the selected improvement, its cost,
and what will stay unchanged. A survey report alone does not authorize the work.

## Make the change with a safety net

The lab's agreed test seam is `preview(folder)`: observe the returned plan and
counts, plus preservation of the synthetic input files. It does not test a real
file-moving tool, host permission enforcement, or whether an agent obeys prose.
Agree new seams with the project owner before expanding beyond this exercise.

For a new behavior, follow the actual
[`tdd` skill](../upstream/matt-pocock/skills/engineering/tdd/SKILL.md):

1. Write **one** test with an expected result worked out from the requirement,
   not copied from the implementation's output.
2. Run it before changing the implementation. Verify that the failure concerns
   the missing behavior, not a broken import or test-discovery mistake.
3. Make the smallest change that satisfies the expectation.
4. Rerun that check and the relevant existing checks. Keep the actual output.

Then review the design and refactor in small, checked steps. The pinned Matt
skill calls the implementation loop **red–green** and puts refactoring in the
review stage. Tests through the public interface should survive an internal
reshape that keeps the promised behavior unchanged.

For existing code, characterization tests capture behavior you intend to keep.
Writing them after the code is useful, but it is not retroactive TDD. Likewise,
the supplied stage files are teaching checkpoints, not an invented historical
commit sequence. The lab's [evidence record](../examples/chad-architecture-lab/evidence/RESULTS.md)
identifies the newly observed test-first cycles, checks, and limits.

Finally, try a deliberately broken condition in the disposable lab. The relevant
test must fail for the expected behavioral reason. Restore the condition and
rerun it. A test that cannot detect the defect gives you false reassurance.
An expected demonstration failure is distinct from an unexpected suite failure;
do not hide the latter or weaken assertions to make the screen green.

**Checkpoint:** explain which test caught the broken behavior, which tests
survived the refactor, and what those results still cannot establish.

## Second survey: inspect the next ordinary change

Now add uppercase-extension handling. Does the same classification decision
serve the rows and their summary? Can you explain what state a preview depends
on without remembering the last call?

Compare concrete evidence before and after:

| Question | Evidence to record |
| --- | --- |
| Did the requested behavior work? | Named acceptance checks and actual results |
| Did old behavior survive? | Unchanged regression checks and preserved fixture bytes/paths |
| Would the test catch a defect? | Named deliberate defect, meaningful failure, restored pass |
| Did knowledge become more local? | Separate classification rules and logical edit locations |
| Did reading become simpler? | Hidden mutable state and unnecessary indirections to trace |

Matt's vocabulary calls the payoff **locality** when a rule, its changes, and
its verification concentrate in one place. A **deep module** provides useful
behavior through a small interface. More files, classes, or lines do not by
themselves make a module deeper.

The second survey may find no worthwhile change. Do not create an abstraction
just to produce a finding. Keep speculative candidates separate from demonstrated
friction, especially when nothing in that area is likely to change soon.

## Take the habit to an active project

Matt's [source README](../upstream/matt-pocock/README.md#4-we-built-a-ball-of-mud)
recommends the survey once every few days and warns that it will not untangle
an arbitrary old codebase for you. **Every couple of days is a reasonable manual
starting habit while you are actively changing a project**, not a proven optimum
or a promise that problems cannot accumulate between reviews. Adjust to the
amount of change; also consider a survey before a substantial new feature.

Two lab checkpoints rehearse that habit in one sitting. They do not measure a
two-day interval. This lesson creates no reminder, recurring job, or DAVID
automation and changes no existing schedule.

If your host has registered the user-invoked command, explicitly request
`/improve-codebase-architecture`. Otherwise ask the agent to read and follow the
original source within the tools and permissions it actually has. The source
sets `disable-model-invocation: true`; reading Assimilation does not install the
command or activate an unattended mode.

A useful request is:

> Use the original improve-codebase-architecture workflow to survey the area I
> have been changing for this feature. Read our glossary and relevant ADRs.
> Show concrete candidates and their trade-offs, then stop for my choice before
> changing implementation. Keep all existing permission and review gates.

The original report scaffold uses Tailwind and Mermaid from CDNs. The lab's
portable teaching reports use **inline CSS/SVG instead**, an explicit offline
adaptation. A copied report is an example, not proof a fresh survey ran. A live
survey should report its actual source revision, artifact location, and checks;
do not assume it opened correctly just because an HTML file was written.

## What each skill contributes

| Source to read when needed | Its job here |
| --- | --- |
| [Improve codebase architecture](../upstream/matt-pocock/skills/engineering/improve-codebase-architecture/SKILL.md) | Find and present candidates; preserve the human choice |
| [Codebase design](../upstream/matt-pocock/skills/engineering/codebase-design/SKILL.md) | Explain module depth, seams, leverage, and locality |
| [TDD](../upstream/matt-pocock/skills/engineering/tdd/SKILL.md) and [code review](../upstream/matt-pocock/skills/engineering/code-review/SKILL.md) | Protect observable behavior; review specification and standards separately |
| [Writing for Agents](../upstream/matt-pocock/skills/productivity/writing-for-agents/SKILL.md) | Give the agent precise triggers, scope, and completion criteria without a wall of repeated rules |
| P-Stack [test behavior](../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md) and [minimize reader load](../upstream/pstack/skills/principle-minimize-reader-load/SKILL.md) | Catch observable defects while reducing hidden state and needless indirection |
| P-Stack [prove it works](../upstream/pstack/skills/principle-prove-it-works/SKILL.md) | Inspect the actual artifact and keep rerunnable evidence |

The lab's `AGENTS.md` expresses its working scope and points to relevant sources.
That is guidance, not an operating-system sandbox. A passing Python test does
not prove an agent loaded those instructions, obeyed them, or will do so on every
run. Instruction-following needs its own controlled scenarios and observations,
as explained in [Writing for Agents and TDD](CHAD-TDD.md#test-instructions-with-observable-scenarios).

This lesson uses Assimilation's preserved Matt source at
`59db609eb1e18aaf59b63284d0e52255aff0c63c` and P-Stack source at
`c742dd61706fbacc1b95f1a20b7b988cf096ce6c`, recorded in
[`sources.lock.json`](../sources.lock.json). Sources remain unchanged reference
material; source-guided use is not a claim that native commands or complete
host-specific workflows ran.

**Done when:** you can distinguish a behavior failure from a design problem,
explain why the selected refactor helps the next change, read the supporting
test evidence, and decide when another survey is useful. This is a controlled
lesson, not a measured productivity comparison or a guarantee against bugs.
