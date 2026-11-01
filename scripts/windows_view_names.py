"""Pure, conservative name preflight for a proposed Windows generated-file view.

Design prototype only: does not inspect paths, read files or authorize installation.
This deliberately rejects non-ASCII names pending a reviewed Unicode policy.
"""
import re

_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z", re.ASCII)
_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.IGNORECASE)


def validate_view_names(paths):
    """Return normalized path keys, or refuse the entire proposal.

    Paths are relative POSIX-style manifest strings, not host filesystem paths.
    This is a necessary preflight, never sufficient for native Windows safety.
    """
    if not isinstance(paths, (list, tuple)) or len(paths) > 20000:
        raise ValueError("invalid-manifest")
    seen = set()
    result = []
    for path in paths:
        if not isinstance(path, str) or not path or len(path) > 1024:
            raise ValueError("invalid-path")
        components = path.split("/")
        if len(components) > 64:
            raise ValueError("path-depth")
        for part in components:
            if (not part or part in (".", "..") or len(part) > 120
                    or not _COMPONENT.fullmatch(part)
                    or part.endswith((".", " "))
                    or _DEVICE.fullmatch(part)):
                raise ValueError("unsupported-windows-component")
        key = "/".join(part.lower() for part in components)
        if key in seen:
            raise ValueError("casefold-collision")
        seen.add(key)
        result.append(key)
    for key in seen:
        parts = key.split("/")
        if any("/".join(parts[:i]) in seen for i in range(1, len(parts))):
            raise ValueError("file-directory-collision")
    return tuple(result)
