# Issue #52: approved reference target and candidate artifacts

Research record, 2026-11-12. Decision owner: Matt Shamblin. Baseline: `3eaab9ec4dac2dda444da643a16f50444b16f126`. This supplements [04's partial manifest](04-artifact-loader-manifest.json) and [06's decision](06-synthetic-first-dsp-decision.md); historical records remain unchanged.

## Accepted target

Matt accepted the proposed reference on 2026-11-12: **Ubuntu 24.04 LTS, amd64/x86-64, CPython 3.12 (cp312), CPU-only**, for passive source/metadata artifact research. This is a prospective reference, not an inspected, selected physical machine or qualified runtime. No Python patch version, OS image digest, host identity or observed environment is established. It authorizes no installation or execution. Acoustic Checkpoint 1 and existing holds remain.

## Candidate identity and published evidence

Versions below are prospective candidates, not an installed environment or complete lock. The framework pair follows SpeechBrain's declared lower bound and upstream's matching CPU release pair. HyperPyYAML 1.2.3 is an explicit candidate satisfying the declared floor, not a claim of tested compatibility.

| Distribution | Exact published wheel filename | Published expected SHA256 | Bytes |
| --- | --- | --- | --- |
| SpeechBrain 1.1.2 | `speechbrain-1.1.2-py3-none-any.whl` | `9fea4144c917ea58bcf13f17a1a1759179ed7472a30ec8416e7c7c8cf21d9c9a` | 912709 |
| HyperPyYAML 1.2.3 | `hyperpyyaml-1.2.3-py3-none-any.whl` | `0088c8ce97dc7c7d3460112b6ccc92dca46fade4d0320bc39f58b1fdda60f7f1` | 16456 |
| torch 2.7.1+cpu | `torch-2.7.1+cpu-cp312-cp312-manylinux_2_28_x86_64.whl` | Unresolved through current metadata access | Unresolved |
| torchaudio 2.7.1+cpu | `torchaudio-2.7.1+cpu-cp312-cp312-manylinux_2_28_x86_64.whl` | Unresolved through current metadata access | Unresolved |

Sources: exact-version [SpeechBrain PyPI JSON](https://pypi.org/pypi/speechbrain/1.1.2/json), [HyperPyYAML PyPI JSON](https://pypi.org/pypi/HyperPyYAML/1.2.3/json), official [torch CPU index](https://download.pytorch.org/whl/cpu/torch/), [torchaudio CPU index](https://download.pytorch.org/whl/cpu/torchaudio/), and [PyTorch previous-version guidance](https://pytorch.org/get-started/previous-versions/).

The CPU index entries establish platform-tag availability; they do not prove loading on an actual host. The pure-Python wheel tags likewise do not validate native dependencies. PyPI also publishes core-metadata expected SHA256 values: SpeechBrain `a8e30de45cac9458fa2db35eb6b2f54f784da4888379cde8bc8b3cd4a25d719d`; HyperPyYAML `2a5c8b94a5b79b3b8d3410e683a6e7ef0c4d9fcd0ff41570f6f59ac2960687d3`. All hashes here are publisher metadata, not locally verified artifact bytes. No wheel or model payload was acquired.

The browser renderer exposed CPU filenames but suppressed full href/hash fragments. Requests for CPU wheel `.metadata` sidecars were inaccessible through the tool. These are access limitations, not evidence that upstream hashes or metadata do not exist.

## Dependencies and configuration boundaries

SpeechBrain's exact-version metadata declares Python `>=3.8.1` and twelve base requirements: hyperpyyaml>=0.0.1, joblib>=0.14.1, numpy>=1.17.0, packaging, requests>=2.20.0, scipy>=1.4.1, sentencepiece>=0.1.91, soundfile>=0.12.1, torch>=2.7.1, torchaudio>=2.7.1, tqdm>=4.42.0, huggingface_hub>=0.8.0. Development extras are excluded. HyperPyYAML 1.2.3 declares pyyaml>=5.1 and ruamel.yaml>=0.17.28,<0.19.0; its PyPI requires-python field is null, which is not proof of Python 3.12 support.

[PyTorch v2.7.1 setup.py](https://github.com/pytorch/pytorch/blob/v2.7.1/setup.py) declares filelock, typing-extensions>=4.10.0, setuptools on Python>=3.12, sympy>=1.13.3, networkx, jinja2 and fsspec; build settings can append requirements. [TorchAudio v2.7.1 setup.py](https://github.com/pytorch/audio/blob/v2.7.1/setup.py) derives its torch requirement from PYTORCH_VERSION, otherwise leaving it unpinned. Source declarations therefore do not establish the published CPU wheel METADATA or a complete dependency closure. The CPU pair must remain explicit; availability does not justify substituting another distribution or unreviewed dependency set.

The existing SpeechBrain source pin `c0241278f93ef02cd5191f03caf4e5f8e1292bf6` and model pin `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286` remain the audited candidates. A same-version wheel does not establish source-to-wheel byte equivalence. The prior five-file loader/configuration analysis, expected weight hashes, unresolved small-file hashes, constructor behavior and cache concerns remain in 04. No reviewed local configuration hash or runtime observation has been added.

## Finite result and next action

Resolved: reference-target decision, four candidate wheel identities/platform entries, two published wheel hashes/sizes and their metadata hashes, and explicit dependency edges. Unresolved: CPU wheel hashes/sizes and exact wheel requirements; selection and artifact identities for the full transitive closure; remaining model/configuration hashes; source-to-wheel correspondence; eventual host/isolation and retention evidence; frozen trial acceptance and actual independent execution review.

Next owner: Number One coordinates a passive CPU-index/metadata read capable of preserving href hash anchors, followed by a bounded dependency-resolution proposal on this reference. No further host-choice question is needed for that research. Actual machine qualification and any acquisition or execution require their own applicable authority; this record grants none. No voice sample is needed. Issue #52 stays open.
