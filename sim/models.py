"""Facts each simulated source is allowed to know, plus a scenario seed."""

from dataclasses import dataclass
from typing import Literal

SwitchStatus = Literal["pending", "success", "failed"]


@dataclass(frozen=True, slots=True)
class TransferFacts:
    transfer_id: str
    sender_account: str
    sender_bank: str
    beneficiary_account: str
    beneficiary_bank: str
    amount_kobo: int
    currency: str
    balance_before_kobo: int
    sender_debited: bool
    debit_at: str
    switch_status: SwitchStatus
    switch_updated_at: str
    beneficiary_credited: bool
    credit_at: str | None
    reversal_applied: bool
    reversed_at: str | None


@dataclass(frozen=True, slots=True)
class ChaosFlags:
    """Per-scenario fault switches. An empty value means that fault is off."""

    timeout_ops: tuple[str, ...] = ()
    connection_error_ops: tuple[str, ...] = ()
    stale_switch_status: str | None = None
    lying_reversal: bool = False
    flaky_ops: tuple[str, ...] = ()  # fail with a timeout on the first call only

    def enabled(self) -> bool:
        return bool(
            self.timeout_ops
            or self.connection_error_ops
            or self.stale_switch_status
            or self.lying_reversal
            or self.flaky_ops
        )


@dataclass(frozen=True, slots=True)
class Scenario:
    seed: int
    pattern: str
    complaint_id: str
    customer_name: str
    narrative: str
    complained_at: str
    facts: TransferFacts
    chaos: ChaosFlags


@dataclass(frozen=True, slots=True)
class StepResult:
    op: str
    ok: bool
    value: dict | None
    error: str | None


@dataclass(frozen=True, slots=True)
class ScenarioRun:
    seed: int
    steps: tuple[StepResult, ...]
