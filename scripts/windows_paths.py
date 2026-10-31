"""Pure candidate package namespace checks; no filesystem admission authority.

Names are preserved or refused, never normalized. This conservative portable
profile is not a model of every NTFS alias, a handle check, or an ACL decision.
"""
import unicodedata
import re

MAX_MEMBERS = 5000
MAX_RELATIVE_UTF16_UNITS = 240
MAX_COMPONENT_UTF16_UNITS = 255
_FORBIDDEN = frozenset('<>:"|?*\\')
_DEVICES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
_DEVICES.update(prefix + digit for prefix in ("COM", "LPT")
                for digit in "123456789\u00b9\u00b2\u00b3")


class NamespaceError(ValueError):
    """Fixed refusal codes only; package names never appear in diagnostics."""


def validate_namespace(paths):
    """Return a bounded portable file inventory without rewriting its names.

    Input is a list or tuple of canonical slash-separated relative file names.
    This validates package metadata only, never a live filesystem or extraction.
    """
    if type(paths) not in (list, tuple) or not 1 <= len(paths) <= MAX_MEMBERS:
        raise NamespaceError("invalid_inventory")
    for path in paths:
        if type(path) is not str or not path or path.startswith("/"):
            raise NamespaceError("invalid_name")
        if len(path) > MAX_RELATIVE_UTF16_UNITS:
            raise NamespaceError("path_bound")
        if any(unicodedata.category(c).startswith("C") for c in path):
            raise NamespaceError("invalid_name")
        if unicodedata.normalize("NFC", path) != path:
            raise NamespaceError("noncanonical_unicode")
        if sum(1 if ord(c) <= 0xFFFF else 2 for c in path) > MAX_RELATIVE_UTF16_UNITS:
            raise NamespaceError("path_bound")
        for part in path.split("/"):
            if (not part or part in {".", ".."} or part.endswith((" ", "."))
                    or any(c in _FORBIDDEN for c in part)):
                raise NamespaceError("invalid_component")
            if sum(1 if ord(c) <= 0xFFFF else 2 for c in part) > MAX_COMPONENT_UTF16_UNITS:
                raise NamespaceError("component_bound")
            if part.split(".")[0].rstrip(" ").upper() in _DEVICES:
                raise NamespaceError("reserved_device")
            if re.fullmatch(r"(?i)(?:\.git|\.?git~[0-9]+)", part):
                raise NamespaceError("reserved_metadata")
    keys = [path.casefold() for path in paths]
    if len(set(keys)) != len(keys):
        raise NamespaceError("name_collision")
    files = set(keys)
    spellings = {}
    for path in paths:
        parts = path.split("/")
        for i in range(1, len(parts) + 1):
            spelling = "/".join(parts[:i])
            prior = spellings.setdefault(spelling.casefold(), spelling)
            if prior != spelling:
                raise NamespaceError("component_alias")
    for key in keys:
        parts = key.split("/")
        if any("/".join(parts[:i]) in files for i in range(1, len(parts))):
            raise NamespaceError("file_directory_collision")
    return tuple(paths)
