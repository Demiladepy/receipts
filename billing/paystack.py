"""Paystack adapter: turn a usage statement into a Payment Request (an invoice).

Test mode is selected by the key itself (sk_test_...). Notifications stay off, so a
test invoice never emails anyone. One line item per proved resolution, named after
the complaint and its neatlogs trace.
"""

import os
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "https://api.paystack.co"


def _key() -> str:
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("PAYSTACK_SECRET_KEY", "")
    if not key:
        raise SystemExit("PAYSTACK_SECRET_KEY is empty. Add a test secret key (sk_test_...) to .env.")
    if not key.startswith("sk_test_") and os.environ.get("RECEIPTS_ALLOW_LIVE_BILLING") != "1":
        raise SystemExit("Refusing a live Paystack key. Use sk_test_..., or set RECEIPTS_ALLOW_LIVE_BILLING=1.")
    return key


def _post(client: httpx.Client, path: str, body: dict) -> dict:
    resp = client.post(path, json=body)
    data = resp.json()
    if not data.get("status"):
        raise RuntimeError(f"Paystack {path}: {data.get('message')}")
    return data["data"]


def line_items(statement: dict) -> list[dict]:
    return [{
        "name": f"{line['complaint_id']} · proved resolution · trace {(line['neatlogs_trace_id'] or '')[:12]}",
        "amount": line["amount_kobo"],
        "quantity": 1,
    } for line in statement["lines"]]


def payload(statement: dict, customer_code: str, *, due_in_days: int = 14) -> dict:
    due = (datetime.now(timezone.utc) + timedelta(days=due_in_days)).date().isoformat()
    return {
        "customer": customer_code,
        "description": (f"Receipts, {statement['period']}: {statement['proved_resolutions']} proved "
                        f"resolutions. {statement['escalated_free']} escalations to your team are not "
                        f"charged. Every line names the neatlogs trace that proves it."),
        "line_items": line_items(statement),
        "amount": statement["total_kobo"],
        "currency": "NGN",
        "due_date": due,
        "send_notification": False,
        "draft": True,
    }


def invoice(statement: dict, *, email: str, name: str, client: httpx.Client | None = None) -> dict:
    """Create (or reuse) the customer and a draft Payment Request for the statement."""
    if statement["proved_resolutions"] == 0:
        raise SystemExit("Nothing to invoice: no proved resolutions in this statement.")
    own = client is None
    client = client or httpx.Client(base_url=BASE_URL, timeout=30,
                                    headers={"Authorization": f"Bearer {_key()}"})
    try:
        first, _, last = name.partition(" ")
        customer = _post(client, "/customer", {"email": email, "first_name": first, "last_name": last or "Bank"})
        request = _post(client, "/paymentrequest", payload(statement, customer["customer_code"]))
        return {"customer_code": customer["customer_code"], "request_code": request.get("request_code"),
                "status": request.get("status"), "amount": request.get("amount"), "id": request.get("id")}
    finally:
        if own:
            client.close()
