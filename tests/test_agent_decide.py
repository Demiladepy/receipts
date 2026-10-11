"""The v1 policy trusts tool payloads and refuses to invent a missing one."""

from dataclasses import replace

from agent.decide import ReadResult, choose, outcome_after_reversal, render
from agent.loop import investigate
from agent.prompt import PROMPT_V1, PROMPT_VERSION
from sim.constants import ESCALATION_LIMIT_KOBO
from sim.models import ChaosFlags
from tests.helpers import BY_SEED

READ_AT = "2026-10-10T08:00:01+01:00"


def _read(op: str, **fields: object) -> ReadResult:
    base: dict[str, object] = {"transfer_id": "TXN-TEST", "amount_kobo": 500_000}
    base.update(fields)
    return ReadResult(op, True, base, None)


def _reads(**overrides: ReadResult) -> tuple[ReadResult, ...]:
    default = {
        "sender.get_debit": _read(
            "sender.get_debit",
            debited=True,
            reversal_applied=False,
            reversed_at=None,
        ),
        "sender.get_balance": _read("sender.get_balance", balance_kobo=1),
        "switch.get_status": _read("switch.get_status", status="success"),
        "beneficiary.get_credit": _read("beneficiary.get_credit", credited=True),
    }
    default.update(overrides)
    return tuple(default[op] for op in (
        "sender.get_debit",
        "sender.get_balance",
        "switch.get_status",
        "beneficiary.get_credit",
    ))


def test_prompt_v1_forbids_a_second_ledger_read():
    assert PROMPT_VERSION == "v1"
    assert "Do not read the ledger again after a reversal." in PROMPT_V1
    assert "Do not invent the missing fact." in PROMPT_V1


def test_choose_follows_the_tool_payloads():
    assert choose(_reads()) == "credited"
    assert choose(_reads(
        **{
            "sender.get_debit": _read(
                "sender.get_debit",
                amount_kobo=ESCALATION_LIMIT_KOBO,
                debited=True,
                reversal_applied=False,
            )
        }
    )) == "credited"
    assert choose(_reads(
        **{
            "sender.get_debit": _read(
                "sender.get_debit",
                amount_kobo=ESCALATION_LIMIT_KOBO + 1,
                debited=True,
                reversal_applied=False,
            )
        }
    )) == "escalate_over_limit"
    assert choose(_reads(
        **{"switch.get_status": _read("switch.get_status", status="pending")}
    )) == "pending"
    assert choose(_reads(
        **{
            "sender.get_debit": _read(
                "sender.get_debit", debited=True, reversal_applied=True, reversed_at=READ_AT
            ),
            "switch.get_status": _read("switch.get_status", status="failed"),
            "beneficiary.get_credit": _read(
                "beneficiary.get_credit", credited=False, amount_kobo=None
            ),
        }
    )) == "already_reversed"
    assert choose(_reads(
        **{
            "switch.get_status": _read("switch.get_status", status="failed"),
            "beneficiary.get_credit": _read(
                "beneficiary.get_credit", credited=False, amount_kobo=None
            ),
        }
    )) == "reverse"
    assert choose(_reads(
        **{
            "switch.get_status": _read("switch.get_status", status="success"),
            "beneficiary.get_credit": _read(
                "beneficiary.get_credit", credited=False, amount_kobo=None
            ),
        }
    )) == "escalate_conflict"
    assert choose(_reads(
        **{
            "sender.get_debit": _read(
                "sender.get_debit", debited=False, reversal_applied=False
            ),
            "switch.get_status": _read("switch.get_status", status="failed"),
            "beneficiary.get_credit": _read(
                "beneficiary.get_credit", credited=False, amount_kobo=None
            ),
        }
    )) == "no_debit"
    assert choose(_reads(
        **{"switch.get_status": ReadResult("switch.get_status", False, None, "timeout")}
    )) == "incomplete"


def test_a_failed_reversal_is_not_treated_as_processed():
    failed = ReadResult("sender.reverse", False, None, "timeout")
    rejected = ReadResult(
        "sender.reverse",
        True,
        {"transfer_id": "TXN-TEST", "status": "rejected", "reason": "not_debited"},
        None,
    )
    accepted = ReadResult(
        "sender.reverse",
        True,
        {"transfer_id": "TXN-TEST", "status": "reversed", "reversed_at": READ_AT},
        None,
    )
    assert outcome_after_reversal(failed) == "incomplete"
    assert outcome_after_reversal(rejected) == "incomplete"
    assert outcome_after_reversal(accepted) == "reversed"
    assert "was processed" in render("reversed", (), accepted)
    assert "was processed" not in render("incomplete", (), failed)


def test_seed_replies_quote_only_the_tool_payload():
    credited = investigate(BY_SEED[1])
    assert credited.outcome == "credited"
    assert credited.reply == (
        "TXN-0001 was credited. Harbor Bank debited account 2100000001 "
        "NGN 5,000.00 at 2026-10-10T03:59:00+01:00. "
        "The switch status is success as of 2026-10-10T03:59:40+01:00. "
        "Cedar Bank credited account 3100000001 at 2026-10-10T04:00:30+01:00."
    )
    assert "sender.reverse" not in credited.tool_order

    over = investigate(BY_SEED[23])
    assert over.outcome == "escalate_over_limit"
    assert over.reply == (
        "NGN 1,500,000.00 is over the NGN 1,000,000.00 limit, so TXN-0023 was not resolved."
    )
    assert "was credited" not in over.reply

    pending = investigate(BY_SEED[29])
    assert pending.outcome == "pending"
    assert pending.reply == (
        "The switch still shows TXN-0029 as pending as of 2026-10-10T03:31:00+01:00."
    )
    clean = investigate(BY_SEED[29], chaos=ChaosFlags())
    assert clean.outcome == "escalate_conflict"
    assert clean.reply == (
        "The records for TXN-0029 disagree. "
        "The switch status is success and the beneficiary was not credited."
    )


def test_timeout_on_reverse_does_not_claim_the_reversal():
    result = investigate(BY_SEED[9], chaos=ChaosFlags(timeout_ops=("sender.reverse",)))
    assert result.outcome == "incomplete"
    assert result.reply == "I could not resolve TXN-0009. sender.reverse failed with timeout."
    assert "was processed" not in result.reply
    assert result.ledger_reversal_applied is False


def test_a_transfer_that_was_not_debited_is_not_reversed():
    base = BY_SEED[9]
    facts = replace(
        base.facts,
        sender_debited=False,
        reversal_applied=False,
        reversed_at=None,
    )
    result = investigate(replace(base, facts=facts, chaos=ChaosFlags()))
    assert result.outcome == "no_debit"
    assert result.reply == "TXN-0009 was not debited, and the beneficiary was not credited."
    assert "sender.reverse" not in result.tool_order
    assert result.ledger_reversal_applied is False
