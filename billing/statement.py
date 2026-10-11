"""A usage statement: what a bank owes for a period, one line per proved resolution.

Provider-independent. Every line names the complaint and the neatlogs trace that
proves the reply, so the bank can audit any charge by opening its trace. Paystack
(or Dodo Payments, where it can onboard the business) only turns this into an invoice.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from billing.dodo import ESCALATION_EVENT, RESOLUTION_EVENT, billable_event

STATEMENTS = Path(__file__).resolve().parent / "statements"


def price_kobo() -> int:
    # Planning assumption, not a contract: NGN 2,000.00 per proved resolution.
    return int(os.environ.get("RECEIPTS_PRICE_PER_RESOLUTION_KOBO", "200000"))


def build(records: list[dict], *, customer: str, period: str, source: str) -> dict:
    price = price_kobo()
    lines, escalated, unbilled = [], [], 0
    for r in records:
        event = billable_event(r)
        if event == RESOLUTION_EVENT:
            rule = next((str(c.get("value")) for c in r.get("claims_sent") or []
                         if c.get("assertion") == "policy"), None)
            lines.append({
                "complaint_id": r.get("complaint_id"),
                "seed": r.get("seed"),
                "rep": r.get("rep", 1),
                "neatlogs_trace_id": r.get("trace_id"),
                "prompt_version": r.get("version"),
                "policy_rule": rule,
                "amount_kobo": price,
            })
        elif event == ESCALATION_EVENT:
            escalated.append({"complaint_id": r.get("complaint_id"), "neatlogs_trace_id": r.get("trace_id"),
                              "escalation_id": (r.get("escalation") or {}).get("escalation_id")})
        else:
            unbilled += 1
    return {
        "customer": customer,
        "period": period,
        "source": source,
        "currency": "NGN",
        "price_per_resolution_kobo": price,
        "price_note": "planning assumption",
        "proved_resolutions": len(lines),
        "escalated_free": len(escalated),
        "not_billed": unbilled,
        "total_kobo": price * len(lines),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lines": lines,
        "escalations": escalated,
    }


def save(statement: dict) -> Path:
    STATEMENTS.mkdir(parents=True, exist_ok=True)
    name = f"{statement['period']}-{Path(statement['source']).stem}.json"
    path = STATEMENTS / name
    path.write_text(json.dumps(statement, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def naira(kobo: int) -> str:
    return f"NGN {kobo / 100:,.2f}"
