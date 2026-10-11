"""One complaint in, one reply out. v1 does not re-read the ledger after a reversal."""

import neatlogs

from agent.decide import ReadResult, choose, outcome_after_reversal, render
from agent.prompt import PROMPT_VERSION
from agent.result import AgentResult
from agent.tools import ToolFailure, Toolbelt
from sim.constants import READ_OPS
from sim.models import ChaosFlags, Scenario
from sim.world import World, open_world

_READS = {
    "sender.get_debit": "get_debit",
    "sender.get_balance": "get_balance",
    "switch.get_status": "get_switch_status",
    "beneficiary.get_credit": "get_credit",
}


def investigate(scenario: Scenario, *, chaos: ChaosFlags | None = None) -> AgentResult:
    return _investigate(scenario.seed, open_world(scenario, chaos=chaos))


@neatlogs.span(
    kind="AGENT",
    name="receipts.investigate",
    version=PROMPT_VERSION,
    tags=[f"prompt:{PROMPT_VERSION}"],
    capture_input=False,
    capture_output=False,
)
def _investigate(seed: int, world: World) -> AgentResult:
    belt = Toolbelt(world)
    reads = tuple(_capture(op, getattr(belt, _READS[op])) for op in READ_OPS)
    action = choose(reads)
    reversal = None
    if action == "reverse":
        reversal = _capture("sender.reverse", belt.reverse)
        outcome = outcome_after_reversal(reversal)
    else:
        outcome = action
    return AgentResult(
        seed=seed,
        outcome=outcome,
        reply=render(outcome, reads, reversal),
        reads=reads,
        reversal=reversal,
        tool_order=tuple(belt.order),
        ledger_reversal_applied=world.ledger.reversal_applied,
    )


def _capture(op: str, fn) -> ReadResult:
    try:
        return ReadResult(op=op, ok=True, value=fn(), error=None)
    except ToolFailure as exc:
        return ReadResult(op=op, ok=False, value=None, error=exc.code)
