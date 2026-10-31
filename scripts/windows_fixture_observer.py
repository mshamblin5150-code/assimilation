"""Conservative Windows path metadata preflight for disposable fixtures only.

No path resolution, file content reads, writes, ACL changes, or installation.
This is NOT handle-based confinement and is unsafe as an installer authorization gate.
"""
from pathlib import Path
import os
import stat
import sys


class Refused(ValueError):
    pass


def observe_regular_chain(root, relative_parts):
    """Reject missing/reparse/non-directory ancestors and reparse/nonregular leaves.

    Caller must supply a test-owned root and nonempty plain relative components.
    The observations are raceable; never use them to authorize writes.
    """
    if sys.platform != "win32":
        raise Refused("windows-only")
    if not isinstance(root, Path) or not isinstance(relative_parts, (tuple, list)) or not relative_parts:
        raise Refused("invalid-input")
    if not all(isinstance(p, str) and p not in ("", ".", "..") and
               "/" not in p and "\\" not in p and ":" not in p for p in relative_parts):
        raise Refused("unsafe-component")
    current = root
    for index, part in enumerate(("", *relative_parts)):
        if index:
            current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise Refused("unobservable-path") from exc
        if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise Refused("reparse-point")
        if index < len(relative_parts):
            if not stat.S_ISDIR(info.st_mode):
                raise Refused("non-directory-ancestor")
        elif not stat.S_ISREG(info.st_mode):
            raise Refused("nonregular-leaf")
    return True
