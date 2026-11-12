# Issue 52: English/Klatt stored-wave reachability audit

Source-only correction packet, November 12, 2026. Decision owner: Matt Shamblin. Coordinator: Vox. Baseline [cc0e7645d3593e630ceef010a938d2efeb950345](https://github.com/mshamblin5150-code/assimilation/tree/cc0e7645d3593e630ceef010a938d2efeb950345); canonical tracker [Issue #52](https://github.com/mshamblin5150-code/assimilation/issues/52). This extends [packet 04](04-artifact-loader-corrections.md) without modifying its historical evidence.

**Finding:** the unmodified English language plus Klatt variant at eSpeak NG commit **4870adfa25b1a32b4361592f1be8a40337c58d6c** can reach stored-wave assets. A concrete source witness is the inherited English /s/ phoneme. Conversely, the sampled glottal-source routines are not selected by klatt 1. These are distinct paths.

This disproves a universal stored-wave-free claim for that English configuration. It does not show that every utterance uses a stored wave, establish that a reachable WAV was recorded from a human, or establish output licensing/consent. Acoustic Checkpoint 1 remains HOLD. No build, audio acquisition/generation, runtime or simulator test was performed.

## Exact selection and static witness

Scope is the specified, unmodified language file and variant, with a build that enables Klatt and matching compiled phoneme data from this source. No installed executable/data file was inspected.

| Step | Pinned source evidence | Consequence |
| --- | --- | --- |
| Select language | [lang/gmw/en](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/espeak-ng-data/lang/gmw/en), blob f23fb53124eb2a927dd796154f3fdc41c38467fc, lists en-gb first, then en | This is the exact prospective language file, not every English accent. |
| Select phoneme table | [voices.c](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/voices.c#L548) uses the first language, splits at the hyphen and selects en | en-gb resolves to phoneme table en. |
| Inherit definitions | [phonemes](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/phsource/phonemes#L1695) declares en base1 and includes ph_english; [compiler inheritance](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/compiledata.c#L2218) copies parent entries | ph_english has no definition overriding plain s, so its base1 definition remains. |
| Select variant | [voices/!v/klatt](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/espeak-ng-data/voices/!v/klatt), blob b739a86e488eeec6f5693b7ee2590f84d6c95191, sets klatt 1 | It does not replace the inherited phoneme table or suppress WAV instructions. |
| Choose /s/ sound | [base1 s program](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/phsource/phonemes#L1506) | Pause context selects WAV(ufric/s_); following p/t/k selects WAV(ufric/s!); otherwise WAV(ufric/s). There is no KlattSynth exclusion. |
| Interpret command | [WAV semantics](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/docs/phontab.md#L228), [interpreter return semantics](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthdata.c#L919) | WAV selects stored waveform data; ordinary WAV implies return, so the first matching branch is not overwritten by the later fallback. |

A falsifiable **hypothetical** input is [[s]] with espeakPHONEMES enabled, this exact language/variant and unmodified matching data. The [public API](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/include/espeak-ng/speak_lib.h#L322) documents that flag and bracket syntax; [speech.c](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/speech.c#L436) sets option_phoneme_input; [translate.c](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/translate.c#L1209) recognizes the delimiter under that option. This avoids assuming the pronunciation of the ordinary text letter s. It is a source witness, not an instruction or authorization to execute it now. The exact selected branch in a particular compiled run remains unobserved; all branches reach a stored wave.

## From source asset to output dispatch

The [data compiler](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/compiledata.c#L1291) resolves a source path, tries .wav as a fallback and recognizes RIFF data. Its [LoadWavefile](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/compiledata.c#L1081) processes it into phoneme data. This pipeline was read, not run.

At runtime, [LoadPhData](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthdata.c#L110) loads phondata and makes it available as wavefile_data. The [unvoiced-fricative branch](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthesize.c#L1275) invokes DoSample3. [DoSample3](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthesize.c#L353) uses pd_WAV; [DoSample2](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthesize.c#L293) emits WCMD_WAVE for this path; [wavegen dispatch](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/wavegen.c#L1308) calls PlayWave without a Klatt exclusion.

A second, corroborating path exists for inherited voiced z: its [program](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/phsource/phonemes#L1182) uses FMT plus addWav(ufric/s_, ...), including with Klatt-specific transitions. [Voiced-fricative synthesis](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/synthesize.c#L1338) passes pd_ADDWAV into DoSpect2. That path emits WCMD_WAVE2; [wavegen.c](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/wavegen.c#L1318) configures mixing, and the [Klatt mixer](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/klatt.c#L376) adds the waveform. The /s/ witness alone already establishes reachability; this second path is not required to infer it.

## The sampled glottal source is a different question

[Voice parsing](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/voices.c#L679) stores the selected value; [SetSynth_Klatt](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/klatt.c#L966) assigns glsource from it. [klatt.h](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/klatt.h#L38) defines IMPULSIVE=1, NATURAL=2, SAMPLED=3 and SAMPLED2=4. The [source switch](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/src/libespeak-ng/klatt.c#L276) therefore chooses impulsive_source for unchanged klatt 1.

The existence of sampled_source or its embedded table is not evidence that this variant invokes that glottal source. Excluding this branch does not exclude phoneme WAV playback or addWav mixing.

## Asset identities and provenance limit

Only repository tree metadata was inspected for the following assets; no audio or formant-file payload was fetched. Git blob identities are not local SHA-256 verification.

| Reachable /s/ asset | Git blob | Repository bytes |
| --- | --- | ---: |
| phsource/ufric/s_.wav | b6ab4bf852283e04ecdf4c143ec5fb14d602a7ab | 5,510 |
| phsource/ufric/s!.wav | a6bfa485cb4f1c88f67b0bacb1baea955dea2e72 | 4,482 |
| phsource/ufric/s.wav | 5d41e96213cbf733190c893119181715020e1cbe | 3,934 |

Source: [immutable tree metadata](https://api.github.com/repos/espeak-ng/espeak-ng/git/trees/4870adfa25b1a32b4361592f1be8a40337c58d6c?recursive=1). The scoped history query for s_.wav returned its [initial SVN import](https://github.com/espeak-ng/espeak-ng/commit/8d59235f7a7f2a9f0127602ccdfb243dd3a2f390), dated May 5, 2007, with no recording/generation or consent description in that commit message. That limited history is not proof of origin.

The pinned [README license declaration](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/README.md#L129) states GPL-3.0-or-later; [COPYING](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/COPYING) supplies the license. Those declarations are source/license evidence, not proof that these waveforms were human-recorded, generated procedurally or cleared for a particular downstream research distribution. No per-asset origin/consent statement was established in the inspected metadata/history. MBROLA remains outside this candidate and must not inherit clearance from this audit.

Generated speech can contain stored-wave components. This audit rejects the stronger stored-wave-free claim; it does not invent a blanket rule that every such synthesis violates the accepted synthetic-first scope. Candidate use still needs the existing provenance/terms review. A WAV filename alone does not establish a human biometric collection event.

## A narrower source-only alternative and its limits

The [English a/a2/a# programs](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/phsource/ph_english#L176) offer a small **phoneme-program** alternative:

- a2 changes to a; a may diminish to a#.
- The a/a# branches reach FMT(vowel/a), FMT(vowel/a_8) or FMT(vowel/a#_3), with no WAV, addWav or further CALL in those three definitions.
- Formant asset metadata: vowel/a = d4c64565b1f2a68b729652e77ab56d86640da466 (1,625 bytes); vowel/a_8 = 1974c863212f55a9510f67de35012a6eb4cd2610 (1,627); vowel/a#_3 = f6c9c0d2177d8322460de62d04ea10f6457fd43b (1,292).
- [FMT documentation](https://github.com/espeak-ng/espeak-ng/blob/4870adfa25b1a32b4361592f1be8a40337c58d6c/docs/phontab.md#L241) describes synthesis from formant-value sequences and says the files are made with external espeakedit.

This establishes absence of WAV/addWav instructions in that named program closure, not a recording-free end-to-end pipeline. Context transformations, transitions, compiled data contents and formant-parameter origin still need closure. Restricting a prospective audit to explicit isolated phoneme input, klatt 1, no language/variant changes and no SSML/audio/soundicon additions makes the next source question smaller. It does not authorize generation. A future implementation could enforce refusal of any WAV/addWav or sampled-glottal path, but no guard was implemented or verified here. Muting consonant amplitude is not a substitute for proving no sample path is traversed.

The vowel-only condition would be an artificial DSP probe, not representative English speaker recognition, natural-person identity or convincing voice-clone evidence. No ready, recording-free full-English replacement generator was established.

## Falsification, remaining work and handoff

The universal claim can be refuted by one reachable stored-wave phoneme; exhaustive inventory of every English phoneme is unnecessary for that negative result. Reproduce this source finding by checking the exact selected files, inherited s program, WAV return semantics and sample dispatch above. A refutation would need a source override or unconditional Klatt bypass on that specific chain; none was found in the inspected definitions.

Runtime correspondence remains untested. An installed binary with different build flags, modified phoneme data or other voices is outside this source result. All existing artifact-hash, host-isolation, lifecycle and execution holds remain.

The smallest next permitted source task is closure of the isolated a/a2/a# context-transform and formant-parameter path, or finding an upstream provenance statement for the three s waveforms. Audio inspection alone could not establish consent or original authorship. No operator voice sample is needed, and no new permission gate is inferred.

Original methods retained: Matt Research at 59db609eb1e18aaf59b63284d0e52255aff0c63c; P-Stack Prove It Works at c742dd61706fbacc1b95f1a20b7b988cf096ce6c. Root traced engine/loader paths; genuine source child /root/espeak_english_path independently traced language/table inheritance and the narrower vowel candidate. It completed without mutation or execution. Independent reviewer /root/espeak_provenance_challenge read the exact draft and checked pinned language/variant selection, inheritance, s branches/return semantics, sample dispatch, Klatt source mapping and asset metadata. It found no required correction and returned **PASS for publication and documentation-only merge of the exact draft**. This is static source/publication review, not runtime verification or acoustic clearance. Neither child acquired audio/formant payloads or performed execution/mutation. The original task creation timestamp remains unknown; this finite packet does not reset it.
