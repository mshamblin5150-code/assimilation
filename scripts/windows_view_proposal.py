"""Pure synthetic proposal parser. Never establishes native authority or consent."""
from dataclasses import dataclass
import hashlib
import json
import re
from windows_view_names import validate_view_names


@dataclass(frozen=True)
class Proposal:
    canonical_view: bytes
    canonical_plan: bytes
    view_sha256: str
    plan_sha256: str


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate-field")
        result[key] = value
    return result


def _load(raw):
    if type(raw) is not bytes or len(raw) > 8 * 1024 * 1024:
        raise ValueError("invalid-json-input")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid-json-input") from exc


def _fields(value, expected):
    if type(value) is not dict or set(value) != set(expected.split()):
        raise ValueError("invalid-fields")


def _hex(value, length):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{%d}" % length, value):
        raise ValueError("invalid-digest")


def _view(view):
    _fields(view, "schema source mapping files")
    if view["schema"] != "generated-files-v1" or view["mapping"] != "regular-files-only-v1":
        raise ValueError("unsupported-view")
    source = view["source"]
    _fields(source, "object_format commit tree lock_sha256")
    if source["object_format"] not in ("sha1", "sha256"):
        raise ValueError("unsupported-source-format")
    length = 40 if source["object_format"] == "sha1" else 64
    _hex(source["commit"], length)
    _hex(source["tree"], length)
    _hex(source["lock_sha256"], 64)
    files = view["files"]
    if type(files) is not list or not 1 <= len(files) <= 20000:
        raise ValueError("invalid-files")
    keys = validate_view_names([file.get("path") if type(file) is dict else None for file in files])
    if keys != tuple(sorted(keys)):
        raise ValueError("unsorted-files")
    for file in files:
        _fields(file, "path size sha256 origin")
        if type(file["size"]) is not int or not 0 <= file["size"] <= 2**53 - 1:
            raise ValueError("invalid-size")
        _hex(file["sha256"], 64)
        origin = file["origin"]
        _fields(origin, "path blob mode")
        if origin["mode"] != "100644":
            raise ValueError("unsupported-source-mode")
        _hex(origin["blob"], length)
        validate_view_names([origin["path"]])


def _plan(plan, view, digest):
    _fields(plan, "schema view_sha256 destination_display destination_binding effects activation recovery")
    if (plan["schema"] != "installation-plan-proposal-v1"
            or plan["destination_binding"] != "unqualified"
            or plan["activation"] != "none" or plan["recovery"] != "unqualified"):
        raise ValueError("unsupported-plan")
    if type(plan["destination_display"]) is not str or not plan["destination_display"]:
        raise ValueError("invalid-display")
    try:
        plan["destination_display"].encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("invalid-display") from exc
    _hex(plan["view_sha256"], 64)
    if plan["view_sha256"] != digest:
        raise ValueError("view-binding-mismatch")
    if type(plan["effects"]) is not list or not plan["effects"]:
        raise ValueError("invalid-effects")
    if len(plan["effects"]) != len(view["files"]):
        raise ValueError("effect-count-mismatch")
    for effect, file in zip(plan["effects"], view["files"]):
        _fields(effect, "action path before after")
        if (effect["action"] != "create" or effect["before"] is not None
                or effect["path"] != file["path"] or effect["after"] != file["sha256"]):
            raise ValueError("effect-binding-mismatch")


def parse_proposal(view_json: bytes, plan_json: bytes) -> Proposal:
    """Return immutable proposal bytes, not an executable installation plan."""
    view = _load(view_json)
    plan = _load(plan_json)
    _view(view)
    canonical_view = json.dumps(view, sort_keys=True, ensure_ascii=True,
                                separators=(",", ":")).encode("ascii")
    _plan(plan, view, hashlib.sha256(canonical_view).hexdigest())
    canonical_plan = json.dumps(plan, sort_keys=True, ensure_ascii=True,
                                separators=(",", ":")).encode("ascii")
    return Proposal(canonical_view, canonical_plan,
                    hashlib.sha256(canonical_view).hexdigest(),
                    hashlib.sha256(canonical_plan).hexdigest())
