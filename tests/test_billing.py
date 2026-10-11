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
