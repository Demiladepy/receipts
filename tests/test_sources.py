"""Each source answers only for the facts it owns."""

from dataclasses import replace

import pytest

from sim.beneficiary import BeneficiaryBank
from sim.errors import SimNotFound
from sim.ledger import SenderLedger
from sim.switch import Switch
from tests.helpers import BY_SEED

READ_AT = "2026-10-10T08:00:01+01:00"


def test_ledger_reports_the_debit_and_the_reduced_balance():
    facts = BY_SEED[1].facts
    ledger = SenderLedger(facts)
    debit = ledger.get_debit(facts.transfer_id, READ_AT)
    balance = ledger.get_balance(facts.sender_account, READ_AT)
    assert debit["debited"] is True
    assert debit["amount_kobo"] == 500_000
    assert debit["reversal_applied"] is False
    assert debit["reversed_at"] is None
    assert balance["balance_kobo"] == 999_500_000
    assert set(debit) == {
        "transfer_id",
        "account",
        "bank",
        "amount_kobo",
        "currency",
        "debited",
        "debit_at",
        "reversal_applied",
        "reversed_at",
        "read_at",
    }
    assert "credited" not in debit
    assert "status" not in debit


def test_honest_reverse_restores_the_balance_once():
    facts = BY_SEED[9].facts
    ledger = SenderLedger(facts)
    first = ledger.reverse(facts.transfer_id, READ_AT, apply=True)
    second = ledger.reverse(facts.transfer_id, "2026-10-10T08:00:02+01:00", apply=True)
    assert first == {
        "transfer_id": facts.transfer_id,
        "status": "reversed",
        "already_applied": False,
        "reversed_at": READ_AT,
        "read_at": READ_AT,
    }
    assert second["already_applied"] is True
    assert second["reversed_at"] == READ_AT
    assert ledger.get_debit(facts.transfer_id, READ_AT)["reversal_applied"] is True
    assert ledger.balance_kobo() == facts.balance_before_kobo


def test_unapplied_reverse_leaves_the_ledger_unchanged():
    facts = BY_SEED[9].facts
    ledger = SenderLedger(facts)
    before = ledger.balance_kobo()
    result = ledger.reverse(facts.transfer_id, READ_AT, apply=False)
    assert result["status"] == "reversed"
    assert result["already_applied"] is False
    assert ledger.balance_kobo() == before
    debit = ledger.get_debit(facts.transfer_id, READ_AT)
    assert debit["reversal_applied"] is False
    assert debit["reversed_at"] is None


def test_reverse_rejects_a_transfer_that_was_not_debited():
    facts = replace(BY_SEED[9].facts, sender_debited=False)
    ledger = SenderLedger(facts)
    result = ledger.reverse(facts.transfer_id, READ_AT, apply=True)
    assert result == {
        "transfer_id": facts.transfer_id,
        "status": "rejected",
        "reason": "not_debited",
        "read_at": READ_AT,
    }
    assert ledger.balance_kobo() == facts.balance_before_kobo


def test_already_reversed_ledger_does_not_credit_twice():
    facts = BY_SEED[15].facts
    ledger = SenderLedger(facts)
    assert ledger.balance_kobo() == facts.balance_before_kobo
    result = ledger.reverse(facts.transfer_id, READ_AT, apply=True)
    assert result["already_applied"] is True
    assert result["reversed_at"] == facts.reversed_at
    assert ledger.balance_kobo() == facts.balance_before_kobo


def test_ledger_unknown_ids_raise():
    facts = BY_SEED[1].facts
    ledger = SenderLedger(facts)
    with pytest.raises(SimNotFound) as debit_error:
        ledger.get_debit("TXN-NOPE", READ_AT)
    with pytest.raises(SimNotFound) as balance_error:
        ledger.get_balance("0000000000", READ_AT)
    with pytest.raises(SimNotFound):
        ledger.reverse("TXN-NOPE", READ_AT, apply=True)
    assert debit_error.value.code == "not_found"
    assert debit_error.value.identifier == "TXN-NOPE"
    assert balance_error.value.op == "sender.get_balance"


def test_switch_and_beneficiary_stay_on_their_own_facts():
    credited = BY_SEED[1].facts
    missing = BY_SEED[9].facts
    switch = Switch(credited)
    status = switch.get_status(credited.transfer_id, READ_AT)
    overridden = switch.get_status(
        credited.transfer_id,
        READ_AT,
        status="pending",
        updated_at=credited.debit_at,
    )
    posted = BeneficiaryBank(credited).get_credit(credited.transfer_id, READ_AT)
    absent = BeneficiaryBank(missing).get_credit(missing.transfer_id, READ_AT)
    assert status["status"] == "success"
    assert status["updated_at"] == credited.switch_updated_at
    assert overridden["status"] == "pending"
    assert overridden["updated_at"] == credited.debit_at
    assert set(status) == {
        "transfer_id",
        "status",
        "amount_kobo",
        "currency",
        "updated_at",
        "read_at",
    }
    assert "balance_kobo" not in status
    assert "debited" not in status
    assert posted["credited"] is True
    assert posted["amount_kobo"] == credited.amount_kobo
    assert posted["credit_at"] == credited.credit_at
    assert absent["credited"] is False
    assert absent["amount_kobo"] is None
    assert absent["credit_at"] is None
    assert "reversal_applied" not in posted
    with pytest.raises(SimNotFound):
        switch.get_status("TXN-NOPE", READ_AT)
    with pytest.raises(SimNotFound):
        BeneficiaryBank(credited).get_credit("TXN-NOPE", READ_AT)
