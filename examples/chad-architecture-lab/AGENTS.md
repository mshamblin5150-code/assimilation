# Architecture-upkeep practice scope

Use this directory only for the fictional, preview-only lesson in
`../../docs/CHAD-ARCHITECTURE-UPKEEP.md`. The parent repository's authority and
approval holds still apply.

- Run examples only with the runner's own synthetic temporary fixture. The
  command accepts a named stage, not a user folder. Inspect `preview(folder)`
  through its returned plan and the preservation of fixture names and bytes.
- Keep the intentionally tangled stage labeled and separate. The existing
  `../chad-organizer/` is not a practice target for introducing defects.
- For a new behavior, read Matt's original `tdd` and its test/mocking references;
  write one independently expected failing check, observe the intended failure,
  implement the smallest change, and verify it. Refactor in review after green.
- For architectural upkeep, read the actual `improve-codebase-architecture`
  source and report reference. Survey recent changes; show candidates before
  asking which to explore. A survey never chooses or implements a refactor for
  the learner. Keep this exercise's worked choice distinct from their answer.
- Use P-Stack's behavior-testing, reader-load and prove-it-works principles when
  reviewing. Run the actual checks; retain failures as well as passes.

Done means the verifier accepts only the specifically expected red checkpoints,
the final stage passes, the fixture is preserved, and the report states what
was run and what remains untested. Instruction text is not filesystem
confinement, a scheduler, native skill registration or proof of agent obedience.
