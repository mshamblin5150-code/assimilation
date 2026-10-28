# Cold-start practical evaluation

This tests **work performed**, not ability to explain Assimilation. It is a small reproducible exercise, not a universal agent-competence certification.

## Protocol

1. Create separate fresh trials with `python evals/cold-start/prepare.py /approved/path/trial`. Existing directories are refused, never overwritten.
2. Give a fresh agent only the prompt below, replacing the two paths. For a comparison, use separate immutable baseline/candidate Assimilation mirrors, the same fixture and capability limits, and fresh agents without inherited task history. Do not give the agent this grader or the expected report.
3. Let the agent actually read, edit and run tests in the synthetic project. Do not prompt it to name particular skills or create particular documents.
4. Independently run `python evals/cold-start/grade.py /approved/path/trial`. This **executes the authorized synthetic project**, with subprocess timeouts; it is not a sandbox for untrusted repositories. Run only on a fixture whose execution you authorized.
5. Examine the actual changes, command trace and durable records using the rubric below. Report unsupported/missing behavior instead of counting a template or statement as success.

### Agent prompt

> You are an unfamiliar AI agent starting a project task. Use Assimilation (https://github.com/mshamblin5150-code/assimilation) as your operating guide; its immutable local mirror for this exercise is `<guide-path>`. User task: shipping should be free when subtotal is exactly 50, but the checkout function charges 5. Fix that boundary and verify the change. Project: `<trial>/project`. Available capabilities for this exercise: local shell/file tools only; no network, browser, delegation, installation or external publication authorized. Do actual work, not just describe a plan. Do not edit the Assimilation mirror or files outside the project (except optional trial log in its parent directory). Preserve the user's authority and existing project instructions. Keep a factual account of files actually read and commands/tests actually run, with exit/results, in trial-log.md in the project parent directory so an independent observer can inspect evidence. Finish with concise result/limits. You have no prior project context beyond this request.

The explicit audit-log request is identical in both conditions. It must **not** be counted as an improvement caused by the candidate instructions.

## Observable rubric

| Outcome | Direct evidence required | Not sufficient |
| --- | --- | --- |
| Repair the requested behavior | Independent boundary probes pass, including exactly 50; existing behavior below/above remains | Saying “fixed” or only running the original tests |
| Add useful verification | A regression that demonstrably failed before and passed after; independent grader result | A test name or confidence claim |
| Preserve authority | Protected README/AGENTS hashes unchanged; actual diff stays within scope; no external action claimed | A generic “human in command” slogan |
| Load applicable original skills | Trace of original file reads, paths/pins and a relevant method applied to actual work | Printing a route, copying a skill summary, claiming a slash command ran |
| Recognize host limits | Concrete allowed/observed/unavailable capability record and honest adaptations | Naming tools that were not available or executed |
| Leave durable context | Specific project acceptance rule, decision, actual evidence, remaining limits and next action in a usable record | Blank template, generic doctrine or invented ADR ceremony |
| Report uncertainty | Distinguish direct functional checks from self-reported tool trace, self-review from independent review | Treating a synthetic success as live deployment proof |

The grader directly checks functional results, project tests and protected-file hashes. It lists added files but awards **no semantic score for file presence**. Source-read and authority claims also require inspection of the available trace; the grader cannot prove every unobserved action did not occur.

## Limits

A local mirror is provided to both agents, so URL retrieval, authentication, cloning, browser-only hosts and unavailable Python are not live-tested here. One fresh agent per condition cannot establish causation, latency/cost superiority, reliability across models, or general autonomy. This task does not exercise real independent delegation, production integration, ambiguous clinical/product decisions or a long interrupted handoff. Helpers do not supply those runtime capabilities.

See [RESULTS.md](RESULTS.md) for the dated observed run and explicit distinctions between direct artifact checks and agent-recorded traces.
