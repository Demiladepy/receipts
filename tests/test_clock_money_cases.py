"""Clock, money formatting, and ground-truth case classification."""

from datetime import datetime, timedelta, timezone

import pytest

from sim.cases import case_type, sources_conflict
from sim.clock import Clock, isoformat
from sim.constants import ESCALATION_LIMIT_KOBO
from sim.money import format_naira
from tests.helpers import facts


def test_format_naira_keeps_kobo():
    assert format_naira(500_000) == "NGN 5,000.00"
    assert format_naira(50) == "NGN 0.50"
    assert format_naira(0) == "NGN 0.00"


def test_format_naira_rejects_non_ints():
    with pytest.raises(TypeError):
        format_naira(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        format_naira(1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        format_naira(-1)


def test_clock_advances_one_second_per_successful_read():
    start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone(timedelta(hours=1)))
    clock = Clock(start)
    assert clock.peek() == "2026-10-10T08:00:00+01:00"
    assert clock.peek() == "2026-10-10T08:00:00+01:00"
    assert clock.now() == "2026-10-10T08:00:01+01:00"
    assert clock.now() == "2026-10-10T08:00:02+01:00"
    assert clock.peek() == "2026-10-10T08:00:02+01:00"


def test_clock_and_isoformat_reject_naive_datetimes():
    with pytest.raises(ValueError, match="timezone-aware"):
        Clock(datetime(2026, 10, 10, 8, 0))
    with pytest.raises(ValueError, match="timezone-aware"):
        isoformat(datetime(2026, 10, 10, 8, 0))


def test_case_type_matrix():
    assert case_type(facts()) == "credited"
    assert case_type(facts(amount_kobo=ESCALATION_LIMIT_KOBO)) == "credited"
    assert case_type(facts(amount_kobo=ESCALATION_LIMIT_KOBO + 1)) == "escalate_over_limit"
    assert (
        case_type(
            facts(
                amount_kobo=ESCALATION_LIMIT_KOBO + 1,
                beneficiary_credited=False,
                credit_at=None,
            )
        )
        == "escalate_over_limit"
    )
    assert (
        case_type(facts(beneficiary_credited=False, credit_at=None, switch_status="success"))
        == "escalate_conflict"
    )
    assert (
        case_type(facts(switch_status="failed", beneficiary_credited=True))
        == "escalate_conflict"
    )
    assert (
        case_type(
            facts(
                switch_status="failed",
                beneficiary_credited=False,
                credit_at=None,
                reversal_applied=False,
            )
        )
        == "failed_reverse"
    )
    assert (
        case_type(
            facts(
                switch_status="failed",
                beneficiary_credited=False,
                credit_at=None,
                reversal_applied=True,
                reversed_at="2026-10-10T04:02:40+01:00",
            )
        )
        == "reversed"
    )
    assert (
        case_type(
            facts(
                sender_debited=False,
                switch_status="failed",
                beneficiary_credited=False,
                credit_at=None,
            )
        )
        == "no_debit"
    )
    assert case_type(facts(switch_status="pending")) == "escalate_conflict"


def test_conflict_wins_over_a_reversal_when_the_switch_says_success():
    disputed = facts(
        beneficiary_credited=False,
        credit_at=None,
        reversal_applied=True,
        reversed_at="2026-10-10T04:02:40+01:00",
    )
    assert sources_conflict(disputed) is True
    assert case_type(disputed) == "escalate_conflict"


def test_failed_transfer_is_not_a_source_conflict():
    failed = facts(
        switch_status="failed",
        beneficiary_credited=False,
        credit_at=None,
    )
    assert sources_conflict(failed) is False


def test_unclassified_combination_raises():
    with pytest.raises(ValueError, match="unclassified"):
        case_type(facts(reversal_applied=True, reversed_at="2026-10-10T04:02:40+01:00"))
