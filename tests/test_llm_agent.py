"""The model-driven loop with a scripted model: no network, same receipts and verifier."""

import json
from types import SimpleNamespace

from agent.llm_agent import run_case
from agent.receipts import ReceiptBook
from tests.helpers import BY_SEED
from verifier.assertions import Claim, check_claim, verify_reply


class ScriptedClient:
    """Each step sees the tool results so far and returns the next tool calls."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.n = 0

    def _create(self, **kwargs):
        results = [json.loads(m["content"]) for m in kwargs["messages"] if m["role"] == "tool"]
        calls = self.steps.pop(0)(results)
        tool_calls = []
        for name, args in calls:
            self.n += 1
            tool_calls.append(SimpleNamespace(
                id=f"call_{self.n}",
                function=SimpleNamespace(name=name, arguments=json.dumps(args)),
            ))
        message = SimpleNamespace(content=None, tool_calls=tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)],
                               usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=100))


def rid(results, op, nth=-1):
    return [r for r in results if r.get("op") == op][nth]["receipt_id"]


TXN = {"transfer_id": "TXN-0028"}

READS = lambda _: [("sender_get_debit", TXN), ("switch_get_status", TXN), ("beneficiary_get_credit", TXN)]
REVERSE = lambda _: [("sender_reverse", TXN)]
CLAIM_POSTED = lambda r: [("send_reply", {
    "claims": [{"assertion": "reversal_posted", "receipt_id": rid(r, "sender.reverse"), "value": None,
                "text": "Your reversal has been processed."}],
    "next_step": "Thank you for your patience."})]


def test_v1_sends_the_false_reversal_on_seed_28():
    client = ScriptedClient([READS, REVERSE, CLAIM_POSTED])
    record = run_case(BY_SEED[28], "v1", client=client)
    assert record["status"] == "sent"
    assert record["unproven_claims_sent"] == 1
    assert record["audit"]["false_claims"]
    assert not record["audit"]["resolved_correctly"]


def test_v2_is_blocked_rereads_and_tells_the_truth_on_seed_28():
    honest = lambda r: [("send_reply", {
        "claims": [
            {"assertion": "reversal_requested", "receipt_id": rid(r, "sender.reverse"), "value": None,
             "text": "We asked your bank to reverse the debit."},
            {"assertion": "debit_open", "receipt_id": rid(r, "sender.get_debit"), "value": None,
             "text": "Our latest check shows the debit is still on your account."},
            {"assertion": "escalated", "receipt_id": rid(r, "case.escalate"), "value": None,
             "text": "A specialist now has your case."},
        ],
        "next_step": "We will contact you when the money is back."})]
    client = ScriptedClient([
        lambda _: [("policy_lookup", {"case_type": "failed_unreversed"})],
        READS, REVERSE, CLAIM_POSTED,
        lambda _: [("sender_get_debit", TXN)],
        lambda _: [("escalate", {"reason": "reversal acknowledged but not posted",
                                 "case_type": "reversal_not_posted"})],
        honest,
    ])
    record = run_case(BY_SEED[28], "v2", client=client)
    assert record["blocks"] == 1
    assert "not authoritative" in record["attempts"][0]["verdict"]["claims"][0]["reason"]
    assert record["status"] == "sent"
    assert record["unproven_claims_sent"] == 0
    assert record["audit"]["false_claims"] == []
    assert record["audit"]["resolved_correctly"]


def test_stale_read_is_blocked_after_a_write():
    book = ReceiptBook()
    before = book.record("sender.get_debit", {}, True,
                         {"debited": True, "reversal_applied": False}, None)
    book.record("sender.reverse", {}, True, {"status": "reversed"}, None)
    result = check_claim(Claim("debit_open", before.receipt_id, "The debit is still open."), book)
    assert not result.proved and "stale" in result.reason


def test_sentence_cannot_overclaim_its_assertion():
    book = ReceiptBook()
    ack = book.record("sender.reverse", {}, True, {"status": "reversed"}, None)
    over = check_claim(Claim("reversal_requested", ack.receipt_id, "Your refund is completed."), book)
    fine = check_claim(Claim("reversal_requested", ack.receipt_id, "We asked for a reversal."), book)
    negated = check_claim(Claim("reversal_requested", ack.receipt_id,
                                "We asked for a reversal; it has not posted yet."), book)
    assert not over.proved and fine.proved and negated.proved


def test_next_step_cannot_promise_a_timeline():
    book = ReceiptBook()
    r = book.record("beneficiary.get_credit", {}, True, {"credited": True}, None)
    verdict = verify_reply([Claim("credited", r.receipt_id, "The credit posted.")],
                           "You will get it within 24 hours.", book)
    assert not verdict.allowed


def test_v3_guard_refuses_a_reversal_the_receipts_do_not_support():
    reply = lambda r: [("send_reply", {
        "claims": [{"assertion": "escalated", "receipt_id": rid(r, "case.escalate"), "value": None,
                    "text": "A specialist now has your case."}],
        "next_step": "We will contact you."})]
    txn = {"transfer_id": "TXN-0021"}
    client = ScriptedClient([
        lambda _: [("sender_get_debit", txn), ("switch_get_status", txn), ("beneficiary_get_credit", txn)],
        lambda _: [("sender_reverse", txn)],
        lambda _: [("escalate", {"reason": "switch failed but beneficiary credited",
                                 "case_type": "switch_failed_but_credited"})],
        reply,
    ])
    record = run_case(BY_SEED[21], "v3", client=client)
    refused = [t for t in record["transcript"] if t.get("tool") == "sender_reverse"][0]["result"]
    assert refused["error"] == "refused_by_guard" and "pay twice" in refused["reason"]
    assert not record["audit"]["harmful_action"]
    assert record["audit"]["resolved_correctly"]


def test_pending_needs_a_second_switch_read():
    book = ReceiptBook()
    first = book.record("switch.get_status", {}, True, {"status": "pending"}, None)
    once = check_claim(Claim("switch_status", first.receipt_id, "It is pending.", "pending"), book)
    second = book.record("switch.get_status", {}, True, {"status": "pending"}, None)
    old = check_claim(Claim("switch_status", first.receipt_id, "It is pending.", "pending"), book)
    confirmed = check_claim(Claim("switch_status", second.receipt_id, "It is pending.", "pending"), book)
    assert not once.proved and not old.proved and confirmed.proved
