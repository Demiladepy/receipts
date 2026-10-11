"""One fresh world per run. Scenario facts are never mutated in place."""

from datetime import datetime

from sim.beneficiary import BeneficiaryBank
from sim.chaos import ChaosSession
from sim.clock import Clock
from sim.constants import READ_OPS
from sim.errors import SimError
from sim.ledger import SenderLedger
from sim.models import ChaosFlags, Scenario, ScenarioRun, StepResult
from sim.switch import Switch


class World:
    def __init__(self, scenario: Scenario, chaos: ChaosFlags):
        self.scenario = scenario
        self.chaos = chaos
        self.facts = scenario.facts
        self.clock = Clock(self._start())
        self.session = ChaosSession(chaos)
        self.ledger = SenderLedger(scenario.facts)
        self.switch = Switch(scenario.facts)
        self.beneficiary = BeneficiaryBank(scenario.facts)

    def _start(self) -> datetime:
        return datetime.fromisoformat(self.scenario.complained_at)

    def get_debit(self, transfer_id: str | None = None) -> dict:
        op = "sender.get_debit"
        self.session.before(op)
        return self.ledger.get_debit(transfer_id or self.facts.transfer_id, self.clock.now())

    def get_balance(self, account: str | None = None) -> dict:
        op = "sender.get_balance"
        self.session.before(op)
        return self.ledger.get_balance(account or self.facts.sender_account, self.clock.now())

    def get_switch_status(self, transfer_id: str | None = None) -> dict:
        op = "switch.get_status"
        self.session.before(op)
        read_at = self.clock.now()
        status = self.session.displayed_switch_status(self.facts.switch_status)
        updated_at = self.facts.switch_updated_at
        if status != self.facts.switch_status:
            updated_at = self.facts.debit_at
        return self.switch.get_status(
            transfer_id or self.facts.transfer_id,
            read_at,
            status=status,
            updated_at=updated_at,
        )

    def get_credit(self, transfer_id: str | None = None) -> dict:
        op = "beneficiary.get_credit"
        self.session.before(op)
        return self.beneficiary.get_credit(transfer_id or self.facts.transfer_id, self.clock.now())

    def reverse(self, transfer_id: str | None = None) -> dict:
        op = "sender.reverse"
        self.session.before(op)
        return self.ledger.reverse(
            transfer_id or self.facts.transfer_id,
            self.clock.now(),
            apply=self.session.reversal_should_apply(),
        )


def open_world(scenario: Scenario, *, chaos: ChaosFlags | None = None) -> World:
    """Open a fresh world. Pass ChaosFlags() to force every fault off."""
    flags = scenario.chaos if chaos is None else chaos
    return World(scenario, flags)


def run_scenario(scenario: Scenario, *, chaos: ChaosFlags | None = None) -> ScenarioRun:
    """Read debit, balance, switch, and beneficiary. Faults are recorded, not raised."""
    world = open_world(scenario, chaos=chaos)
    calls = {
        "sender.get_debit": world.get_debit,
        "sender.get_balance": world.get_balance,
        "switch.get_status": world.get_switch_status,
        "beneficiary.get_credit": world.get_credit,
    }
    steps: list[StepResult] = []
    for op in READ_OPS:
        try:
            steps.append(StepResult(op=op, ok=True, value=calls[op](), error=None))
        except SimError as exc:
            steps.append(StepResult(op=op, ok=False, value=None, error=exc.code))
    return ScenarioRun(seed=scenario.seed, steps=tuple(steps))
