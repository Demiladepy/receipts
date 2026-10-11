"""Deterministic receipt check for model-written replies.

A reply is a list of claims. Each claim names an assertion from a closed vocabulary,
cites the receipt that proves it, and carries the sentence the customer will read.
The check never calls a model:

1. The receipt exists and came from a source that is authoritative for the assertion.
2. The receipt's payload says what the assertion says.
3. Mutable state (reversal, open debit, balance) was read after the last write.
4. The sentence does not claim completion that its assertion does not prove.
"""

import re
from dataclasses import dataclass
from typing import Callable

from agent.receipts import Receipt, ReceiptBook
from sim.constants import ESCALATION_LIMIT_KOBO

AMOUNT_OPS = ("sender.get_debit", "switch.get_status", "beneficiary.get_credit")


@dataclass(frozen=True, slots=True)
class Rule:
    ops: tuple[str, ...]
    holds: Callable[[dict, object], bool]
    mutable: bool = False
    may_say: frozenset[str] = frozenset()
    describe: str = ""


_DONE = frozenset({"processed", "completed", "complete", "successful", "successfully"})

RULES: dict[str, Rule] = {
    "debited": Rule(("sender.get_debit",), lambda v, _: v.get("debited") is True,
                    describe="the sender ledger shows the debit"),
    "not_debited": Rule(("sender.get_debit",), lambda v, _: v.get("debited") is False,
                        describe="the sender ledger shows no debit"),
    "amount": Rule(AMOUNT_OPS, lambda v, x: v.get("amount_kobo") == x,
                   describe="value = amount in kobo"),
    "switch_status": Rule(("switch.get_status",), lambda v, x: v.get("status") == x,
                          may_say=_DONE | {"succeeded"},
                          describe="value = success | failed | pending"),
    "credited": Rule(("beneficiary.get_credit",), lambda v, _: v.get("credited") is True,
                     may_say=_DONE | {"credited", "posted", "received", "arrived"},
                     describe="the beneficiary bank shows the credit"),
    "not_credited": Rule(("beneficiary.get_credit",), lambda v, _: v.get("credited") is False,
                         describe="the beneficiary bank shows no credit"),
    "reversal_posted": Rule(("sender.get_debit",), lambda v, _: v.get("reversal_applied") is True,
                            mutable=True,
                            may_say=_DONE | {"reversed", "refunded", "returned", "posted", "resolved"},
                            describe="the sender ledger shows the reversal applied"),
    "debit_open": Rule(("sender.get_debit",),
                       lambda v, _: v.get("debited") is True and v.get("reversal_applied") is False,
                       mutable=True,
                       describe="the sender ledger shows the debit still open"),
    "reversal_requested": Rule(("sender.reverse",), lambda v, _: v.get("status") == "reversed",
                               describe="the reversal tool accepted the request (not proof it posted)"),
    "balance": Rule(("sender.get_balance",), lambda v, x: v.get("balance_kobo") == x, mutable=True,
                    describe="value = balance in kobo"),
    "over_limit": Rule(AMOUNT_OPS, lambda v, _: (v.get("amount_kobo") or 0) > ESCALATION_LIMIT_KOBO,
                       describe="the amount is over the escalation limit"),
    "escalated": Rule(("case.escalate",), lambda v, _: v.get("status") == "queued",
                      describe="the case was handed to a human"),
    "policy": Rule(("policy.lookup",), lambda v, x: v.get("found") is True and v.get("rule_id") == x,
                   describe="value = rule_id of a committed policy rule"),
    "tool_failed": Rule((), lambda v, x: True, describe="value = the error code of a failed call"),
}

ASSERTIONS = tuple(RULES)

_DONE_WORDS = re.compile(
    r"\b(processed|completed|complete|successful|successfully|succeeded|refunded|returned|"
    r"reversed|credited|posted|resolved|received|arrived)\b",
    re.IGNORECASE,
)
# Negated or conditional context: "not posted", "once it is resolved", "until it posts".
_NEGATION = re.compile(
    r"\b(not|never|no|yet|cannot|unable|until|whether|if|once|when|after|before)\b|n't\b",
    re.IGNORECASE,
)
_DIGIT = re.compile(r"\d")


@dataclass(frozen=True, slots=True)
class Claim:
    assertion: str
    receipt_id: str
    text: str
    value: object = None

    @classmethod
    def from_json(cls, raw: dict) -> "Claim":
        return cls(
            assertion=str(raw.get("assertion", "")),
            receipt_id=str(raw.get("receipt_id", "")),
            text=str(raw.get("text", "")),
            value=raw.get("value"),
        )

    def as_json(self) -> dict:
        return {"assertion": self.assertion, "receipt_id": self.receipt_id,
                "value": self.value, "text": self.text}


@dataclass(frozen=True, slots=True)
class ClaimResult:
    claim: Claim
    proved: bool
    reason: str | None

    def as_json(self) -> dict:
        return {**self.claim.as_json(), "proved": self.proved, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ReplyVerdict:
    allowed: bool
    results: tuple[ClaimResult, ...]
    next_step_reason: str | None = None

    @property
    def reasons(self) -> list[str]:
        out = [f"{r.claim.assertion} ({r.claim.receipt_id}): {r.reason}" for r in self.results if r.reason]
        if self.next_step_reason:
            out.append(f"next_step: {self.next_step_reason}")
        return out

    def as_json(self) -> dict:
        return {
            "allowed": self.allowed,
            "claims": [r.as_json() for r in self.results],
            "next_step_reason": self.next_step_reason,
        }


def verify_reply(claims: list[Claim], next_step: str, book: ReceiptBook) -> ReplyVerdict:
    # Pass 1: which claims hold on their receipts (ignoring wording). Their completion
    # words are earned for the whole reply, so a policy sentence may say "credited"
    # when a proved beneficiary receipt in the same reply says so.
    structural = [check_claim(claim, book, check_text=False) for claim in claims]
    earned = frozenset().union(*(RULES[r.claim.assertion].may_say for r in structural if r.proved))
    results = tuple(check_claim(claim, book, earned=earned) for claim in claims)
    step_reason = _guard_next_step(next_step, earned)
    allowed = bool(results) and all(r.proved for r in results) and step_reason is None
    if not results:
        step_reason = step_reason or "The reply makes no claim a receipt can prove."
    return ReplyVerdict(allowed, results, step_reason)


def check_claim(claim: Claim, book: ReceiptBook, *, earned: frozenset[str] = frozenset(),
                check_text: bool = True) -> ClaimResult:
    rule = RULES.get(claim.assertion)
    if rule is None:
        return ClaimResult(claim, False, f"unknown assertion {claim.assertion!r}")
    receipt = book.get(claim.receipt_id)
    if receipt is None:
        return ClaimResult(claim, False, "no receipt with that id")
    if claim.assertion == "tool_failed":
        if receipt.ok:
            return ClaimResult(claim, False, f"{receipt.op} did not fail")
        if claim.value not in (None, receipt.error):
            return ClaimResult(claim, False, f"{receipt.op} failed with {receipt.error}, not {claim.value}")
        return _text_checked(claim, rule, earned, check_text)
    if receipt.op not in rule.ops:
        allowed = ", ".join(rule.ops)
        hint = " A write tool's response is an acknowledgement, not proof of state." if receipt.is_write else ""
        return ClaimResult(claim, False, f"{receipt.op} is not authoritative for {claim.assertion}; "
                                         f"cite {allowed}.{hint}")
    if not receipt.ok or receipt.value is None:
        return ClaimResult(claim, False, f"{receipt.op} failed with {receipt.error}; it proves nothing")
    if claim.assertion == "policy" and receipt.value.get("found") is not True:
        return ClaimResult(claim, False, "that lookup found no rule, so there is nothing to cite. "
                                         "Drop this claim; internal policy is not news to the customer")
    if claim.assertion == "policy" and receipt.value.get("conditions"):
        from policy.store import conditions_hold

        fits, why = conditions_hold(receipt.value["conditions"], [r.as_json() for r in book.receipts])
        if not fits:
            return ClaimResult(claim, False, f"rule {receipt.value.get('rule_id')} does not fit this case: {why}")
    if not rule.holds(receipt.value, _coerce(claim.value)):
        return ClaimResult(claim, False, f"{receipt.op} does not say that ({rule.describe})")
    if claim.assertion == "switch_status":
        stale = _switch_staleness(receipt, claim.value, book)
        if stale:
            return ClaimResult(claim, False, stale)
    if rule.mutable:
        last_write = book.last_write_seq()
        if last_write and receipt.seq < last_write:
            return ClaimResult(claim, False, f"stale: this read (#{receipt.seq}) happened before the "
                                             f"write at #{last_write}; read again")
    return _text_checked(claim, rule, earned, check_text)


def _switch_staleness(receipt: Receipt, value: object, book: ReceiptBook) -> str | None:
    """The switch is a moving source. Cite its latest read, and confirm a pending status
    with a second read before telling a customer the transfer is still pending."""
    reads = [r for r in book.receipts if r.op == "switch.get_status" and r.ok]
    if reads and receipt.seq != reads[-1].seq:
        return f"stale: a later switch read (#{reads[-1].seq}) exists; cite the latest"
    if value == "pending" and len(reads) < 2:
        return "pending is a moving status; read the switch again to confirm it before saying so"
    return None


def _text_checked(claim: Claim, rule: Rule, earned: frozenset[str] = frozenset(),
                  check_text: bool = True) -> ClaimResult:
    word = _unearned_word(claim.text, rule.may_say | earned) if check_text else None
    if word:
        return ClaimResult(claim, False, f"the sentence says {word!r}, which neither {claim.assertion} "
                                         "nor any other proved claim in this reply proves")
    return ClaimResult(claim, True, None)


def _guard_next_step(text: str, earned: frozenset[str] = frozenset()) -> str | None:
    """A next step may repeat what a proved claim earned, but may not add a new fact."""
    if _DIGIT.search(text or ""):
        return "a next step may not promise amounts, dates or timelines"
    word = _unearned_word(text or "", earned)
    if word:
        return (f"the next step says {word!r}, which no proved claim in this reply earns; "
                "put facts in claims and keep next_step to what happens next")
    return None


def _unearned_word(text: str, may_say: frozenset[str]) -> str | None:
    for match in _DONE_WORDS.finditer(text):
        word = match.group(0).lower()
        if word in may_say:
            continue
        before = text[max(0, match.start() - 40):match.start()]
        if _NEGATION.search(" ".join(before.split()[-4:])):
            continue
        return word
    return None


def _coerce(value: object) -> object:
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def receipt_summary(receipt: Receipt) -> str:
    return f"#{receipt.seq} {receipt.op} {'ok' if receipt.ok else receipt.error} [{receipt.receipt_id}]"
