"""Case file payloads for the demo. Importing this does not import neatlogs."""

from pathlib import Path

from agent.engine import review
from agent.result import AgentResult
from sim.catalog import build_catalog
from sim.models import ChaosFlags
from sim.money import format_naira
from verifier.check import Verdict

ROOT = Path(__file__).resolve().parent
PAGE_PATH = ROOT / "public" / "index.html"
CATALOG = build_catalog()
BY_SEED = {scenario.seed: scenario for scenario in CATALOG}


def scenario_index() -> list[dict]:
    return [
        {
            "seed": scenario.seed,
            "complaint_id": scenario.complaint_id,
            "customer_name": scenario.customer_name,
            "pattern": scenario.pattern,
            "chaos": chaos_notes(scenario.chaos),
        }
        for scenario in CATALOG
    ]


def case_payload(seed: int) -> dict | None:
    scenario = BY_SEED.get(seed)
    if scenario is None:
        return None
    filed = review(scenario)
    facts = scenario.facts
    return {
        "seed": scenario.seed,
        "complaint_id": scenario.complaint_id,
        "customer_name": scenario.customer_name,
        "narrative": scenario.narrative,
        "pattern": scenario.pattern,
        "complained_at": scenario.complained_at,
        "transfer_id": facts.transfer_id,
        "amount": format_naira(facts.amount_kobo),
        "sender_bank": facts.sender_bank,
        "sender_account": facts.sender_account,
        "beneficiary_bank": facts.beneficiary_bank,
        "beneficiary_account": facts.beneficiary_account,
        "chaos": chaos_notes(scenario.chaos),
        "same_reply": filed.same_reply,
        "v1": _side(filed.v1, filed.v1_verdict),
        "v2": _side(filed.v2, filed.v2_verdict),
    }


def page_html() -> str:
    return PAGE_PATH.read_text(encoding="utf-8")


def chaos_notes(flags: ChaosFlags) -> list[str]:
    notes = [f"timeout on {op}" for op in flags.timeout_ops]
    notes.extend(f"connection error on {op}" for op in flags.connection_error_ops)
    if flags.stale_switch_status:
        notes.append(f"stale switch status {flags.stale_switch_status}")
    if flags.lying_reversal:
        notes.append("reversal reports success without posting")
    return notes or ["none"]


def _side(result: AgentResult, verdict: Verdict) -> dict:
    return {
        "outcome": result.outcome,
        "reply": result.reply,
        "allowed": verdict.allowed,
        "ledger_reversal_applied": result.ledger_reversal_applied,
        "tool_order": list(result.tool_order),
        "claims": [
            {
                "name": check.claim.name,
                "statement": check.claim.statement,
                "op": check.claim.op,
                "read_at": check.claim.read_at,
                "proved": check.proved,
                "reason": check.reason,
            }
            for check in verdict.checks
        ],
        "spans": [_span(read) for read in (*result.reads, *([result.reversal] if result.reversal else []))],
    }


def _span(read) -> dict:
    value = read.value or {}
    if not read.ok:
        summary = read.error or "failed"
    elif "balance_kobo" in value and "debited" not in value:
        summary = format_naira(value["balance_kobo"])
    elif "debited" in value:
        state = "reversed" if value.get("reversal_applied") else "debited" if value.get("debited") else "not debited"
        summary = state
    elif "status" in value and "credited" not in value:
        summary = str(value["status"])
    elif "credited" in value:
        summary = "credited" if value["credited"] else "not credited"
    else:
        summary = str(value.get("status", "ok"))
    return {
        "op": read.op,
        "ok": read.ok,
        "error": read.error,
        "read_at": value.get("read_at"),
        "summary": summary,
    }
