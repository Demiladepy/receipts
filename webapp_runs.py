"""Recorded model runs for the demo page. No model is called on request: the page
shows the exact runs the before/after numbers come from, with their trace ids."""

import json
from functools import lru_cache
from pathlib import Path

from agent.bench import metrics
from agent.taxonomy import LABELS, classify
from sim.catalog import build_catalog
from sim.money import format_naira
from sim.stress import stress_flags

ROOT = Path(__file__).resolve().parent
RUN_FILES = {v: ROOT / "runs" / f"{v}-stress-x3.jsonl" for v in ("v1", "v2", "v3")}
BY_SEED = {s.seed: s for s in build_catalog()}


@lru_cache(maxsize=None)
def _records(version: str) -> tuple[dict, ...]:
    path = RUN_FILES[version]
    if not path.exists():
        return ()
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def summary() -> dict:
    out = {}
    for version in RUN_FILES:
        records = list(_records(version))
        if records:
            out[version] = metrics(records)
    return out


def flagged_seeds() -> list[int]:
    """Seeds where v1 sent at least one false claim in any repeat."""
    return sorted({r["seed"] for r in _records("v1") if r["audit"]["false_claims"]})


def taxonomy() -> dict:
    out: dict[str, list] = {}
    for version in RUN_FILES:
        counts: dict[str, int] = {}
        for r in _records(version):
            for tag in classify(r):
                counts[tag] = counts.get(tag, 0) + 1
        out[version] = [{"tag": t, "label": LABELS[t], "runs": counts[t]} for t in LABELS if t in counts]
    return out


def chaos_notes(seed: int) -> list[str]:
    flags = stress_flags(BY_SEED[seed])
    notes = [f"first {op} call times out" for op in flags.flaky_ops]
    notes += [f"{op} always times out" for op in flags.timeout_ops]
    notes += [f"{op} connection error" for op in flags.connection_error_ops]
    if flags.stale_switch_status:
        notes.append(f"first switch read is stale ({flags.stale_switch_status})")
    if flags.lying_reversal:
        notes.append("reversal reports success and never posts")
    return notes


def case(seed: int, rep: int = 1) -> dict | None:
    scenario = BY_SEED.get(seed)
    if scenario is None:
        return None
    f = scenario.facts
    sides = {}
    for version in RUN_FILES:
        match = [r for r in _records(version) if r["seed"] == seed and r.get("rep", 1) == rep]
        if match:
            sides[version] = _side(match[0])
    return {
        "seed": seed,
        "rep": rep,
        "complaint_id": scenario.complaint_id,
        "customer_name": scenario.customer_name,
        "narrative": scenario.narrative,
        "pattern": scenario.pattern,
        "amount": format_naira(f.amount_kobo),
        "truth": {
            "debited": f.sender_debited,
            "switch": f.switch_status,
            "credited": f.beneficiary_credited,
            "already_reversed": f.reversal_applied,
        },
        "chaos": chaos_notes(seed),
        "runs": sides,
    }


def _side(r: dict) -> dict:
    receipts = {x["receipt_id"]: x for x in r["receipts"]}
    final = r["attempts"][-1]["verdict"] if r["attempts"] else None
    return {
        "trace_id": r["trace_id"],
        "status": r["status"],
        "message": r["message"],
        "audit": r["audit"],
        "failures": [LABELS[t] for t in classify(r)],
        "blocks": r["blocks"],
        "cost_usd": r["usage"]["cost_usd"],
        "steps": [_step(x) for x in r["receipts"]],
        "attempts": [
            {
                "allowed": a["verdict"]["allowed"],
                "next_step_reason": a["verdict"]["next_step_reason"],
                "claims": [
                    {**c, "op": receipts.get(c["receipt_id"], {}).get("op"),
                     "seq": receipts.get(c["receipt_id"], {}).get("seq")}
                    for c in a["verdict"]["claims"]
                ],
            }
            for a in r["attempts"]
        ],
        "final_allowed": final["allowed"] if final else None,
    }


def _step(x: dict) -> dict:
    v = x.get("value") or {}
    if not x["ok"]:
        said = x["error"]
    elif x["op"] == "sender.get_debit":
        said = "reversal applied" if v.get("reversal_applied") else "debit open" if v.get("debited") else "not debited"
    elif x["op"] == "sender.get_balance":
        said = format_naira(v.get("balance_kobo", 0))
    elif x["op"] == "switch.get_status":
        said = v.get("status")
    elif x["op"] == "beneficiary.get_credit":
        said = "credited" if v.get("credited") else "not credited"
    elif x["op"] == "sender.reverse":
        said = f"acknowledged: {v.get('status')}"
    elif x["op"] == "policy.lookup":
        said = f"rule {v.get('rule_id')}" if v.get("found") else "no rule"
    elif x["op"] == "case.escalate":
        said = f"queued {v.get('escalation_id')}"
    else:
        said = "ok"
    return {"seq": x["seq"], "op": x["op"], "receipt_id": x["receipt_id"], "ok": x["ok"], "said": said}
