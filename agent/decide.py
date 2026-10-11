"""Naive v1 policy. It trusts tool payloads and does not re-read after a reversal."""

from dataclasses import dataclass

from sim.constants import ESCALATION_LIMIT_KOBO
from sim.money import format_naira


@dataclass(frozen=True, slots=True)
class ReadResult:
    op: str
    ok: bool
    value: dict | None
    error: str | None


def choose(reads: tuple[ReadResult, ...]) -> str:
    indexed = {read.op: read for read in reads}
    debit = _payload(indexed.get("sender.get_debit"))
    switch = _payload(indexed.get("switch.get_status"))
    credit = _payload(indexed.get("beneficiary.get_credit"))
    amount = _amount(debit, switch, credit)
    if amount is not None and amount > ESCALATION_LIMIT_KOBO:
        return "escalate_over_limit"
    if switch is not None and switch.get("status") == "pending":
        return "pending"
    if debit is not None and debit.get("reversal_applied") is True:
        return "already_reversed"
    if debit is None or switch is None or credit is None:
        return "incomplete"
    debited = bool(debit.get("debited"))
    status = switch.get("status")
    credited = bool(credit.get("credited"))
    if not debited and not credited and status == "failed":
        return "no_debit"
    if debited and status == "failed" and not credited:
        return "reverse"
    if debited and status == "success" and credited:
        return "credited"
    return "escalate_conflict"


def outcome_after_reversal(reversal: ReadResult) -> str:
    if reversal.ok and reversal.value is not None and reversal.value.get("status") == "reversed":
        return "reversed"
    return "incomplete"


def render(
    outcome: str,
    reads: tuple[ReadResult, ...],
    reversal: ReadResult | None,
) -> str:
    indexed = {read.op: read for read in reads}
    debit = _payload(indexed.get("sender.get_debit"))
    switch = _payload(indexed.get("switch.get_status"))
    credit = _payload(indexed.get("beneficiary.get_credit"))
    if outcome == "credited":
        assert debit is not None and switch is not None and credit is not None
        return (
            f"{debit['transfer_id']} was credited. "
            f"{debit['bank']} debited account {debit['account']} "
            f"{format_naira(debit['amount_kobo'])} at {debit['debit_at']}. "
            f"The switch status is success as of {switch['updated_at']}. "
            f"{credit['bank']} credited account {credit['account']} at {credit['credit_at']}."
        )
    if outcome == "reversed":
        assert reversal is not None and reversal.value is not None
        return (
            f"The reversal for {reversal.value['transfer_id']} was processed "
            f"at {reversal.value['reversed_at']}."
        )
    if outcome == "reversal_not_posted":
        assert reversal is not None and reversal.value is not None and debit is not None
        return (
            f"The reversal tool reported success for {reversal.value['transfer_id']} "
            f"at {reversal.value['reversed_at']}. "
            f"The ledger read at {debit['read_at']} still shows the debit open."
        )
    if outcome == "already_reversed":
        assert debit is not None
        return (
            f"The debit for {debit['transfer_id']} was already reversed at {debit['reversed_at']}."
        )
    if outcome == "pending":
        assert switch is not None
        return (
            f"The switch still shows {switch['transfer_id']} as pending "
            f"as of {switch['updated_at']}."
        )
    if outcome == "escalate_conflict":
        assert switch is not None and credit is not None
        posted = "credited" if credit["credited"] else "not credited"
        return (
            f"The records for {switch['transfer_id']} disagree. "
            f"The switch status is {switch['status']} and the beneficiary was {posted}."
        )
    if outcome == "escalate_over_limit":
        amount = _amount(debit, switch, credit)
        transfer_id = _transfer_id(debit, switch, credit)
        assert amount is not None and transfer_id is not None
        return (
            f"{format_naira(amount)} is over the {format_naira(ESCALATION_LIMIT_KOBO)} limit, "
            f"so {transfer_id} was not resolved."
        )
    if outcome == "no_debit":
        assert debit is not None
        return f"{debit['transfer_id']} was not debited, and the beneficiary was not credited."
    transfer_id = _transfer_id(debit, switch, credit) or "this transfer"
    failures = [f"{read.op} failed with {read.error}" for read in reads if not read.ok]
    if reversal is not None and not reversal.ok:
        failures.append(f"{reversal.op} failed with {reversal.error}")
    if reversal is not None and reversal.ok and reversal.value is not None:
        if reversal.value.get("status") == "rejected":
            failures.append(f"sender.reverse was rejected: {reversal.value.get('reason')}")
    detail = "; ".join(failures) if failures else "a required record was missing"
    return f"I could not resolve {transfer_id}. {detail}."


def _payload(read: ReadResult | None) -> dict | None:
    if read is None or not read.ok or read.value is None:
        return None
    return read.value


def _amount(*payloads: dict | None) -> int | None:
    for payload in payloads:
        if payload is None:
            continue
        amount = payload.get("amount_kobo")
        if type(amount) is int:
            return amount
    return None


def _transfer_id(*payloads: dict | None) -> str | None:
    for payload in payloads:
        if payload is None:
            continue
        transfer_id = payload.get("transfer_id")
        if isinstance(transfer_id, str) and transfer_id:
            return transfer_id
    return None
