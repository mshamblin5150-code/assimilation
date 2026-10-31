#!/usr/bin/env python3
"""Check a private handoff's structure; never execute or verify its claims."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


FIELDS = (
    "schema_version", "phase", "task_id", "owner", "coordinator", "repository",
    "revision", "ticket", "objective", "instructions", "scope", "work_state",
    "task_started_at", "observed_at", "handoff_due_at", "completed", "untested",
    "evidence", "admission", "pending_operations", "blockers", "retry", "next",
)
MAX_INPUT_BYTES = 262144


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("non-JSON constant")


def check(record):
    if not isinstance(record, dict):
        return ["record must be an object"]
    findings = []

    def require(condition, field, rule):
        if not condition:
            findings.append(f"{field}: {rule}")

    def text(value, field):
        require(isinstance(value, str) and bool(value.strip()), field, "nonempty text required")

    def choice(value, field, choices):
        require(isinstance(value, str) and value in choices, field, "unsupported value")

    def texts(value, field, nonempty=False):
        require(isinstance(value, list), field, "list required")
        if isinstance(value, list):
            require(not nonempty or bool(value), field, "at least one entry required")
            for item in value:
                text(item, field)

    def obj(value, field, keys):
        require(isinstance(value, dict), field, "object required")
        if not isinstance(value, dict):
            return False
        require(set(value) == set(keys), field, "required fields missing or unknown fields present")
        return all(k in value for k in keys)

    def timestamp(value, field):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
                raise ValueError
            return parsed.astimezone(timezone.utc)
        except (AttributeError, TypeError, ValueError, OverflowError):
            findings.append(f"{field}: UTC timestamp required")
            return None

    if not obj(record, "record", FIELDS):
        return findings + [f"{field}: required" for field in FIELDS if field not in record]
    require(type(record["schema_version"]) is int and record["schema_version"] == 1,
            "schema_version", "version 1 required")
    choice(record["phase"], "phase", {"start", "end"})
    choice(record["work_state"], "work_state", {"not_started", "running", "blocked", "complete"})
    for field in ("task_id", "owner", "coordinator", "repository", "revision", "ticket", "objective"):
        text(record[field], field)
    texts(record["instructions"], "instructions", nonempty=True)
    for field in ("completed", "untested"):
        texts(record[field], field)
    if obj(record["scope"], "scope", ("authorized", "holds")):
        texts(record["scope"]["authorized"], "scope.authorized", nonempty=True)
        texts(record["scope"]["holds"], "scope.holds")
    for field in ("evidence", "pending_operations", "blockers"):
        require(isinstance(record[field], list), field, "list required")
    if isinstance(record["evidence"], list):
        require(bool(record["evidence"]), "evidence", "at least one observed reference required")
        for item in record["evidence"]:
            if obj(item, "evidence", ("kind", "ref", "result")):
                choice(item["kind"], "evidence.kind", {"read", "test", "write", "review"})
                text(item["ref"], "evidence.ref")
                text(item["result"], "evidence.result")
    if isinstance(record["pending_operations"], list):
        for item in record["pending_operations"]:
            if obj(item, "pending_operations", ("id", "state")):
                text(item["id"], "pending_operations.id")
                choice(item["state"], "pending_operations.state", {"running", "pending", "uncertain"})
    admission = record["admission"]
    admission_ok = obj(admission, "admission", ("status", "operation_id", "evidence"))
    if admission_ok:
        choice(admission["status"], "admission.status", {"not_requested", "admitted", "denied", "uncertain"})
        text(admission["evidence"], "admission.evidence")
        if admission["operation_id"] is not None:
            text(admission["operation_id"], "admission.operation_id")
        if admission["status"] == "admitted":
            text(admission["operation_id"], "admission.operation_id")
    next_step = record["next"]
    next_ok = obj(next_step, "next", ("owner", "kind", "action", "success_condition", "check_at"))
    if next_ok:
        for field in ("owner", "action", "success_condition"):
            text(next_step[field], "next." + field)
        choice(next_step["kind"], "next.kind", {"none", "continue", "reconcile", "resolve", "wait", "handoff"})
        if record["work_state"] == "complete":
            require(next_step["kind"] == "none", "next.kind", "complete work has no continuation")
        else:
            require(next_step["kind"] != "none", "next.kind", "incomplete work needs an owned continuation")
        if admission_ok and admission["status"] == "uncertain":
            require(next_step["kind"] in ("reconcile", "handoff"), "next.kind", "uncertain admission needs reconciliation or handoff")
    if record["work_state"] == "complete":
        require(not record["pending_operations"] and not record["blockers"],
                "work_state", "complete work cannot have pending operations or blockers")
        require(bool(record["completed"]), "completed", "complete work needs a result")
        require(admission_ok and admission["status"] not in ("denied", "uncertain"),
                "admission", "complete work cannot retain denied or uncertain admission")
    denied = admission_ok and admission["status"] == "denied"
    unresolved_execution = False
    if isinstance(record["blockers"], list):
        if record["work_state"] == "blocked":
            require(bool(record["blockers"]), "blockers", "blocked work needs a diagnosis")
        for blocker in record["blockers"]:
            if obj(blocker, "blockers", ("action", "target", "outcome", "reason", "attempts", "alternatives")):
                for field in ("action", "target", "reason"):
                    text(blocker[field], "blockers." + field)
                choice(blocker["outcome"], "blockers.outcome", {"denied", "pending", "uncertain", "failed", "unavailable"})
                denied = denied or blocker["outcome"] == "denied"
                unresolved_execution = unresolved_execution or blocker["outcome"] in ("uncertain", "pending")
                texts(blocker["attempts"], "blockers.attempts", nonempty=True)
                if obj(blocker["alternatives"], "blockers.alternatives", ("local", "cloud")):
                    for route in ("local", "cloud"):
                        alternative = blocker["alternatives"][route]
                        if obj(alternative, "blockers.alternatives." + route, ("status", "reason")):
                            choice(alternative["status"], "blockers.alternatives.status", {"available", "blocked", "unavailable", "not_applicable"})
                            text(alternative["reason"], "blockers.alternatives.reason")
    started = timestamp(record["task_started_at"], "task_started_at")
    observed = timestamp(record["observed_at"], "observed_at")
    due = timestamp(record["handoff_due_at"], "handoff_due_at")
    if started and due:
        require(timedelta(0) < due - started <= timedelta(hours=24),
                "handoff_due_at", "must follow original task start by at most 24 hours")
    if started and observed:
        require(observed >= started, "observed_at", "cannot precede task start")
    if next_ok:
        if observed and due and observed >= due and record["work_state"] != "complete":
            require(next_step["kind"] == "handoff", "next.kind", "task deadline requires handoff, not renewed work")
        if next_step["kind"] == "wait":
            require(next_step["check_at"] is not None, "next.check_at", "waiting needs a next observation")
        if next_step["check_at"] is not None:
            check_at = timestamp(next_step["check_at"], "next.check_at")
            if check_at and observed and due:
                require(observed <= check_at <= due, "next.check_at", "must be between observation and handoff")
    retry = record["retry"]
    if obj(retry, "retry", ("decision", "reason", "prior_outcome", "window_started_at", "window_expires_at", "materially_new_evidence", "attempt_for_evidence")):
        choice(retry["decision"], "retry.decision", {"none", "retry", "reconcile", "hold"})
        choice(retry["prior_outcome"], "retry.prior_outcome", {"not_attempted", "known_not_executed", "completed", "running", "uncertain"})
        text(retry["reason"], "retry.reason")
        if record["work_state"] == "complete":
            require(retry["decision"] == "none", "retry.decision", "complete work cannot schedule retry, reconciliation, or hold")
        require(type(retry["attempt_for_evidence"]) is int and retry["attempt_for_evidence"] >= 0,
                "retry.attempt_for_evidence", "nonnegative integer required")
        if retry["materially_new_evidence"] is not None:
            text(retry["materially_new_evidence"], "retry.materially_new_evidence")
        window_start = window_end = None
        if retry["window_started_at"] is not None or retry["window_expires_at"] is not None:
            window_start = timestamp(retry["window_started_at"], "retry.window_started_at")
            window_end = timestamp(retry["window_expires_at"], "retry.window_expires_at")
            if window_start and window_end:
                require(timedelta(0) < window_end - window_start <= timedelta(minutes=15),
                        "retry.window_expires_at", "retry attempts have at most 15 minutes")
        if retry["decision"] == "retry":
            require(not unresolved_execution, "retry", "uncertain or pending blockers require reconciliation")
            require(retry["prior_outcome"] == "known_not_executed", "retry.prior_outcome", "reconcile execution before retry")
            require(not record["pending_operations"], "retry", "pending operations must be reconciled before retry")
            require(admission_ok and admission["status"] != "uncertain", "retry", "uncertain admission must be reconciled")
            require(bool(window_start and window_end and observed and window_start <= observed <= window_end),
                    "retry", "attempt must be inside its recorded retry window")
            require(bool(due and observed and observed < due), "retry", "task deadline requires handoff")
            if denied:
                text(retry["materially_new_evidence"], "retry.materially_new_evidence")
                require(type(retry["attempt_for_evidence"]) is int and retry["attempt_for_evidence"] == 1,
                        "retry.attempt_for_evidence", "denied route permits one retry per new relevant evidence")
        if admission_ok and admission["status"] == "uncertain":
            require(retry["decision"] in ("reconcile", "hold"), "retry.decision", "uncertain admission cannot be retried")
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        if not args.record.is_file():
            raise ValueError("regular file required")
        with args.record.open("rb") as source:
            payload = source.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise ValueError("record too large")
        record = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object,
                            parse_constant=reject_constant)
    except (OSError, UnicodeError, ValueError, RecursionError):
        print("handoff: input unreadable or invalid")
        return 2
    findings = check(record)
    for finding in findings:
        print(f"handoff: {finding}")
    if not findings:
        print("handoff: structure OK; claims and authorization not verified")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
