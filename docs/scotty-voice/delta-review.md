# Independent delta review: r2 spelling-only correction

Review date: 8 November 2026.

## Disposition

**Pass for this limited integration delta.** Independently inspected the derivative against the original reviewed v1 files. No change to characterization, corpus evidence, interpretation, counts, source metadata, permissions or scope was found. The original substantive review remains the basis for those findings; this separate review extends assessment only to the exact derivative bytes listed below. Refreshing a hash alone would not have conferred approval.

## Checks and findings

- All nine v1 files still match their previously recorded final hashes. The baseline hashes in release-notes.md match those files and the earlier independent review record.
- Exactly eight non-quotation prose spelling substitutions occurred: four in research.md, two in provenance-and-limitations.md and two in review.md. Each changes the double-L spelling to the single-L spelling. The two embedded occurrences in the separate word beginning with “un” remain unchanged. No canonical quotation was edited.
- Reconstructed the expected derivative from v1 using only those eight substitutions plus the two necessary artifact-hash replacements in review.md. Every derivative file matches that expected result exactly; no additional change was found in the original nine files.
- Independently recomputed every artifact hash listed in the derivative review.md. All eight entries match their actual derivative files.
- VOICE.md, films.md, both source inventories, films-sources.json and audit-method.py are byte-identical to v1. The package's corpus descriptions and evidence inventories are unchanged. Temporary raw transcript caches were not accessed or distributed in this delta review.
- Read the new release-notes.md. It distinguishes the historical review from derivative approval, correctly describes the limited changes and does not claim a CI pass, fresh research or expanded permission. This report supplies the independent disposition to which those notes refer.
- No blocker or substantive defect was found. Original Doohan-textual-corpus limitations and all approval holds remain applicable.

## Limits

This was local byte comparison, hash verification and editorial delta inspection. No research retrieval, corpus analysis, test suite or CI job was rerun, and no CI result is asserted. Original archive containers were not inspected or modified in this review; the verified immutability assertion concerns the nine original source artifacts. No publication, repository mutation, merge or assistant configuration was performed. This review does not grant any additional action authority.

## Exact reviewed r2 artifacts

The following ten artifacts are covered. This newly written delta-review.md is not self-hashed. Any later modification requires a new comparison or review.

- VOICE.md: cbd2e2ea4f70eddaa56a1c2fdb5e71ed2005e13451f53e6434fd35be99bbe3ab
- audit-method.py: db79323c796366ffa79eac9ee248070de55b0f0f9a1b73403be5fcbabbd0294b
- films-sources.json: 18e506498b03eedc326b2436c5a29ad41ca59cd64e241dd78591035b0a546452
- films.md: f18b9f2b91b2227cc8bf40e5c40d0a83e253eb57fbb0b6b4bcdb160b232dff1c
- provenance-and-limitations.md: f97480010cc9cc247ce4dabcc015ad8baadd7b1e528d4be946d94258f41d68c0
- research.md: 2cfab4e6cffeaeae3e21701ed7e479f9fd4a041f6a899756cb38153b283b0a47
- review.md: 33775034db883f7293820fb947c1a2af43912ac1e06adf44b107c768a5083998
- source-inventory.csv: 7d0f9fc63bbc6b667ec7924b2842996573af8bd580eb22f0ed286bd30c027732
- source-inventory.json: b6b9018ff1b41d390195724cd1d98b28b6b75395c5378cc5929bffb308dba776
- release-notes.md: 9bf60b11527c99ef3d01b966b92e44579892d7464b3fc81b58a2eec2c850f7b5
