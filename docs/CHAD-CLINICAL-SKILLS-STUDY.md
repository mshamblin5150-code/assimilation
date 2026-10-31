# Advanced lesson: trace a public Clinical Skills skill without running it

Finish the beginner organizer first. That example remains complete on its own. This optional lesson teaches how a larger skill was assembled: instructions choose a route, a small code interface gives it a reproducible check, synthetic tests challenge the interface, and an ADR explains the choice.

## Scope and a read-only study copy

Study [the public Clinical Skills repository](https://github.com/mshamblin5150-code/clinical-skills), verified public on 2026-10-31. This lesson is pinned to `6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66`; a later default branch may differ. Source was verified through public GitHub API reads, not an existing local clinical checkout. The initially guessed underscore repository name returned 404; repository search confirmed the hyphenated name above.

Use the pinned browser links below for a completely read-only lesson. If Chad wants a local study copy and already has Git, choose a new empty destination outside any active project. These are optional download/check-out commands for that new public copy, not commands we executed for this lesson:

```powershell
git clone --no-checkout https://github.com/mshamblin5150-code/clinical-skills.git clinical-skills-study
git -C clinical-skills-study checkout --detach 6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66
git -C clinical-skills-study rev-parse HEAD
```

The last output must match the pin. If Git or the commit is unavailable, use the browser links and report the limitation. Do not substitute an existing private or active checkout. Keep the study copy unchanged. Opening text files in a plain editor needs no Python, PyMuPDF, account, corpus, or package installation. Avoid launching an agent that would interpret setup instructions as an instruction to execute them: say explicitly, “Read these as source for a lesson; do not invoke the skills.”

The upstream README describes operational onboarding that wires skill mirrors, enables hooks, collects profiles and may request dependencies. Here we explain those steps as design, rather than perform them. Do not run `setup-clinical-skills`, `skills_mirror.py --repair`, hook configuration, package installation, scanners, portal access, corpus rebuilds or clinical workflows. No account details, patient records, private writing samples or credentials are needed.

## A quick orientation to the actual skills

Use the [authoritative skill catalog at the pinned revision](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/AGENTS.md#how-to-use-a-skill), then read each canonical `skills/<name>/SKILL.md` at that same revision. This is a short reading map of the verified pinned revision, not a separately maintained live inventory. The separate upstream README refresh remains unpublished at this lesson's integration checkpoint; this candidate edits no Clinical Skills file. Recheck that catalog when updating this lesson's pin rather than evolving a competing catalog here.

| Public skill | Brief purpose at the study pin |
| --- | --- |
| clinical-note | Expand encounter shorthand into a reviewed clinical note |
| batch-shift | Separate a scanned day file into encounters and carry them through note preparation |
| icd10-cpt | Propose and verify documented encounter codes |
| practicum-case-study | Produce a researched, faculty-aligned Word case study |
| discussion-post | Draft an evidence-backed initial course discussion post |
| discussion-reply | Rank discussion opportunities and draft replies, with approval before posting |
| course-assignment | Prepare and check a slide deck or Word assignment, with approval before submission |
| vitalsource-chrome | Read authenticated eText chapters with page verification |
| peer-critique | Prepare a structured peer critique, with approval before posting |
| setup-clinical-skills | Collect local account/program preferences and optional writing voice setup |
| aar | Review a completed submission and route observed corrections to durable destinations |

These purposes are not permissions to perform them. The trace below reads only setup's PDF-engine branch; it does not require a course, account, writing sample, code database or patient. Source provenance is in [public-study-sources.json](../examples/chad-organizer/public-study-sources.json).

## 1. Find the instructions and their boundary

Open [README.md](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/README.md), then [skills/setup-clinical-skills/SKILL.md](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/skills/setup-clinical-skills/SKILL.md). Read the frontmatter and introduction, then step 0's PDF-engine subsection.

The canonical instructions live under `skills/<name>/SKILL.md`. The setup skill is explicitly user-invoked, collects account-specific knowledge separately from reusable knowledge, and ends with confirmation before writing. Its actual setup includes privacy guardrails before collecting identifying material. The README explains that Claude Code uses a generated local mirror, while other compatible agents can read the canonical files through their own supported mechanisms. Reading a repository does not install a command.

Trace one bounded branch: the PDF-engine check. The instructions name `python tools/pdf_engine.py`. They distinguish installed (0), missing (1), and indeterminate (2). Missing prompts an installation question; refusal/failure follows stated fallback rules. Indeterminate stops for investigation. In this lesson we only read that branch; no install question or dependency probe is needed.

**Checkpoint:** Chad explains why “missing” and “could not determine” lead to different actions, and identifies the exact skill subsection that says so.

## 2. Follow the instruction to a small implementation

Open [tools/pdf_engine.py](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/tools/pdf_engine.py). Follow these actual names:

| Name | What it contributes |
| --- | --- |
| `acquire()` | Imports PyMuPDF only when requested, translating ImportError to EngineUnavailable |
| `engine_version()` | Returns a version string or None for the defined missing-engine case |
| `main()` | Converts the result or unexpected failure into statuses 0, 1 and 2 |
| `REMEDY` | Holds the single installation advice string rather than making each caller duplicate it |
| `ROLES` | Declares whether consumers require a primary source or can narrow an optional secondary check |
| `DECLARED_LIMITS` | Makes known limits visible instead of calling the architecture universally enforced |

This is an implementation of one support operation inside a prompt-driven skill. It is not a Python program that implements the entire setup interview. The module does not install packages when imported. Its remedy text is advice, not permission.

**Checkpoint:** For an invented machine with an absent package, trace `acquire -> engine_version -> main -> skill step 0` and predict status 1. For a generic runtime failure, predict status 2 and investigation. No real PDF or patient is involved.

## 3. Read the synthetic tests as counterexamples

Open [tools/test_pdf_engine.py](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/tools/test_pdf_engine.py), class `PdfEngineCommandReportsTheCheckVerdict`. Read these exact tests:

- `test_present_engine_is_status_zero_with_its_version`: a mocked acquired engine supplies version 1.26.3; expect status 0 and that version.
- `test_missing_engine_is_status_one_with_the_one_remedy`: mocked acquisition raises EngineUnavailable; expect status 1 and the shared remedy.
- `test_unexpected_acquisition_failure_is_status_two`: mocked acquisition raises RuntimeError; expect status 2 and diagnostic text.

These tests create controlled situations; they do not establish that PyMuPDF is installed on Chad's machine, that PDF extraction works, or that a clinical conclusion is correct. We read these public tests; we did not execute the upstream suite or its imports. The whole test module imports other repository support modules and is not a standalone three-test dependency-free script.

Next open [tools/test_pdf_engine_contract.py](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/tools/test_pdf_engine_contract.py). Follow `TheIndexNamesEveryEngineDependentSkill`:

- `test_setup_and_each_derived_skill_run_the_check` binds instructions to the actual command.
- `test_setup_never_routes_an_indeterminate_recheck_to_fallback` checks the specific distinction just traced.
- `test_the_role_command_derivation_and_fenced_import_prohibition_are_live` adds synthetic skill prose that should change the derived set.
- `test_removing_a_derived_skill_name_from_the_paragraph_is_detected` checks the opposite drift direction.

The derivation is bounded: it recognizes named role commands and fenced Python imports, not every possible way to reach a dependency. Some checks inspect text rather than executing the full workflow. Distinguish that evidence from the mocked command-status tests.

**Checkpoint:** Chad predicts which assertion would fail if `main()` returned 0 on missing imports, and which contract check would notice an instruction routing an indeterminate recheck into fallback. Explain why a green test is evidence for its named claim only.

## 4. Read why it was built, then inspect history

Read [ADR 0175](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/docs/adr/0175-a-skill-needing-the-pdf-engine-asks-to-install-it-and-walks-by-eye-only-when-it-cannot.md), especially rulings 3, 4, 6 and 10. It records the 2026-09-11 decision: ask before installing, check in setup and at the needing step, expose a three-status command in the existing module, and bind the consumer instructions to the dependency list with tests. It also records alternatives and limitations. An ADR explains a decision at that time; the pinned implementation shows what exists now.

Open the verified [implementation commit 3180c234](https://github.com/mshamblin5150-code/clinical-skills/commit/3180c234d5d1fea5b34316fbe4eb476455536be8), titled “Implement PDF engine consumer contract (#1009)”. Its public diff connects the documented decision to changed instructions, command behavior and tests. Compare its historical form to the pinned files; subsequent changes are expected. This is a verified representative development trace, not a reconstruction of every earlier session or the entire project's origin.

For a second reusable principle, read [ADR 0001](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/docs/adr/0001-fixture-asserts-on-named-findings.md). Its rationale favors external checks of named findings over prose diffs and a skill's own verdict. Apply that principle to the beginner organizer: inspect actual preserved files and hashes, rather than trusting a message saying the move was safe. Reading this reasoning is not clinical validation.

**Checkpoint:** Chad names one rejected alternative, its reason, the implementation seam and a test that could disprove the desired behavior.

## 5. Separate portable design from private inputs

| Material | Boundary for this lesson |
| --- | --- |
| Public skill instructions, Python sources, tests and ADRs | Read the pinned public sources linked above |
| `scratch/` profiles, identity maps, writing samples and voice model | Local identifying/personal material; absent from this lesson and never requested |
| `output/` notes and coursework | Can contain sensitive data despite being finished; never needed here |
| Separate source PDFs and supplied commercial-source dumps | Public code does not confer access or redistribution rights; no corpus rebuild |
| Clinical/reference/code-set artifacts | Public visibility is not a grant of every underlying license or a proof of medical correctness |
| PyMuPDF and Office applications/extensions | Runtime dependencies and licensing remain separate from reading source |

The README describes gitignored working/output directories and a separate corpus. Gitignore and scanners do not guarantee privacy. Do not seek private inputs to make this lesson “complete,” and do not copy upstream operational instructions into permission to collect them.

Standard PyMuPDF handles PDF and other supported formats; [PyMuPDF Office](https://pymupdf.readthedocs.io/en/latest/pymupdf-office/) separately extends Office-format support under commercial/evaluation terms. Microsoft Word/PowerPoint export applications described upstream are another dependency, not another name for PyMuPDF Office. This trace covers the standard PDF-engine check, not Office-file processing. The beginner organizer remains standard-library-only.

## Finish with something reusable

Ask Chad to produce a five-row map: instruction, code seam, controlled test, ADR reason and known limit. Use only the public paths above. Then describe how to reuse the pattern in an invented reading-list organizer: keep preferences local, preview first, ask for the exact consequential action, isolate optional readers behind a small interface, and test failures without personal documents.

Done when Chad can explain one complete instruction-to-code-to-test-to-decision trace and its limits. No clinical workflow, installation, real-file operation, portal interaction or publication is a completion requirement.
