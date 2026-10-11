"""Claims the reply is asserting, taken from the outcome rather than from every span."""

from dataclasses import dataclass

from agent.result import AgentResult
from sim.constants import ESCALATION_LIMIT_KOBO
from sim.money import format_naira


@dataclass(frozen=True, slots=True)
class Claim:
    name: str
    statement: str
    op: str
    read_at: str | None
    ledger: bool
    expect: tuple[tuple[str, object], ...] = ()
    error: str | None = None


def claims_for(result: AgentResult) -> tuple[Claim, ...]:
    if result.outcome == "reversed":
        return (_reversal_posted(result),)
    if result.outcome == "reversal_not_posted":
        return _reversal_open(result)
    if result.outcome == "incomplete":
        return _failures(result)
    debit = _payload(result, "sender.get_debit")
    switch = _payload(result, "switch.get_status")
    credit = _payload(result, "beneficiary.get_credit")
    if result.outcome == "credited":
        assert debit is not None and switch is not None and credit is not None
        return (
            _claim(
                "debited",
                f"{debit['transfer_id']} was debited {format_naira(debit['amount_kobo'])}.",
                "sender.get_debit",
                debit,
                (("debited", True), ("amount_kobo", debit["amount_kobo"])),
            ),
            _claim(
                "switch_success",
                f"The switch status for {switch['transfer_id']} is success.",
                "switch.get_status",
                switch,
                (("status", "success"),),
            ),
            _claim(
                "credited",
                f"{credit['bank']} credited account {credit['account']}.",
                "beneficiary.get_credit",
                credit,
                (("credited", True),),
            ),
        )
    if result.outcome == "already_reversed":
        assert debit is not None
        return (
            _claim(
                "already_reversed",
                f"The debit for {debit['transfer_id']} was already reversed.",
                "sender.get_debit",
                debit,
                (("reversal_applied", True),),
            ),
        )
    if result.outcome == "pending":
        assert switch is not None
        return (
            _claim(
                "pending",
                f"The switch shows {switch['transfer_id']} as pending.",
                "switch.get_status",
                switch,
                (("status", "pending"),),
                ledger=False,
            ),
        )
    if result.outcome == "escalate_conflict":
        assert switch is not None and credit is not None
        posted = "credited" if credit["credited"] else "not credited"
        return (
            _claim(
                "switch_status",
                f"The switch status is {switch['status']}.",
                "switch.get_status",
                switch,
                (("status", switch["status"]),),
                ledger=False,
            ),
            _claim(
                "credit_status",
                f"The beneficiary was {posted}.",
                "beneficiary.get_credit",
                credit,
                (("credited", credit["credited"]),),
                ledger=False,
            ),
        )
    if result.outcome == "escalate_over_limit":
        source = debit or switch or credit
        assert source is not None
        op = "sender.get_debit" if debit else "switch.get_status" if switch else "beneficiary.get_credit"
        return (
            _claim(
                "over_limit",
                (
                    f"{format_naira(source['amount_kobo'])} is over the "
                    f"{format_naira(ESCALATION_LIMIT_KOBO)} limit."
                ),
                op,
                source,
                (("amount_kobo", source["amount_kobo"]),),
                ledger=False,
            ),
        )
    if result.outcome == "no_debit":
        assert debit is not None and switch is not None and credit is not None
        return (
            _claim(
                "not_debited",
                f"{debit['transfer_id']} was not debited.",
                "sender.get_debit",
                debit,
                (("debited", False),),
            ),
            _claim(
                "switch_failed",
                "The switch status is failed.",
                "switch.get_status",
                switch,
                (("status", "failed"),),
                ledger=False,
            ),
            _claim(
                "not_credited",
                "The beneficiary was not credited.",
                "beneficiary.get_credit",
                credit,
                (("credited", False),),
                ledger=False,
            ),
        )
    return ()


def spans_of(result: AgentResult) -> tuple:
    rows = list(result.reads)
    if result.reversal is not None:
        rows.append(result.reversal)
    return tuple(rows)


def _reversal_posted(result: AgentResult) -> Claim:
    action_at = _action_at(result)
    fresh = None
    for read in spans_of(result):
        if read.op != "sender.get_debit" or not read.ok or read.value is None:
            continue
        if action_at and read.value.get("read_at", "") > action_at and read.value.get("reversal_applied") is True:
            fresh = read.value
    if fresh is not None:
        return _claim(
            "reversal_posted",
            f"The ledger shows the reversal for {fresh['transfer_id']} posted.",
            "sender.get_debit",
            fresh,
            (("reversal_applied", True),),
        )
    value = result.reversal.value if result.reversal and result.reversal.value else {}
    transfer_id = value.get("transfer_id", "this transfer")
    return Claim(
        name="reversal_posted",
        statement=f"The reversal for {transfer_id} posted.",
        op="sender.reverse",
        read_at=value.get("read_at"),
        ledger=True,
        expect=(("status", "reversed"),),
    )


def _reversal_open(result: AgentResult) -> tuple[Claim, ...]:
    value = result.reversal.value if result.reversal and result.reversal.value else {}
    debit = _latest(result, "sender.get_debit")
    assert debit is not None
    return (
        Claim(
            name="tool_reported_reversal",
            statement=(
                f"The reversal tool reported success for {value.get('transfer_id', 'this transfer')}."
            ),
            op="sender.reverse",
            read_at=value.get("read_at"),
            ledger=False,
            expect=(("status", "reversed"),),
        ),
        _claim(
            "debit_still_open",
            f"The ledger read at {debit['read_at']} still shows the debit open.",
            "sender.get_debit",
            debit,
            (("reversal_applied", False),),
        ),
    )


def _failures(result: AgentResult) -> tuple[Claim, ...]:
    claims = []
    for read in spans_of(result):
        if read.ok:
            continue
        claims.append(
            Claim(
                name=f"failed:{read.op}",
                statement=f"{read.op} failed with {read.error}.",
                op=read.op,
                read_at=None,
                ledger=False,
                error=read.error,
            )
        )
    return tuple(claims)


def _payload(result: AgentResult, op: str) -> dict | None:
    found = None
    for read in result.reads:
        if read.op == op and read.ok and read.value is not None:
            found = read.value
    return found


def _latest(result: AgentResult, op: str) -> dict | None:
    return _payload(result, op)


def _action_at(result: AgentResult) -> str | None:
    if result.reversal is None or not result.reversal.ok or result.reversal.value is None:
        return None
    read_at = result.reversal.value.get("read_at")
    return read_at if isinstance(read_at, str) else None


def _claim(
    name: str,
    statement: str,
    op: str,
    payload: dict,
    expect: tuple[tuple[str, object], ...],
    *,
    ledger: bool = True,
) -> Claim:
    return Claim(
        name=name,
        statement=statement,
        op=op,
        read_at=payload.get("read_at"),
        ledger=ledger,
        expect=expect,
    )
