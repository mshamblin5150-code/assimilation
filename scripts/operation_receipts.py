#!/usr/bin/env python3
"""Explicit, passive receipt ingestion. Never execute, approve, retry or subscribe.

Call ingest with caller-selected, already exposed JSON metadata. No result text,
payload, rule, URL or raw identifier is retained. Reference/identifier fingerprints
are correlation aids, not locators, authority, authenticity or proof of execution.
Keep their mapping in the existing private task record. Do not supply secrets.

Input: a list of at most 256 plain JSON objects / 256 KiB. Fields and supported
values are listed in CHOICES and IDENTITIES below; all other fields are omitted,
including their names. source_time is an exposed timezone-bearing ISO timestamp.
source_sequence, if actually exposed, must be a contiguous 1-based sequence scoped
to this attempt/item; otherwise omit it. Missing/invalid values remain unknown.
attempt_id is a caller's distinct-attempt label, never an invented service ID.
Use a new attempt_id for every actual retry; never reuse an operation's identity
for a different action. item_id separates individual partial-write targets.

Correlation requires exact source_id, operation_id and attempt_id, plus item_id
when supplied. Unknown identities are not merged. Duplicate marking additionally
requires delivery_id and identical typed JSON content; every arrival is retained.
Summary outcomes describe supplied assertions only. Readback is separate from
returned results, disagreement remains unknown, and no result proves consent.
Source/arrival order is retained; missing phases and supplied sequence gaps are
diagnostics, not proof of a complete trace. No source is polled or looked up.

Triage uses these sanitized records only. Fixed review leads identify surfaced
denials, supplied authority references needing scope comparison, unknown/partial
execution, inconsistent metadata, conflicting results/readbacks, and differences
between a returned result and later readback. Leads carry event/attempt indices,
not verdicts or instructions to retry. A supplied reference does not prove a valid
grant; a denial or different readback does not establish an erroneous review.
Missing-coverage facts are separate informational visibility limits, not anomaly
leads. Even a complete supplied batch proves no live event coverage. Known plan
provenance is never promoted to an observed denial or terminal result.

Integration: explicitly call ingest(events) at an existing worker result boundary,
or pipe the selected JSON batch to this script's stdin. It is dry-run by default.
Pass private_output=/absolute/private/task/NEW-receipt.json (CLI --private-output)
only for an authorized private artifact destination. Its existing parent must be
owner-only on POSIX. No directory is created; existing files and symlinks refuse.
Persistence performs a local byte readback, not a durable remote save. Windows
private-file persistence is unqualified and reports capture_error without writing.
Capture errors are reported as data, without raw inputs, exception text or paths.
The CLI returns zero for handled capture errors: do not use it as an action gate.

Each invocation sees only its supplied batch. To reconcile a late result, include
the earlier exposed metadata in that batch, or compare fingerprints in the existing
private task record. No previous artifact is automatically read or amended. This
aid installs nothing and captures nothing unless a real worker invokes it. It
does not inspect reviewer inputs, protected logs, credentials or host internals.
It changes no action arguments, authority, holds, retry rules or other workflow.
No uploads, public events, network access, background threads or dependencies.
"""
from datetime import datetime, timezone
import argparse
from contextlib import suppress
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


MAX_BYTES = 262144
MAX_EVENTS = 256
CHOICES = {
    "stage": {"planned", "submitted", "result", "readback"},
    "outcome": {"unknown", "running", "awaiting_approval", "denied", "succeeded", "failed", "partial"},
    "execution": {"unknown", "not_started", "started", "partial", "completed"},
    "reason": {"not_exposed", "timeout", "transport_loss", "approval_denial", "access_denial", "argument_binding", "other"},
    "provenance": {"operator_plan", "direct_result", "preserved_result", "worker_report", "independent_readback"},
}
IDENTITIES = ("source_id", "operation_id", "attempt_id", "delivery_id", "item_id",
              "action_ref", "target_ref", "authority_ref", "evidence_ref")
PROVENANCE_BY_STAGE = {
    "planned": {"operator_plan"},
    "submitted": {"direct_result", "preserved_result", "worker_report"},
    "result": {"direct_result", "preserved_result", "worker_report"},
    "readback": {"direct_result", "preserved_result", "worker_report", "independent_readback"},
}


def _fingerprint(value):
    # Even identifier-shaped secrets must never be echoed. A hash is not consent.
    if type(value) is str and 0 < len(value) <= 512:
        try:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()
        except UnicodeError:
            return None
    return None


def _timestamp(value):
    try:
        if type(value) is not str or len(value) > 40:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat() if parsed.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _sanitize(raw):
    safe = {field: raw.get(field) if type(raw.get(field)) is str and raw[field] in values
            else ("not_exposed" if field == "reason" else "unknown")
            for field, values in CHOICES.items()}
    safe["identity_sha256"] = {name: _fingerprint(raw.get(name)) for name in IDENTITIES}
    safe["source_time"] = _timestamp(raw.get("source_time"))
    sequence = raw.get("source_sequence")
    safe["source_sequence"] = sequence if type(sequence) is int and 1 <= sequence <= 1000000 else None
    safe["provenance_stage_conflict"] = (safe["stage"] in PROVENANCE_BY_STAGE
                                         and safe["provenance"] != "unknown"
                                         and safe["provenance"] not in PROVENANCE_BY_STAGE[safe["stage"]])
    safe["denial"] = (safe["reason"] if safe["reason"] in {"access_denial", "approval_denial"}
                      else "unspecified_denial") if (safe["stage"] == "result"
                      and not safe["provenance_stage_conflict"]
                      and safe["outcome"] == "denied") else "none_observed"
    safe["stage_outcome_conflict"] = (safe["stage"] in {"planned", "submitted"}
                                      and safe["outcome"] in {"succeeded", "denied", "failed", "partial"})
    safe["reason_outcome_conflict"] = (safe["outcome"] == "succeeded"
                                       and safe["reason"] in {"approval_denial", "access_denial"})
    safe["unknown_fields"] = [field for field in CHOICES if safe[field] in {"unknown", "not_exposed"}]
    safe["unknown_fields"] += [field for field in IDENTITIES if safe["identity_sha256"][field] is None]
    safe["unknown_fields"] += [field for field in ("source_time", "source_sequence") if safe[field] is None]
    safe["omitted_field_count"] = len(set(raw) - set(CHOICES) - set(IDENTITIES) - {"source_time", "source_sequence"})
    return safe


def _summarize(indices, safe):
    observations = [safe[i] for i in indices]
    result = {"event_indices": indices}
    result["delivery_collision"] = any(e["delivery_collision"] for e in observations)
    for stage, field in (("result", "returned_outcome"), ("readback", "readback_outcome")):
        terminal = {e["outcome"] for e in observations
                    if e["stage"] == stage and not e["provenance_stage_conflict"]
                    and e["outcome"] in {"succeeded", "denied", "failed", "partial"}}
        result[field] = next(iter(terminal)) if len(terminal) == 1 else "unknown"
        result[field + "_conflict"] = len(terminal) > 1
    stages = {e["stage"] for e in observations}
    result["missing_stages"] = [stage for stage in ("planned", "submitted", "result") if stage not in stages]
    sequences = [e["source_sequence"] for e in observations if e["duplicate_of"] is None
                 and e["source_sequence"] is not None]
    result["out_of_order"] = any(b < a for a, b in zip(sequences, sequences[1:]))
    result["sequence_collision"] = len(set(sequences)) != len(sequences)
    result["sequence_unknown"] = any(e["source_sequence"] is None for e in observations)
    points = [0] + sorted(set(sequences))
    result["missing_sequence_ranges"] = [[a + 1, b - 1] for a, b in zip(points, points[1:]) if b - a > 1]
    result["coverage_established"] = False  # No subscription, trailing-gap knowledge or trace authentication.
    return result


def _triage(safe, attempts):
    """Fixed leads from sanitized assertions only; never an authority decision."""
    result = {"review_leads": [], "visibility_limits": [], "coverage": "caller_supplied_only"}
    event_attempt = {event: number for number, attempt in enumerate(attempts) for event in attempt["event_indices"]}

    def add(bucket, flag, indices):
        result[bucket].append({"flag": flag, "event_indices": indices,
                               "attempt_indices": sorted({event_attempt[i] for i in indices})})

    denied = [i for i, e in enumerate(safe) if e["denial"] != "none_observed"]
    observed = [i for i, e in enumerate(safe) if e["stage"] in {"submitted", "result"}
                and not e["provenance_stage_conflict"]]
    leads = (
        ("observed_denial", denied),
        ("authority_scope_comparison_needed", [i for i in denied if safe[i]["identity_sha256"]["authority_ref"]]),
        ("unknown_execution", [i for i in observed if safe[i]["execution"] == "unknown"]),
        ("partial_execution", [i for i in observed if safe[i]["execution"] == "partial" or safe[i]["outcome"] == "partial"]),
        ("inconsistent_event_metadata", [i for i, e in enumerate(safe)
                                          if e["stage_outcome_conflict"] or e["provenance_stage_conflict"]
                                          or e["reason_outcome_conflict"] or e["delivery_collision"]]),
    )
    for flag, indices in leads:
        if indices:
            add("review_leads", flag, indices)
    for field, flag, stages in (
        ("returned_outcome_conflict", "conflicting_returned_results", {"result"}),
        ("readback_outcome_conflict", "conflicting_readbacks", {"readback"}),
        (None, "result_readback_scope_comparison_needed", {"result", "readback"}),
    ):
        indices = []
        for attempt in attempts:
            selected = (attempt[field] if field else
                        attempt["returned_outcome"] != "unknown" and attempt["readback_outcome"] != "unknown"
                        and attempt["returned_outcome"] != attempt["readback_outcome"])
            if selected:
                indices.extend(i for i in attempt["event_indices"] if safe[i]["stage"] in stages
                               and not safe[i]["provenance_stage_conflict"])
        if indices:
            add("review_leads", flag, sorted(indices))
    gaps = [i for attempt in attempts
            if (attempt["missing_stages"] or attempt["sequence_unknown"] or attempt["missing_sequence_ranges"]
                or attempt["sequence_collision"])
            for i in attempt["event_indices"]]
    gaps += [i for i, e in enumerate(safe) if e["stage"] == "unknown" or e["provenance"] == "unknown"
             or any(e["identity_sha256"][key] is None for key in ("source_id", "operation_id", "attempt_id"))]
    if gaps or not safe:
        add("visibility_limits", "missing_coverage", sorted(set(gaps)))
    return result


def _persist(report, destination):
    """Create one artifact, never append/overwrite. No action is coupled to this I/O."""
    directory_fd = None
    created = False
    try:
        if os.name != "posix":
            raise ValueError  # Windows ACLs have not been qualified for this sink.
        path = Path(destination)
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_fd = os.open("/", flags)
        for part in path.parent.parts[1:]:
            child_fd = os.open(part, flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = child_fd
        parent = os.fstat(directory_fd)
        if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077:
            raise ValueError
        # All bytes have passed the allowlist before opening the output file.
        artifact = {k: v for k, v in report.items() if k != "capture_status"}
        data = (json.dumps(artifact, sort_keys=True, indent=2) + "\n").encode("utf-8")
        fd = os.open(path.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        created = True
        with os.fdopen(fd, "w+b") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            handle.seek(0)
            if handle.read(len(data) + 1) != data:
                raise OSError
        report.update(capture_status="saved", write_state="written", readback_verified=True,
                      artifact_sha256=hashlib.sha256(data).hexdigest())
    except Exception:
        # Leave any partial sanitized artifact in place. Never retry or erase it.
        report.update(capture_status="capture_error", readback_verified=False,
                      write_state="unknown_or_partial" if created else "not_written")
    finally:
        if directory_fd is not None:
            with suppress(OSError):
                os.close(directory_fd)
    return report


def ingest(events, *, private_output=None):
    """Ingest a bounded batch; optional exclusive private output, dry-run otherwise.

    No callbacks or action arguments are accepted. Capture errors are data, not
    permission decisions. Caller must not gate/replay an action on this status.
    Use a new artifact in the existing private task-record directory, then attach
    its verified hash there. Never point this sink at the existing record itself.
    """
    try:
        if type(events) is not list or len(events) > MAX_EVENTS or any(type(e) is not dict for e in events):
            raise ValueError
        if len(json.dumps(events, allow_nan=False).encode("utf-8")) > MAX_BYTES:
            raise ValueError
        exact = [json.dumps(e, sort_keys=True, allow_nan=False) for e in events]
        safe = [_sanitize(e) for e in events]
        groups = {}
        for index, raw in enumerate(events):
            # Exact supplied IDs only, not hashed equality or guessed similarity.
            key = tuple(raw.get(k) for k in ("source_id", "operation_id", "attempt_id"))
            if not all(_fingerprint(value) for value in key):
                key = (index,)
            elif raw.get("item_id") is not None and not _fingerprint(raw["item_id"]):
                key = (index,)
            else:
                key += (raw.get("item_id"),)
            safe[index]["duplicate_of"] = next((prior for prior in groups.get(key, [])
                                                 if _fingerprint(raw.get("delivery_id"))
                                                 and exact[index] == exact[prior]), None)
            safe[index]["delivery_collision"] = any(
                _fingerprint(raw.get("delivery_id")) and raw["delivery_id"] == events[prior].get("delivery_id")
                and exact[index] != exact[prior] for prior in groups.get(key, []))
            groups.setdefault(key, []).append(index)
        report = {"schema_version": 1, "capture_status": "dry_run", "events": safe,
                  "recorded_at": datetime.now(timezone.utc).isoformat(),
                  "attempts": [_summarize(indices, safe) for indices in groups.values()]}
        report["triage"] = _triage(safe, report["attempts"])
    except Exception:
        # No input/exception echo, action callback, network request, or retry.
        return {"schema_version": 1, "capture_status": "invalid_input", "events": []}
    return _persist(report, private_output) if private_output is not None else report


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        # Argument values may contain private paths or accidental secrets.
        print('{"capture_status":"invalid_arguments"}')
        self.exit(0)


def main():
    parser = _Parser(description="Passive caller-fed receipt batch from JSON stdin; dry-run by default. No live watcher.")
    parser.add_argument("--private-output", help="New artifact path in an existing owner-only POSIX directory; never overwritten")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError
        events = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        report = ingest(events, private_output=args.private_output)
    except Exception:
        report = {"schema_version": 1, "capture_status": "invalid_input", "events": []}
    try:
        print(json.dumps(report, sort_keys=True))
    except (BrokenPipeError, OSError):
        pass
    # Capture health is explicit data. Never make an action's shell gate/retry signal.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
