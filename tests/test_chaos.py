"""Chaos flags change observations. They do not change ground truth."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from sim.chaos import ChaosSession
from sim.errors import SimConnectionError, SimNotFound, SimTimeout
from sim.models import ChaosFlags
from sim.world import open_world, run_scenario
from tests.helpers import BY_SEED


def test_connection_error_wins_over_timeout_and_unknown_ops_fail():
    session = ChaosSession(
        ChaosFlags(
            timeout_ops=("switch.get_status",),
            connection_error_ops=("switch.get_status",),
        )
    )
    with pytest.raises(SimConnectionError) as exc:
        session.before("switch.get_status")
    assert exc.value.code == "connection_error"
    with pytest.raises(ValueError, match="unknown op"):
        ChaosSession(ChaosFlags()).before("nope")


def test_timeout_does_not_advance_the_clock_or_consume_the_stale_read():
    scenario = BY_SEED[26]
    world = open_world(scenario)
    assert world.clock.peek() == scenario.complained_at
    debit = world.get_debit()
    assert debit["read_at"] == "2026-10-10T08:00:01+01:00"
    peeked = world.clock.peek()
    with pytest.raises(SimTimeout):
        world.get_switch_status()
    assert world.clock.peek() == peeked
    assert world.session.switch_reads == 0


def test_timeout_hides_not_found_because_the_call_never_reaches_the_ledger():
    world = open_world(BY_SEED[30])
    with pytest.raises(SimTimeout) as exc:
        world.get_debit("TXN-NOPE")
    assert exc.value.op == "sender.get_debit"
    clean = open_world(BY_SEED[30], chaos=ChaosFlags())
    with pytest.raises(SimNotFound):
        clean.get_debit("TXN-NOPE")


def test_stale_switch_status_flips_on_the_second_read():
    scenario = BY_SEED[29]
    world = open_world(scenario)
    first = world.get_switch_status()
    second = world.get_switch_status()
    third = world.get_switch_status()
    assert first["status"] == "pending"
    assert first["updated_at"] == scenario.facts.debit_at
    assert second["status"] == "success"
    assert second["updated_at"] == scenario.facts.switch_updated_at
    assert third["status"] == "success"
    assert first["read_at"] < second["read_at"] < third["read_at"]


def test_forcing_chaos_off_returns_ground_truth_on_the_first_read():
    scenario = BY_SEED[29]
    world = open_world(scenario, chaos=ChaosFlags())
    assert scenario.chaos.stale_switch_status == "pending"
    assert world.chaos.enabled() is False
    first = world.get_switch_status()
    second = world.get_switch_status()
    assert first["status"] == second["status"] == "success"
    assert first["updated_at"] == second["updated_at"] == scenario.facts.switch_updated_at


def test_chaos_can_be_turned_on_for_a_clean_seed():
    run = run_scenario(BY_SEED[1], chaos=ChaosFlags(timeout_ops=("sender.get_balance",)))
    assert [step.error for step in run.steps] == [None, "timeout", None, None]
    assert run.steps[0].value is not None
    assert run.steps[2].value["status"] == "success"


def test_lying_reversal_reports_success_and_does_not_apply():
    scenario = BY_SEED[28]
    world = open_world(scenario)
    before = world.get_balance()["balance_kobo"]
    first = world.reverse()
    second = world.reverse()
    debit = world.get_debit()
    after = world.get_balance()["balance_kobo"]
    assert first["status"] == "reversed"
    assert first["already_applied"] is False
    assert second["status"] == "reversed"
    assert first["reversed_at"] != second["reversed_at"]
    assert debit["reversal_applied"] is False
    assert debit["reversed_at"] is None
    assert after == before
    assert before == scenario.facts.balance_before_kobo - scenario.facts.amount_kobo


def test_same_seed_reverses_honestly_when_the_lie_is_switched_off():
    scenario = BY_SEED[28]
    world = open_world(scenario, chaos=ChaosFlags())
    result = world.reverse()
    debit = world.get_debit()
    balance = world.get_balance()
    assert result["status"] == "reversed"
    assert debit["reversal_applied"] is True
    assert debit["reversed_at"] == result["reversed_at"]
    assert balance["balance_kobo"] == scenario.facts.balance_before_kobo


def test_a_lie_cannot_reverse_a_transfer_that_was_not_debited():
    base = BY_SEED[28]
    facts = replace(
        base.facts,
        sender_debited=False,
        reversal_applied=False,
        reversed_at=None,
    )
    world = open_world(replace(base, facts=facts))
    assert world.reverse()["status"] == "rejected"
    assert world.reverse()["reason"] == "not_debited"
    assert world.get_balance()["balance_kobo"] == facts.balance_before_kobo


def test_honest_reverse_is_idempotent_and_worlds_do_not_share_state():
    scenario = BY_SEED[9]
    first_world = open_world(scenario, chaos=ChaosFlags())
    second_world = open_world(scenario, chaos=ChaosFlags())
    first = first_world.reverse()
    second = first_world.reverse()
    assert first["already_applied"] is False
    assert second["already_applied"] is True
    assert second["reversed_at"] == first["reversed_at"]
    assert first_world.get_balance()["balance_kobo"] == scenario.facts.balance_before_kobo
    assert second_world.get_debit()["reversal_applied"] is False
    assert (
        second_world.get_balance()["balance_kobo"]
        == scenario.facts.balance_before_kobo - scenario.facts.amount_kobo
    )


def test_an_already_posted_reversal_is_not_applied_again():
    scenario = BY_SEED[15]
    world = open_world(scenario)
    balance = world.get_balance()["balance_kobo"]
    result = world.reverse()
    assert balance == scenario.facts.balance_before_kobo
    assert result["already_applied"] is True
    assert result["reversed_at"] == scenario.facts.reversed_at
    assert world.get_balance()["balance_kobo"] == balance


def test_run_records_faults_and_keeps_reading():
    timed_out = run_scenario(BY_SEED[26])
    dropped = run_scenario(BY_SEED[27])
    assert [step.op for step in timed_out.steps] == [
        "sender.get_debit",
        "sender.get_balance",
        "switch.get_status",
        "beneficiary.get_credit",
    ]
    assert timed_out.steps[2].ok is False
    assert timed_out.steps[2].error == "timeout"
    assert timed_out.steps[3].ok is True
    assert timed_out.steps[3].value["credited"] is True
    assert dropped.steps[3].error == "connection_error"
    assert dropped.steps[0].value["debited"] is True

    start = datetime.fromisoformat(BY_SEED[26].complained_at)
    assert timed_out.steps[0].value["read_at"] == (start + timedelta(seconds=1)).isoformat(
        timespec="seconds"
    )
    assert timed_out.steps[1].value["read_at"] == (start + timedelta(seconds=2)).isoformat(
        timespec="seconds"
    )
    assert timed_out.steps[3].value["read_at"] == (start + timedelta(seconds=3)).isoformat(
        timespec="seconds"
    )


def test_authored_read_faults_disappear_when_chaos_is_forced_off():
    expected = {
        26: ("switch.get_status", "success"),
        27: ("beneficiary.get_credit", "not_credited"),
        30: ("sender.get_debit", "debited"),
    }
    for seed, (op, clean_token) in expected.items():
        authored = run_scenario(BY_SEED[seed])
        clean = run_scenario(BY_SEED[seed], chaos=ChaosFlags())
        authored_step = next(step for step in authored.steps if step.op == op)
        clean_step = next(step for step in clean.steps if step.op == op)
        assert authored_step.ok is False
        assert clean_step.ok is True
        assert clean_step != authored_step
        if op == "switch.get_status":
            assert clean_step.value["status"] == clean_token
        elif op == "beneficiary.get_credit":
            assert clean_step.value["credited"] is False
        else:
            assert clean_step.value["debited"] is True


def test_lying_reversal_does_not_change_the_read_transcript():
    scenario = BY_SEED[28]
    assert run_scenario(scenario) == run_scenario(scenario, chaos=ChaosFlags())
