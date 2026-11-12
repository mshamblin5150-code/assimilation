# Issue 52: synthetic-first candidate decision and DSP controls

Source-only decision packet, November 12, 2026. Decision owner: Matt Shamblin. Coordinator: Vox. Baseline [51e0f9b8f486df26801f8ac5d97f3357d202b63f](https://github.com/mshamblin5150-code/assimilation/tree/51e0f9b8f486df26801f8ac5d97f3357d202b63f). Canonical tracker: [Issue #52](https://github.com/mshamblin5150-code/assimilation/issues/52). Prior [artifact packet](04-artifact-loader-corrections.md) and [English/Klatt audit](05-english-klatt-provenance.md) remain unchanged.

**Recommendation:** retain eSpeak as a conditionally suitable generated-speech candidate under the accepted synthetic-first scope; do not reject it because it uses stored waves or recording-informed formant parameters. Use independently authored analytical signals as the first prospective numerical DSP controls. Keep the isolated vowel as an optional generator-integration control, not a speaker or spoofing benchmark. Stop the bounded asset-origin search here and carry its documented gap to the existing Checkpoint 1 review.

These are research recommendations, not newly accepted operator decisions or execution clearance. Acoustic Checkpoint 1, simulator execution, human enrollment, live authentication, deployment, upload and permission holds remain. No packages, models, audio or formant payloads were acquired; no generation or execution occurred.

## What the bounded provenance search establishes

Source child /root/espeak_terms_bounded searched pinned eSpeak NG 4870adfa25b1a32b4361592f1be8a40337c58d6c root terms/docs, scoped history for the three /s/ files, legacy official documentation, and upstream public licensing discussions. No person was contacted.

| Evidence | Established fact | Limit |
| --- | --- | --- |
| Three scoped histories: ufric/s_.wav, s!.wav, s.wav | Each returned only [initial SVN import 8d59235f7a7f2a9f0127602ccdfb243dd3a2f390](https://github.com/espeak-ng/espeak-ng/commit/8d59235f7a7f2a9f0127602ccdfb243dd3a2f390), May 5, 2007 | The commit message identifies no recording/procedural origin, authoring procedure or consent. No authoritative asset-origin statement was established. |
| [Pinned README](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/README.md#L129) and [COPYING section 2](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/COPYING#L154) | Upstream declares GPL-3.0-or-later. Section 2 makes output coverage depend on the output's content | Neither a blanket unrestricted-output grant nor a statement that every generated sound inherits GPL follows. These terms do not supply asset origin or consent evidence. |
| Official legacy [espeakedit guide, Keyframe Sequences item 1](https://espeak.sourceforge.net/editor.html) | The documented vowel/a workflow uses an analysed recording spectrum as a guide for formant peaks that produce synthesized sound | This is unversioned historical method documentation, not proof of the origin or contents of the pinned vowel files or particular recording. |
| Upstream [issue 1957](https://github.com/espeak-ng/espeak-ng/issues/1957) | A requester makes an output-license assumption; later comments contain no affirmative maintainer clearance | It cannot be cited as an output license grant. [Issue 908](https://github.com/espeak-ng/espeak-ng/issues/908) concerns linking rather than these asset origins. |

The legacy editor documentation is affirmative evidence that formant design can be recording-informed. It does not convert a future generated vowel into a newly collected human biometric sample. Nor does a WAV component alone establish enrollment, identity targeting or violation of synthetic-first scope. This distinction preserves the accepted research direction instead of adding a recording-free-at-every-level requirement.

The bounded search has ended. Its negative result is limited to the reviewed sources, not a claim that no provenance document exists anywhere. Search receipts: three /commits queries pinned by source SHA and asset path with per_page=100; repository issue searches for generated audio, output/license and ufric/s; official documentation index/license/editor pages. Initial issue queries without an issue-type constraint returned 422 and were corrected. The guessed legacy FAQ route was unavailable. Secondary/mirror search results were excluded; no asset payload was fetched.

## Is the isolated vowel useful?

**Yes, as a limited generator/DSP control.** Packet 05 establishes only the a/a2/a# phoneme-program closure through FMT formant files. This is enough to identify an optional controlled condition for a future, separately reviewed run. It is not evidence of end-to-end recording-free behavior.

Useful future observations would include whether the chosen generator produces a nonempty finite waveform, whether decoding/channel/sample-rate conversion reaches the intended verifier input contract, whether repeated fixed settings give the documented reproducibility, and whether changing a declared synthesis setting has an observable effect. Repeatability and exact waveform equality are tests to perform after freezing build/data/flags; neither is asserted now. Do not presume the generator's output sample rate equals the verifier's required rate.

The [pinned ECAPA model card](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286/README.md) identifies VoxCeleb training and 16 kHz single-channel inputs, and does not warrant transfer performance. The [encoder](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/speechbrain/inference/classifiers.py#L71) expects correctly formatted waveforms. The [scorer](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/speechbrain/inference/speaker.py#L63) compares embeddings; a valid returned score is not proof of meaningful speaker separation.

Consequently:
- a, a2 and a# are phoneme conditions, not three independent speakers.
- Pitch/formant variants from one generator are artificial configuration conditions, not validated independent human identities.
- A vowel-only comparison cannot estimate representative voice false acceptance/rejection, cloned-voice resistance, liveness or identity verification.
- A generated full-utterance synthetic corpus would still need frozen artificial identities/settings, held-out text/conditions, declared attacks, failure accounting and uncertainty. It could characterize those generated conditions, not establish real-world spoof resistance by itself.

## Practical first control packet, specified but not generated

Recommendation: author simple mathematical controls for numerical preprocessing checks before spending more source effort on vowel provenance. This avoids an external phoneme-asset dependency for these particular controls. It does not bypass any existing implementation/execution hold and does not replace speech trials.

Proposed contract: 16,000 samples at 16,000 Hz, index n=0 through 15,999, amplitude A=1/4. Freeze numeric dtype, representation, test tolerances and any serialization choices before implementation. The table is an analytical specification, not an executed generator or observed test result.

| Control | Definition | Intended check |
| --- | --- | --- |
| C00 silence | All samples zero | Shape/finite checks can pass; zero-energy eligibility check must reject it as an enrollment/speech probe. |
| C01 impulse | x[0]=A; all later samples zero | Known index, peak and energy provide numerical oracles. No speaker claim. |
| C02 tone | x[n]=A sin(2 pi 440 n / 16000) | Known bounded periodic signal; inspect numerical/format handling, not a voice identity. |
| C03 identical stereo | Left and right both C02 | Averaging channels should recover C02 within the frozen tolerance. |
| C04 opposite stereo | Left C02; right -C02 | Averaging produces silence in ideal arithmetic; validate energy after mixing, not only before it. |

The [pinned AudioNormalizer](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/speechbrain/dataio/preprocess.py#L42) defaults to 16 kHz and average-to-mono; its _mix uses the channel mean. The channel expectations above are source-based numerical inferences for that configured behavior. They do not assert that every upstream API rejects silence: the energy/finite/shape checks belong to the proposed experimental harness. Missing/nonfinite inputs and zero/nonfinite enrollment embeddings remain explicit failures, as packet 04 requires.

These controls neither call the speaker model nor exercise authentication. Their future implementation, tolerances, artifact hashes and actual test results remain absent. They supply no voice-match accuracy, spoofing or authorization metrics.

## Candidate choice and tradeoffs

| Option | Benefit | Cost/limit | Recommendation |
| --- | --- | --- | --- |
| Authored analytical controls | Clear numerical oracles; no third-party audio/formant assets needed for the definitions | Non-speech; cannot validate speaker models | First prospective DSP harness controls |
| Isolated eSpeak vowel | Exercises a real generator-to-input path with a narrowly described phoneme condition | Same third-party build/data closure; recording-informed design documentation; weak speech diversity | Optional integration control; no further recording-free source chase |
| eSpeak generated full utterances | Practical synthetic-first baseline with a declared source license, configurable conditions and no proposed human enrollment | Reachable stored waves, unresolved asset origins/output-specific terms assessment, limited realism; artifact/host/trial holds remain | Retain as conditional candidate for existing Checkpoint 1 disposition |
| Another generator with explicit data/output documentation | May better fit a later provenance or realistic-speech claim | New model/dependency/license review; no alternative was selected or cleared here | Reopen selection only if that stronger claim is actually required |

The eSpeak candidate can fit the accepted synthetic-first direction in principle; source facts do not establish a disqualifying human collection event. Whether the disclosed origin gap is acceptable for the exact local experiment belongs in the existing independent review, alongside declared terms and intended use. This packet does not grant unrestricted output redistribution, require new consent records for historical assets, or open an extra approval ceremony. No future audio publication is proposed.

## Resolved questions and next bounded action

Resolved by source inspection: the vowel is a limited DSP/integration condition; recording-informed formant design is documented; the scoped search did not resolve the three /s/ origins; neither stored waves nor recording-informed parameters alone disqualify synthetic-first generation. The existing full-English stored-wave-free claim is already refuted and is not revisited.

Still required: named target OS/Python/architecture and approved host record; complete package/model/config hashes and actual-byte verification; reviewed loader/local-resolution behavior; a concrete generator/use/terms disposition; frozen full speech and attack trials; retention/cleanup/isolation evidence. Analytical controls do not clear these findings.

**Next useful authorized step:** find the existing permitted target-platform record and bind the artifact manifest to that exact platform before resolving package artifacts. If no target is recorded, its owner should supply that one concrete choice rather than an agent inventing a wheel set. Do not continue an unbounded source search for recording-free eSpeak. No Captain voice sample is needed.

Methods: current repository onboarding/authority, fleet/operator/publication boundaries and original Matt Research (59db609eb1e18aaf59b63284d0e52255aff0c63c), P-Stack Prove It Works (c742dd61706fbacc1b95f1a20b7b988cf096ce6c). Source child /root/espeak_terms_bounded completed without contact, mutation or execution. Independent reviewer /root/dsp_decision_challenge examined the exact draft and independently checked the official editor guide, pinned GPL section 2, all three asset histories, upstream comments and SpeechBrain input/channel-mixing source. It found no required correction and returned **PASS for publication and documentation-only integration of the exact draft**. This is a bounded static review; no payload acquisition, execution, mutation or publication was performed by the reviewer. Issue #52 stays open; #47 and historical evidence are untouched. Original task creation timestamp remains unknown and is not reset.
