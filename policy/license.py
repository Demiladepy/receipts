"""A committed rule keeps its license only while the runs that cite it stay clean.

    python -m policy.license status
    python -m policy.license check runs/v3-policy-stress-x3.jsonl     # revoke on detections
    python -m policy.license restore agreed-credit-v1 --by "Name" --reason "..."

licenses.jsonl is append-only: approved / revoked / restored events. A rule is active
until a run that cited it sends a false claim or makes a harmful action; then it is
revoked, its case type goes back to the human queue, and only a person restores it.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parent / "licenses.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def events(log: Path = LOG) -> list[dict]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def append(event: dict, log: Path = LOG) -> None:
    with log.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"at": _now(), **event}) + "\n")


def state(rule_id: str, log: Path = LOG) -> dict:
    """Latest license event for a rule; a rule with no events is active."""
    last = {"rule_id": rule_id, "event": "approved", "implicit": True}
    for e in events(log):
        if e["rule_id"] == rule_id:
            last = e
    return last


def is_active(rule_id: str, log: Path = LOG) -> bool:
    return state(rule_id, log)["event"] != "revoked"


def cited_rules(record: dict) -> set[str]:
    return {str(c["value"]) for c in record.get("claims_sent") or [] if c.get("assertion") == "policy"}


def detections(records: list[dict]) -> dict[str, dict]:
    """First failing run per rule: a run that cited the rule and sent a false claim or acted harmfully."""
    found: dict[str, dict] = {}
    for r in records:
        audit = r.get("audit") or {}
        if not (audit.get("false_claims") or audit.get("harmful_action")):
            continue
        for rule_id in cited_rules(r):
            found.setdefault(rule_id, r)
    return found


def check(records: list[dict], log: Path = LOG) -> list[str]:
    """Revoke every active rule with a detection. Returns the revoked rule ids."""
    revoked = []
    for rule_id, r in detections(records).items():
        if not is_active(rule_id, log):
            continue
        audit = r["audit"]
        what = audit["false_claims"][0] if audit.get("false_claims") else "harmful action"
        append({"rule_id": rule_id, "event": "revoked", "by": "audit",
                "reason": f"seed {r['seed']}: {what}", "trace_id": r.get("trace_id")}, log)
        revoked.append(rule_id)
    return revoked


def restore(rule_id: str, by: str, reason: str, log: Path = LOG) -> None:
    append({"rule_id": rule_id, "event": "restored", "by": by, "reason": reason}, log)


def main() -> None:
    from policy.store import load_rules

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    c = sub.add_parser("check")
    c.add_argument("paths", nargs="+", type=Path)
    r = sub.add_parser("restore")
    r.add_argument("rule_id")
    r.add_argument("--by", required=True)
    r.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.cmd == "check":
        records = [json.loads(line) for p in args.paths
                   for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        cited = {rid for rec in records for rid in cited_rules(rec)}
        revoked = check(records)
        print(f"{len(records)} runs, rules cited: {sorted(cited) or 'none'}; revoked: {revoked or 'none'}")
    elif args.cmd == "restore":
        restore(args.rule_id, args.by, args.reason)
    for rule in load_rules():
        s = state(rule["rule_id"])
        print(f"{rule['rule_id']}: {'ACTIVE' if s['event'] != 'revoked' else 'REVOKED'}"
              f"{'' if s.get('implicit') else ' (' + s['event'] + ' ' + s['at'] + ': ' + s.get('reason', '') + ')'}")


if __name__ == "__main__":
    main()
