# Independent repair re-review

2026-10-28 UTC, `verify_trials`; no implementation changes by reviewer.

Inspected repaired CLI modules and ran the unchanged independent public-seam challenge:

```
python -B assimilation-handoff-evidence/recovery-verification/independent_challenge.py assimilation-handoff-evidence/trial-b
python -B assimilation-handoff-evidence/recovery-verification/independent_challenge.py assimilation-handoff-evidence/resumed-a-repaired
```

Both now pass 8/8 tests, exit 0. Logs: `trial-b-repaired-independent.log`, `resumed-a-repaired-repaired-independent.log`. These are coordinator-assisted post-evaluation repairs; original failure outcomes in REVIEW.md are not superseded as historical results.

Read actual changed modules: `set_int_max_str_digits(0)` is confined to `if __name__ == '__main__'`, which is the specified one-shot CLI entry. ValueError and RecursionError map to contract invalid-request output. Importing `parcelquote.__main__` in a fresh subprocess leaves the host digit policy unchanged at 4300, verified separately for both repaired projects. Callable imported `main()` is not claimed to support unbounded digits; it is not the agreed public CLI seam. Removing conversion limits is appropriate only for this unbounded synthetic contract, not a production resource-security recommendation.

`repaired-integrity.json` compares every non-cache file to the saved pre-repair manifest. For both repaired projects, the only changed existing file is `parcelquote/__main__.py`, with `REPAIR.md` added. Pricing, protected project authority, API and tests are unchanged. Original resumed-a has no changed or new non-cache files, confirming retention.

Reviewed draft RESULTS.md for evidence honesty. Its original-versus-repaired separation, explicit failed outcomes, amended-grader distinction and missing original telemetry caveats are sound. Recommended qualifying opening historical swarm/ownership assertions as reported, not independently proven, and repairing missing spaces around several numeric phrases. Final amended-grader totals remain pending separate harness completion and are not claimed by this note.
