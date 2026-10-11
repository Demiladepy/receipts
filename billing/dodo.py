"""Usage billing through Dodo Payments: a bank pays per proved resolution.

A case is billable only when Receipts itself could prove the reply (the verifier
allowed it) and no human had to step in. Withheld replies and unfinished cases are
never billed; escalations are metered separately so the bank sees the human queue.
Billing uses only what the system knows at run time, never the simulator's truth.

Every usage event carries the case's neatlogs trace id, so each line on the
invoice has a receipt behind it.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

RESOLUTION_EVENT = "proved_resolution"
ESCALATION_EVENT = "human_escalation"


def billable_event(record: dict) -> str | None:
    """Which usage event a finished case produces, or None if it produces none."""
    if record.get("status") == "crashed":
        return None
    if record.get("escalation"):
        return ESCALATION_EVENT
    if record.get("status") != "sent":
        return None
    attempts = record.get("attempts") or []
    if not attempts or not attempts[-1]["verdict"]["allowed"]:
        return None  # v1 sends unchecked replies; an unproved reply is never billed
    return RESOLUTION_EVENT


def event_for(record: dict, customer_id: str, *, now: datetime | None = None) -> dict | None:
    name = billable_event(record)
    if name is None:
        return None
    trace_id = record.get("trace_id") or f"seed{record['seed']}-rep{record.get('rep', 1)}"
    claims = record.get("claims_sent") or []
    return {
        # Idempotent: re-sending the same run never bills twice.
        "event_id": f"{name}:{trace_id}",
        "customer_id": customer_id,
        "event_name": name,
        "timestamp": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "metadata": {
            "complaint_id": record.get("complaint_id", ""),
            "neatlogs_trace_id": trace_id,
            "prompt_version": record.get("version", ""),
            "claims_proved": len(claims),
            "policy_rule": next((str(c.get("value")) for c in claims if c.get("assertion") == "policy"), ""),
            "model_cost_usd": float(record.get("usage", {}).get("cost_usd", 0.0)),
        },
    }


def events_for(records: list[dict], customer_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [e for e in (event_for(r, customer_id, now=now) for r in records) if e]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit("billing/config.json is missing. Run: python -m billing setup")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def client():
    from dotenv import load_dotenv
    from dodopayments import DodoPayments

    load_dotenv()
    key = os.environ.get("DODO_PAYMENTS_API_KEY")
    if not key:
        raise SystemExit("DODO_PAYMENTS_API_KEY is empty. Add a test-mode key to .env.")
    return DodoPayments(bearer_token=key,
                        environment=os.environ.get("DODO_PAYMENTS_ENVIRONMENT", "test_mode"))


def bill(records: list[dict], dodo=None, customer_id: str | None = None) -> dict:
    """Send usage events for finished cases. Returns counts by event name."""
    dodo = dodo or client()
    customer_id = customer_id or load_config()["customer_id"]
    events = events_for(records, customer_id)
    for start in range(0, len(events), 500):
        dodo.usage_events.ingest(events=events[start:start + 500])
    counts: dict[str, int] = {}
    for e in events:
        counts[e["event_name"]] = counts.get(e["event_name"], 0) + 1
    return counts
