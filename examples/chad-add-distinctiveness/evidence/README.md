# Evidence provenance

`supplied-author/` preserves the original Python sources and author logs byte for byte, with Python sources renamed to `.py.txt` so they remain inert. The original eight-test logs also remain at their supplied starter/instructor paths. `SHA256.json` lists hashes of all supplied package files; not every listed file is copied here. ZIP SHA256: 1bfd8508884fd60106dd4b8b85d08b8862ce560063a9291e1e38e0ce2d445fa4, 20290 bytes.

The other logs are Vox's Linux/Python3.12.14 integration executions. Absolute current-checkout and temporary-directory prefixes are replaced with `<checkout>`, `<practice-copy>` or `<mutation>` for public-safe paths. Trailing spaces and redundant final blank lines are removed from integration logs only. Assertions, exceptions, counts and exits are unchanged. `starter-red`/`original-instructor-green` rerun the supplied eight tests. `budget-red`/`budget-green` record the real extra-read correction with a ninth test. `input-red`/`final-green` record invalid-status refinement and the expanded fifteen tests. `expanded-starter-red` records the current intentionally unfinished learner.

`replay-red`/`replay-green` are a controlled same-directory substitution of the known corrected reference into a disposable learner copy, not independent learner development or historical TDD. `replay.json` binds both phases to source hashes. `mutation-results.json` gives exact deliberate changes; each corresponding log shows the actual final tests rejecting that variant. No mutant was retained in runnable source.

No log is evidence that Chad ran the lesson, that GitHub CI passed, that a fresh Windows host was tested, or that printer integration is approved.
