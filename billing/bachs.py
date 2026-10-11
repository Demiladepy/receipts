"""Bachs adapter: collect a usage statement through a hosted Bachs checkout.

Bachs is a billing platform for African software companies and settles in NGN, which
is why it replaces Dodo Payments here. Its SDK has no usage meter, so the statement is
the meter: one "Proved resolution" product priced per unit, and a checkout whose
quantity is the statement's count. The checkout carries the statement's SHA-256, so
the bank can confirm it is paying for exactly that list of traced resolutions.

Sandbox keys (sk_sandbox_...) route to Bachs's sandbox automatically; a live key is
refused unless RECEIPTS_ALLOW_LIVE_BILLING=1.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

from billing.dodo import CONFIG_PATH

PRODUCT_NAME = "Receipts: proved resolution"


def _key() -> str:
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("BACHS_API_KEY", "")
    if not key:
        raise SystemExit("BACHS_API_KEY is empty. Add a sandbox key (sk_sandbox_...) to .env.")
    if not key.startswith("sk_sandbox_") and os.environ.get("RECEIPTS_ALLOW_LIVE_BILLING") != "1":
        raise SystemExit("Refusing a live Bachs key. Use sk_sandbox_..., or set RECEIPTS_ALLOW_LIVE_BILLING=1.")
    return key


def client():
    from bachs import BachsClient

    return BachsClient(api_key=_key())


def naira_amount(kobo: int) -> str:
    # Bachs prices are decimal strings in the major unit.
    return f"{kobo / 100:.2f}"


def statement_digest(statement: dict) -> str:
    lines = [(l["complaint_id"], l["neatlogs_trace_id"], l["amount_kobo"]) for l in statement["lines"]]
    return hashlib.sha256(json.dumps(lines, sort_keys=True).encode()).hexdigest()


def _config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}


def setup(price_kobo: int, bachs=None) -> str:
    """Create the per-resolution product once; remember its id in billing/config.json."""
    bachs = bachs or client()
    config = _config()
    if config.get("bachs", {}).get("product_id"):
        return config["bachs"]["product_id"]
    product = bachs.products.create_product(
        name=PRODUCT_NAME,
        description=("One complaint resolved with every claim proved by a neatlogs trace and no human "
                     "needed. Escalations to your team are not charged."),
        price={"currency": "NGN", "price_type": "fixed", "amount": naira_amount(price_kobo)},
        metadata={"unit": "proved_resolution"},
        idempotency_key="receipts-proved-resolution-v1",
    )
    config["bachs"] = {"product_id": product.id, "price_kobo": price_kobo}
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return product.id


def _customer_id(bachs, email: str, name: str) -> str:
    found = bachs.customers.list_customers(search=email)
    for c in getattr(found, "data", None) or getattr(found, "customers", None) or []:
        if getattr(c, "email", None) == email:
            return c.customer_id
    return bachs.customers.create_customer(email=email, name=name,
                                           metadata={"source": "receipts"}).customer_id


def checkout(statement: dict, *, email: str, name: str, bachs=None, expires_in_minutes: int | None = None,
             fresh: bool = False) -> dict:
    if statement["proved_resolutions"] == 0:
        raise SystemExit("Nothing to collect: no proved resolutions in this statement.")
    bachs = bachs or client()
    product_id = setup(statement["price_per_resolution_kobo"], bachs)
    digest = statement_digest(statement)
    session = bachs.checkouts.create_checkout_session(
        customer={"customer_id": _customer_id(bachs, email, name)},
        billing_currency="NGN",
        product_cart=[{"product_id": product_id, "quantity": statement["proved_resolutions"]}],
        reference=f"receipts-{statement['period']}-{digest[:12]}"
                  + (f"-{datetime.now(timezone.utc):%Y%m%d%H%M%S}" if fresh else ""),
        metadata={
            "period": statement["period"],
            "proved_resolutions": statement["proved_resolutions"],
            "escalated_free": statement["escalated_free"],
            "statement_sha256": digest,
            "first_traces": ",".join(l["neatlogs_trace_id"] or "" for l in statement["lines"][:5]),
        },
        idempotency_key=None if fresh else f"receipts-{statement['period']}-{digest[:24]}",
        **({"expires_in_minutes": expires_in_minutes} if expires_in_minutes else {}),
    )
    return {"checkout_id": session.checkout_id, "checkout_url": session.checkout_url,
            "status": session.status, "expires_at": getattr(session, "expires_at", None), "statement_sha256": digest}
