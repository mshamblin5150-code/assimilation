# Issue #52: PyTorch CPU index hashes

This addendum supplies four publisher-reported SHA-256 values missing from the historical [reference target record](07-reference-target-artifacts.md). The target is unchanged: Ubuntu 24.04 LTS, x86-64, CPython 3.12, CPU only, for passive artifact research.

| Exact wheel filename | SHA-256 of wheel (published) | SHA-256 of core metadata (published) | Source |
| --- | --- | --- | --- |
| `torch-2.7.1+cpu-cp312-cp312-manylinux_2_28_x86_64.whl` | `8f8b3cfc53010a4b4a3c7ecb88c212e9decc4f5eeb6af75c3c803937d2d60947` | `0464be2f825052a9766185210a6143fbde6762d77cffd1a77d2f8326baf12ae5` | [Official torch CPU index](https://download.pytorch.org/whl/cpu/torch/) |
| `torchaudio-2.7.1+cpu-cp312-cp312-manylinux_2_28_x86_64.whl` | `65bf843345ae05629b7f71609bab0808004dabfce6cf48ea508a5d4f5419ca74` | `81d7048db7bfa00cb431b71ef824b85f363eb8968def566617e200ce5c3ed6e7` | [Official torchaudio CPU index](https://download.pytorch.org/whl/cpu/torchaudio/) |

The first digest is in each exact wheel link's `#sha256=` fragment. The second is the publisher's core-metadata digest on that same index entry. It is not a second wheel hash. The reviewed entries did not establish byte sizes; the metadata bodies and exact published wheel requirements were not verified. These values do not resolve the transitive dependency lock or qualify a host.

No wheel, model, or audio payload was downloaded; neither wheel nor sidecar bytes were independently hashed. No installation or experiment ran. Acoustic Checkpoint 1 remains **HOLD**, with all existing enrollment, authentication, deployment, and permission holds unchanged. Issue #52 remains open.
