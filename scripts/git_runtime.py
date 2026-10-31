"""Shared Git subprocess policy for source access and baseline inspection.

This isolates Git integrations; it is not an operating-system sandbox. Python,
Git and their runtime environment must be trusted. No host config is modified.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess


def run(*args: str, cwd: Path | None = None, capture: bool = True,
        input_bytes: bytes | None = None) -> bytes:
    # Public sources need no inherited execution policy, credentials, or helpers.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_") and key != "SSH_ASKPASS"}
    protocols = {"https", "file"}
    if "GIT_ALLOW_PROTOCOL" in os.environ:
        protocols &= set(os.environ["GIT_ALLOW_PROTOCOL"].split(":"))
    from_user = os.environ.get("GIT_PROTOCOL_FROM_USER")
    if from_user is not None:
        if from_user.lower() in {"0", "false", "no", "off"}:
            protocols.discard("file")
            env["GIT_PROTOCOL_FROM_USER"] = "0"
        elif from_user.lower() in {"1", "true", "yes", "on"}:
            env["GIT_PROTOCOL_FROM_USER"] = "1"
        else:
            raise RuntimeError("Invalid caller Git protocol restriction")
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_SYSTEM=os.devnull,
               GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM="1",
               GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="",
               GIT_ALLOW_PROTOCOL=":".join(sorted(protocols)))
    cmd = ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "init.templateDir=",
           "-c", "credential.helper=", "-c", "core.fsmonitor=false", *args]
    try:
        options = {"input": input_bytes} if input_bytes is not None else {"stdin": subprocess.DEVNULL}
        proc = subprocess.run(cmd, cwd=cwd, env=env,
                              stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.PIPE, check=False, timeout=180, **options)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError(f"Git {args[0]} failed; no source changes adopted") from None
    if proc.returncode:
        # Git stderr and arguments may contain credentials or remote-controlled
        # messages. Retain no raw diagnostic payload in user-visible failures.
        raise RuntimeError(f"Git {args[0]} failed; no source changes adopted")
    return proc.stdout or b""
