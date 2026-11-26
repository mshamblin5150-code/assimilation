"""Where this machine keeps the harness's local working files: captures, the sandbox, the OCR
environment, decompiled binaries and the interface-string list. None of it is published.

Set ADOBE_REA_CORPUS to that folder; without it, "adobe-rea-corpus" beside the working directory.
"""

from __future__ import annotations

import os
from pathlib import Path

CORPUS = Path(os.environ.get("ADOBE_REA_CORPUS", "adobe-rea-corpus"))
