# Independent adversarial review: Scott voice reconstruction

Review date: 8 November 2026. This assesses a newly researched reconstruction, not the missing earlier study. It evaluates textual characterization and the proposed adaptation, not an acoustic impersonation or certified screen transcription.

## Disposition

**Pass with stated scope limitations, after corrections verified.** Suitable for preservation and use as a text-characterization guide. The substantive characterization is supported within the named Doohan transcript corpus. No critical or high-severity defect was identified. The review must not be represented as proof that every utterance in every continuity, cut, medium or performance has been researched.

## What was independently tested

- Compared the cached TOS/TAS index against the source inventory: exactly 102 distinct episode URLs, with no missing or extra episode entries. This is 79 TOS broadcast installments plus The Cage and 22 TAS episodes. The nonnumeric Menagerie part-two filename is present. An index match proves coverage of this index, not the absence of unpublished or omitted dialogue.
- Recomputed the standard extraction totals: 1,379 TOS and 256 TAS candidate blocks. Independently found all five documented malformed labels, in I, Mudd, The Enterprise Incident, The Mark of Gideon, The Lights of Zetar and Whom Gods Destroy. These raise the TOS candidate total to 1,384. No additional beginning-of-line SCOT/SCOTT variant appeared in that check. Arbitrary misspellings, unlabelled dialogue and incorrect speaker attribution remain possible.
- Inspected speaker entries for all seven Doohan films and Relics, including parenthesized offscreen/intercom labels. Confirmed the per-work counts 31, 21, 29, 56, 38, 36, 22 and 108, totalling 341 individual entries. Generations has an additional joint Kirk/Scott/Chekov label, excluded from the individual count and explicitly disclosed. Film II simulation and film III playback are not unique real-world story events or fresh dialogue.
- Read evidence supporting every central characterization category and the named TOS/TAS examples in research.md. Expanded surrounding dialogue for ordinary recreation and discipline in The Trouble with Tribbles; the failed pump in The Devil in the Dark; authentication and Fox's command dispute in A Taste of Armageddon; the tactical drinking scene in By Any Other Name; the mistaken medical explanation in The Lights of Zetar; and the engineering, holodeck and later repair exchanges in Relics. This was an independent claim-focused review, not an independent close reading of every line of every episode.
- Re-fetched The Devil in the Dark, The Search for Spock and Relics directly from their cited public URLs. Their raw-page SHA-256 hashes and byte sizes matched the inventory. Other source hashes were checked for inventory consistency, not independently re-downloaded in full.
- Independently retrieved the official [Wit and Wisdom anthology](https://www.startrek.com/news/wit-wisdom-of-montgomery-scotty-scott), confirming selected physics, transporter, plumbing, language-barrier and captain-management attributions. It is corroboration of selected examples, not authentication of the full fan-transcript corpus.
- Read the complete research, film analysis and operational guide; inspected both full inventories and their consistency; checked the proposed publication files for private filesystem paths, private conversation identifiers and extensive reproduced dialogue. Original calibration examples are clearly labelled as newly written and fictional.

## Findings and remediation

### F1. Medium: extracted blocks contain material that is not Scott's speech

The extraction correctly finds labels but does not always terminate before a captain's log, stage direction, editorial annotation or page footer. Examples include captain's logs in [The Naked Time](http://www.chakoteya.net/StarTrek/7.htm), [The Galileo Seven](http://www.chakoteya.net/StarTrek/14.htm), [Friday's Child](http://www.chakoteya.net/StarTrek/32.htm), [The Apple](http://www.chakoteya.net/StarTrek/38.htm) and [The Survivor](http://www.chakoteya.net/StarTrek/TAS005.htm). The final block in [Whom Gods Destroy](http://www.chakoteya.net/StarTrek/71.htm) contains footer material. [The Lorelei Signal](http://www.chakoteya.net/StarTrek/TAS006.htm) contains a transcriber's song-identification commentary.

Impact: block counts cannot be treated as pure speech, word totals, sentence counts or a linguistic training dataset. This does not invalidate the specific characterization claims checked here: those claims trace to identifiable Scott speech or clearly identified scene context, rather than the contaminated portions.

Required remediation: explicitly disclose this limitation, exclude non-Scott prose from characterization, and retain the candidate-label terminology. Any future quantitative language study must clean and manually validate speaker boundaries first. **Resolved:** the corrected research and provenance explicitly exclude these attachments from spoken-language interpretation and retain candidate-label limits.

### F2. Low: provenance metadata must distinguish corpus baseline from appearance evidence

The initial inventory labels all episode records with the Doohan characterization baseline, including The Cage and pages with no Scott-labelled match. This could be mistaken for a cast/appearance assertion. The initial Relics source-quality field also inherited a note about film-page credits, which does not establish the TNG page's authorship.

Required remediation: mark the actor field as a corpus baseline rather than evidence of an appearance, and identify Relics simply as a third-party episode transcript unless its particular credit is verified. **Resolved:** episode actor metadata now says it is a Doohan corpus baseline, not an appearance claim; Relics now has a page-specific fan-transcript quality description.

### F3. Low: one official source appears under two inventory IDs

Q1 and O1 initially refer to the same official anthology URL. Distinct record IDs do not make these independent corroborating sources.

Remediation: consolidate them or explicitly mark the shared source. Do not advertise the number of inventory records as a count of unique independent sources. **Resolved:** the duplicate anthology record was removed; the index itself was added as a separate auditable source. The final combined inventory contains 116 records with 116 unique URLs.

### F4. Scope limitation: broad textual review is not everything ever said

The Doohan baseline covers the requested core unusually broadly, including TAS and all seven films. But the package correctly excludes exhaustive Pegg/Kelvin, modern portrayals, games, books, deleted scenes, alternate releases and archival reuse. No released audiovisual performance or licensed caption track was verified end-to-end. This is not a hidden failure if communicated plainly; it is a constraint on what completion can mean.

Required publication wording: call this a broad Doohan textual reconstruction with specified limits. Do not call it recovered original work, exhaustive across all Scotty media, screen-verified, or an exact accent/timing model. Additional performance or continuity coverage would be a separate research pass.

## Attempts to disprove the central guidance

**Craft is more than slogans.** The Kelso repair exchange, I, Mudd's workshop excitement and TAS's spun-metal ship support hands-on curiosity. The Trouble with Tribbles supplies technical reading as recreation, but its bar fight also prevents converting professional affection into an always-calm ideal. The guide permits ordinary conversation without a dialect marker or machinery metaphor.

**Constraints are real, not always inflated.** The Naked Time, Galileo Seven, Immunity Syndrome and TAS's Survivor distinguish material constraints, uncertainty and actual time needed. Film III and Relics nevertheless contain explicit estimate-padding jokes/advice. The package acknowledges both, then deliberately chooses honest estimates for the adaptation. That distinction is necessary and correctly made.

**Competence can fail.** The Devil in the Dark's failed temporary pump, The Apple's worsening situation and damaged systems, film III's combat-inadequate automation, film IV's transport limits and Generations' partial rescue contradict an automatic-miracle persona. Film V's missed deadline answered with humor is a counterexample to perfect accountability. The guide's clearer error reporting is an intentional improvement, not a claim about flawless canon.

**Respect does not mean unthinking compliance.** A Taste of Armageddon and Whom Gods Destroy support resistance and authentication; Operation: Annihilate! supports retaining a specific restriction while seeking a decision. Gamesters of Triskelion shows forceful disagreement that need not be right. Threats, sabotage and fictional military authority are not imported as assistant permissions.

**The character has blind spots.** Space Seed's admiration for Khan, Spock's Brain's gendered assumptions, Lights of Zetar's dismissal of Mira, and film VI's prejudiced accusation and excessive trust in familiar technical rules contradict a uniformly exemplary engineer. The sources are not sanitized; harmful conduct is explicitly excluded from the adaptation.

**Alcohol is situational, not a universal error response.** By Any Other Name ends with Scott incapacitated after a tactical contest. Relics combines bereavement, displacement and bruised usefulness, followed by reciprocal learning and renewed collaboration. Neither supports routine drunkenness after mistakes. The corrected guide explicitly requires the user to have invited its optional rueful flavor; it must remain low-stakes and factually clear; it must never override accountability or serious-risk communication.

**Warmth and vulnerability are real registers.** The Empath's moral parable, Spectre of the Gun's grief, TAS's Eye of the Beholder, film II's concern for colleagues, film V's affectionate interaction, and Relics' farewell resist an engine-only caricature. The guide does not require every exchange to be terse, technical or jocular.

**No compulsory accent or template.** VOICE.md explicitly rejects a Scottish opener applied to generic status prose, heavy phonetic spelling and a fixed acknowledgment/report rhythm. Its examples pass the basic test of remaining practical and varied after dialect markers are removed. These examples demonstrate a proposed adaptation; they are not a substitute for testing actual replies over time.

## Publication and safety assessment

No long canonical quotation anthology or full transcript is included in the reviewed publication artifacts. Scene titles, short lexical examples and original illustrative dialogue are distinguished from paraphrased findings. Source URLs are public. Operational boundaries preserve truthfulness, uncertainty and approvals; a character voice does not grant authority. No private raw conversation, private task identifier or private filesystem location belongs in the distributed package.

Approval is limited to the reviewed artifacts at the hashes below. Adding raw transcript caches, private diagnostics or unreviewed provenance files is outside this assessment. Publishing these documents does not itself prove that a live assistant has adopted the guide; that requires separate configuration/delivery verification.

## Exact reviewed artifacts

The eight artifacts below were re-read or rechecked after the correction handoff. The audit script received static syntax/logic review; its entire network retrieval loop was not rerun. Status-only final edits direct readers to this review; they do not change the substantive findings. No unreviewed modification is covered. The review file itself is not self-hashed.

- research.md: 38fb25dcd9cb0496a171a4a8624615f7d68cb928c5f9b8a3fd7c43783306a59f
- films.md: f18b9f2b91b2227cc8bf40e5c40d0a83e253eb57fbb0b6b4bcdb160b232dff1c
- VOICE.md: cbd2e2ea4f70eddaa56a1c2fdb5e71ed2005e13451f53e6434fd35be99bbe3ab
- source-inventory.json: b6b9018ff1b41d390195724cd1d98b28b6b75395c5378cc5929bffb308dba776
- source-inventory.csv: 7d0f9fc63bbc6b667ec7924b2842996573af8bd580eb22f0ed286bd30c027732
- films-sources.json: 18e506498b03eedc326b2436c5a29ad41ca59cd64e241dd78591035b0a546452
- provenance-and-limitations.md: c1cf3eaa2aa70b9a4c6726733e0a0c30f9a3844e9551e6917f9ee7c51a8a74b7
- audit-method.py: db79323c796366ffa79eac9ee248070de55b0f0f9a1b73403be5fcbabbd0294b
