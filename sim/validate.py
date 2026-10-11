"""Reject scenario seeds whose facts, clocks, or chaos flags cannot be replayed."""

from datetime import datetime

from sim.clock import isoformat
from sim.constants import CURRENCY, GROUND_SWITCH_STATUSES, OPS, SWITCH_STATUSES
from sim.models import ChaosFlags, Scenario, TransferFacts
from sim.patterns import PATTERNS


def _parsed(label: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    if isoformat(parsed) != value:
        raise ValueError(f"{label} must be second-precision ISO-8601")
    return parsed


def _validate_chaos(facts: TransferFacts, chaos: ChaosFlags) -> None:
    if type(chaos.lying_reversal) is not bool:
        raise ValueError("lying_reversal must be a bool")
    for name, ops in (
        ("timeout_ops", chaos.timeout_ops),
        ("connection_error_ops", chaos.connection_error_ops),
    ):
        if len(ops) != len(set(ops)):
            raise ValueError(f"duplicate op in {name}")
        unknown = [op for op in ops if op not in OPS]
        if unknown:
            raise ValueError(f"unknown op {unknown[0]}")
    overlap = set(chaos.timeout_ops) & set(chaos.connection_error_ops)
    if overlap:
        raise ValueError(f"op {sorted(overlap)[0]} cannot both time out and drop")
    if chaos.stale_switch_status is None:
        return
    if chaos.stale_switch_status not in SWITCH_STATUSES:
        raise ValueError(f"stale switch status {chaos.stale_switch_status} is invalid")
    if chaos.stale_switch_status == facts.switch_status:
        raise ValueError("stale switch status must differ from ground truth")


def _validate_facts(facts: TransferFacts, complained_at: datetime) -> None:
    if type(facts.amount_kobo) is not int or type(facts.balance_before_kobo) is not int:
        raise ValueError("money fields must be ints")
    for label, flag in (
        ("sender_debited", facts.sender_debited),
        ("beneficiary_credited", facts.beneficiary_credited),
        ("reversal_applied", facts.reversal_applied),
    ):
        if type(flag) is not bool:
            raise ValueError(f"{label} must be a bool")
    if facts.currency != CURRENCY:
        raise ValueError(f"currency must be {CURRENCY}")
    if facts.amount_kobo <= 0:
        raise ValueError("amount_kobo must be positive")
    if facts.balance_before_kobo < 0:
        raise ValueError("balance_before_kobo must be >= 0")
    if facts.sender_debited and facts.balance_before_kobo < facts.amount_kobo:
        raise ValueError("balance_before_kobo cannot cover the debit")
    if facts.switch_status not in GROUND_SWITCH_STATUSES:
        raise ValueError("ground-truth switch status cannot be pending")
    if not facts.transfer_id:
        raise ValueError("transfer_id is empty")
    if facts.sender_account == facts.beneficiary_account:
        raise ValueError("sender and beneficiary accounts must differ")
    for label, account in (
        ("sender account", facts.sender_account),
        ("beneficiary account", facts.beneficiary_account),
    ):
        if len(account) != 10 or not account.isdigit():
            raise ValueError(f"{label} must be 10 digits")
    if not facts.sender_bank or not facts.beneficiary_bank:
        raise ValueError("bank name is empty")
    if facts.sender_bank == facts.beneficiary_bank:
        raise ValueError("sender and beneficiary banks must differ")
    if facts.beneficiary_credited and facts.reversal_applied:
        raise ValueError("a credited transfer cannot also be reversed")
    if facts.reversal_applied and not facts.sender_debited:
        raise ValueError("reversal requires a debit")

    debit_at = _parsed("debit_at", facts.debit_at)
    switch_at = _parsed("switch_updated_at", facts.switch_updated_at)
    if not (debit_at < switch_at < complained_at):
        raise ValueError("debit, switch, and complaint timestamps are out of order")
    if facts.beneficiary_credited:
        if facts.credit_at is None:
            raise ValueError("credited transfer requires credit_at")
        credit_at = _parsed("credit_at", facts.credit_at)
        if not (switch_at < credit_at < complained_at):
            raise ValueError("credit_at is out of order")
    elif facts.credit_at is not None:
        raise ValueError("credit_at must be empty when the beneficiary was not credited")
    if facts.reversal_applied:
        if facts.reversed_at is None:
            raise ValueError("reversed transfer requires reversed_at")
        reversed_at = _parsed("reversed_at", facts.reversed_at)
        if not (switch_at < reversed_at < complained_at):
            raise ValueError("reversed_at is out of order")
    elif facts.reversed_at is not None:
        raise ValueError("reversed_at must be empty when no reversal posted")


def validate_scenario(scenario: Scenario) -> None:
    if type(scenario.seed) is not int:
        raise ValueError("seed must be an int")
    if scenario.seed < 1:
        raise ValueError("seed must be >= 1")
    if scenario.pattern not in PATTERNS:
        raise ValueError(f"unknown pattern {scenario.pattern}")
    if not scenario.complaint_id or not scenario.customer_name.strip():
        raise ValueError("complaint identity is empty")
    if not scenario.narrative.strip():
        raise ValueError("narrative is empty")
    if scenario.facts.transfer_id not in scenario.narrative:
        raise ValueError("narrative must cite the transfer id")
    complained_at = _parsed("complained_at", scenario.complained_at)
    spec = PATTERNS[scenario.pattern]
    for key, expected in spec.items():
        actual = getattr(scenario.facts, key)
        if actual != expected:
            raise ValueError(f"{scenario.pattern} requires {key}={expected}")
    _validate_facts(scenario.facts, complained_at)
    _validate_chaos(scenario.facts, scenario.chaos)
