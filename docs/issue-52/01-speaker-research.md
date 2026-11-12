# Drone 01: speaker-verification research

Owner: native task `/root/drone01_speaker`. Status: research completed; acoustic execution HOLD. Decision owner: Matt Shamblin. Research date: 2026-11-11 America/New_York.

## Comparison

These are documented capabilities, not executed benchmarks. Enrollment means an application-managed reference embedding; none of these models establishes trusted human identity.

| Candidate | Capability and enrollment | Framework / weights terms | Local requirements and limits |
| --- | --- | --- | --- |
| SpeechBrain ECAPA-TDNN | Embeddings and pairwise comparison; a multi-utterance reference/centroid policy needs evaluation. | Apache-2.0 framework; model card separately labels weights Apache-2.0. | 16 kHz mono. PyTorch/torchaudio >=2.7.1, HyperPyYAML, NumPy, SciPy, soundfile, Hugging Face Hub and further dependencies. CPU path; CUDA optional. Model repository approximately 89.1 MB. |
| pyannote.audio with WeSpeaker ResNet34-LM | Embeddings and cosine-distance comparison, beyond diarization. Reference aggregation remains application policy. | MIT framework; wrapper weights CC-BY-4.0. | 16 kHz mono, 80 mel bins; Python >=3.10, torch/torchaudio >=2.8.0, torchcodec >=0.7.0, Lightning and pyannote packages. CPU/CUDA paths. Explicitly disable telemetry and verify offline behavior. Model repository approximately 26.7 MB. |
| NVIDIA NeMo Speech with TitaNet-Large | Embedding extraction and pairwise verification, approximately 23M parameters; supports file/manifests. | Apache-2.0 framework; TitaNet weights CC-BY-4.0. | NeMo 3.0.0 documentation specifies Python >=3.12, PyTorch >=2.7. CPU inference possible but slow; GPU/CUDA training. Broad dependencies. Model repository approximately 102 MB. |
| Direct WeSpeaker | Embeddings, similarity, register/recognize and local loading, CPU selection; calibration recipes and native/ONNX options. | Apache-2.0 framework; inspected ResNet34-LM weights CC-BY-4.0. | Credible second candidate that removes the pyannote wrapper. Exact chosen weight pin, full dependency lock and loader review unfinished. No demonstrated security advantage. |

No minimum RAM, latency, target-host compatibility or cloning/replay resistance was verified. Repository sizes are acquisition metadata, not installed-memory estimates. Framework licensing does not settle every model, dataset or dependency term.

## Source pins and evidence

| Component | Inspected immutable revision | Primary evidence |
| --- | --- | --- |
| SpeechBrain v1.1.2 | `c0241278f93ef02cd5191f03caf4e5f8e1292bf6` | [Release](https://github.com/speechbrain/speechbrain/releases/tag/v1.1.2), [dependencies](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/pyproject.toml), [license](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/LICENSE) |
| ECAPA weights/config | `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286` | [Model card](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286/README.md), [configuration](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286/hyperparams.yaml) |
| pyannote.audio 4.0.7 | `b749285c5cdd4636b2edc7f766f1352c8dde9369` | [Dependencies](https://github.com/pyannote/pyannote-audio/blob/4.0.7/pyproject.toml), [telemetry controls](https://github.com/pyannote/pyannote-audio#telemetry) |
| pyannote WeSpeaker wrapper | `837717ddb9ff5507820346191109dc79c958d614` | [Card](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM), [configuration](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM/blob/837717ddb9ff5507820346191109dc79c958d614/config.yaml) |
| NeMo Speech v3.0.0 | `fd6a877539710e2b98f28c43272ff81312f83417` | [Installation](https://docs.nvidia.com/nemo/speech/3.0.0/starthere/install.html), [license](https://github.com/NVIDIA-NeMo/Speech/blob/fd6a877539710e2b98f28c43272ff81312f83417/LICENSE) |
| TitaNet weights | `0dc382f40121a5fbd34db10a2bb04d826c2be6a8` | [Model card](https://huggingface.co/nvidia/speakerverification_en_titanet_large) |
| Direct WeSpeaker observed master | `9fecd6cb4f47475d01761d87c826298dff4ef18c` | [Source](https://github.com/wenet-e2e/wespeaker), [official model card](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM) |

Release observations: SpeechBrain v1.1.2 dated 2026-10-14; pyannote 4.0.7 dated 2026-06-30. These are evidence of maintenance, not support guarantees. NeMo v3.0.0 is the inspected release, not a claim it is the latest release.

The three inspected weight pages exposed public paths without an agreement prompt. Acquisition was not attempted; other pipelines/dependencies may be gated.

## Recommendation and source-level pitfalls

Recommend SpeechBrain ECAPA for the first reviewed acoustic experiment because its pairwise workflow is comparatively direct. This is a research recommendation, not installation clearance.

The [pinned implementation](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/speechbrain/inference/speaker.py) returns cosine similarity, with acceptance above a threshold (default 0.25). Its docstring calls this distance. The file helper forwards kwargs to audio loading, not the batch comparison threshold. Calibrate via the batch interface or explicit score comparison.

Pinned model YAML still contains constructor tags and a mutable nested pretrained source. Resolve all dependencies to reviewed local artifacts and audit loaders before execution. The [upstream weight metadata](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286/embedding_model.ckpt) advertises SHA-256 `0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2`. This is metadata read, not verification of downloaded bytes.

None of the inspected cards establishes spoof resistance. A speaker benchmark cannot establish Captain-specific identity or production false-accept rates. [ASVspoof](https://www.asvspoof.org/workshop2024) treats spoof detection as a distinct evaluation problem.

## Proposed acoustic protocol, not executed or cleared

1. Review the exact synthetic generator, voice provenance/terms, model manifest, loaders, host and storage boundary first.
2. Use eight artificial identities, fixed split of four calibration and four held-out identities. No downloaded human speech, Captain samples, real-person cloning or microphone input.
3. Per identity, three independent enrollment utterances and ten independent probe utterances, nominally 5–10 seconds, normalized to 16 kHz mono. Keep enrollment separate from ordinary genuine probes. Use a documented normalized centroid.
4. Each partition yields 40 genuine and 120 ordered impostor comparisons. Calibrate only on calibration identities by minimum balanced false-accept/false-reject error, tie-breaking toward fewer false accepts. Freeze threshold and held-out manifest before evaluation.
5. Freeze separate trial lists/counts for digital replay, simulated channels/noise, short/silent/corrupt input, overlapping artificial voices, transcript/challenge failures and synthetic impersonation. Physical replay and real-world cloning remain untested unless actually executed.
6. Exercise an independent simulated authority matrix for every voice outcome. Include matcher acceptance with authorization denial. Report denominators, failures, timeouts, score direction and environment. Keep zero-effort impostors separate from spoof attempts. Shared-voice comparisons are correlated; avoid naive independent-trial certainty.
7. Proposed maximum synthetic audio/template retention is seven days, with temporary copies removed at run end. Inventory workspace, caches, temporary files, crash outputs and snapshots. Verify path absence without claiming secure erasure.

Generator selection, exact attack counts, dependency/weight hashes, offline host checks and cleanup treatment remain open blockers. No audio, models or dependencies were acquired or executed.
