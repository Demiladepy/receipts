"""Billing decides from what Receipts knows at run time, never from ground truth."""

from billing.dodo import ESCALATION_EVENT, RESOLUTION_EVENT, bill, billable_event, event_for


def record(**over):
    base = {"seed": 28, "rep": 1, "complaint_id": "CMP-0028", "version": "v3", "status": "sent",
            "trace_id": "abc123", "escalation": None, "usage": {"cost_usd": 0.0047},
            "attempts": [{"verdict": {"allowed": True}}],
            "claims_sent": [{"assertion": "policy", "value": "agreed-credit-v1"}]}
    base.update(over)
    return base


def test_only_proved_replies_are_billed():
    assert billable_event(record()) == RESOLUTION_EVENT
    assert billable_event(record(attempts=[{"verdict": {"allowed": False}}])) is None  # v1, unproved
    assert billable_event(record(status="withheld")) is None
    assert billable_event(record(escalation={"escalation_id": "ESC-0028"})) == ESCALATION_EVENT


def test_event_is_idempotent_and_carries_the_trace():
    e = event_for(record(), "cus_1")
    assert e["event_id"] == "proved_resolution:abc123"
    assert e["metadata"]["neatlogs_trace_id"] == "abc123"
    assert e["metadata"]["policy_rule"] == "agreed-credit-v1"


class FakeDodo:
    def __init__(self):
        self.sent = []
        outer = self

        class UsageEvents:
            def ingest(self, events):
                outer.sent.extend(events)

        self.usage_events = UsageEvents()


def test_bill_sends_one_event_per_billable_case():
    dodo = FakeDodo()
    counts = bill([record(), record(trace_id="t2", status="withheld"),
                   record(trace_id="t3", escalation={"x": 1})], dodo=dodo, customer_id="cus_1")
    assert counts == {RESOLUTION_EVENT: 1, ESCALATION_EVENT: 1}
    assert {e["customer_id"] for e in dodo.sent} == {"cus_1"}


def test_statement_lists_each_proved_resolution_with_its_trace():
    from billing.statement import build

    stmt = build([record(), record(trace_id="t2", escalation={"escalation_id": "ESC-1"}),
                  record(trace_id="t3", status="withheld")], customer="Bank", period="2026-10", source="x")
    assert stmt["proved_resolutions"] == 1 and stmt["escalated_free"] == 1 and stmt["not_billed"] == 1
    assert stmt["lines"][0]["neatlogs_trace_id"] == "abc123"
    assert stmt["total_kobo"] == stmt["price_per_resolution_kobo"]


def test_paystack_invoice_is_a_quiet_draft_with_one_line_per_resolution():
    import json as _json

    import httpx

    from billing import paystack
    from billing.statement import build

    seen = {}

    def handler(request):
        body = _json.loads(request.content)
        seen[request.url.path] = body
        if request.url.path == "/customer":
            return httpx.Response(200, json={"status": True, "data": {"customer_code": "CUS_x"}})
        return httpx.Response(200, json={"status": True, "data": {"request_code": "PRQ_x", "status": "draft",
                                                                   "amount": body["amount"], "id": 1}})

    stmt = build([record(), record(trace_id="t2")], customer="Bank", period="2026-10", source="x")
    client = httpx.Client(base_url=paystack.BASE_URL, transport=httpx.MockTransport(handler))
    result = paystack.invoice(stmt, email="d@bank.test", name="Harbor Bank", client=client)
    body = seen["/paymentrequest"]
    assert result["request_code"] == "PRQ_x"
    assert body["send_notification"] is False and body["draft"] is True and body["currency"] == "NGN"
    assert len(body["line_items"]) == 2 and "trace abc123" in body["line_items"][0]["name"]
    assert body["amount"] == sum(i["amount"] for i in body["line_items"])


def test_bachs_checkout_charges_the_statement_count_and_pins_its_digest(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from billing import bachs, dodo
    from billing.statement import build

    monkeypatch.setattr(bachs, "CONFIG_PATH", tmp_path / "config.json")
    calls = {}

    class Fake:
        products = SimpleNamespace(create_product=lambda **kw: calls.setdefault("product", kw) and SimpleNamespace(id="prod_1"))
        customers = SimpleNamespace(
            list_customers=lambda **kw: SimpleNamespace(data=[]),
            create_customer=lambda **kw: calls.setdefault("customer", kw) and SimpleNamespace(customer_id="cus_1"))
        checkouts = SimpleNamespace(create_checkout_session=lambda **kw: calls.setdefault("checkout", kw) and SimpleNamespace(
            checkout_id="chk_1", checkout_url="https://sandbox.bachs.io/c/chk_1", status="open"))

    stmt = build([record(), record(trace_id="t2"), record(trace_id="t3", escalation={"x": 1})],
                 customer="Bank", period="2026-10", source="x")
    result = bachs.checkout(stmt, email="d@bank.test", name="Harbor Bank", bachs=Fake())
    assert calls["product"]["price"] == {"currency": "NGN", "price_type": "fixed", "amount": "2000.00"}
    assert calls["checkout"]["product_cart"] == [{"product_id": "prod_1", "quantity": 2}]
    assert calls["checkout"]["billing_currency"] == "NGN"
    assert calls["checkout"]["metadata"]["statement_sha256"] == result["statement_sha256"] == bachs.statement_digest(stmt)
    assert result["checkout_url"].startswith("https://sandbox")


def test_bachs_refuses_live_keys(monkeypatch):
    import pytest

    from billing import bachs

    monkeypatch.setenv("BACHS_API_KEY", "sk_live_abc")
    monkeypatch.delenv("RECEIPTS_ALLOW_LIVE_BILLING", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    with pytest.raises(SystemExit):
        bachs._key()
