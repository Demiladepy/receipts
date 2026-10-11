"""Span-free investigation for the demo. The traced CLI path stays in agent.loop."""

from dataclasses import dataclass

from agent.decide import ReadResult, choose, outcome_after_reversal, render
from agent.result import AgentResult
from sim.constants import READ_OPS
from sim.errors import SimError
from sim.models import ChaosFlags, Scenario
from sim.world import World, open_world
from verifier.check import Verdict, verify

_CALLS = {
    "sender.get_debit": "get_debit",
    "sender.get_balance": "get_balance",
    "switch.get_status": "get_switch_status",
    "beneficiary.get_credit": "get_credit",
    "sender.reverse": "reverse",
}


@dataclass(frozen=True, slots=True)
class Review:
    v1: AgentResult
    v2: AgentResult
    v1_verdict: Verdict
    v2_verdict: Verdict

    @property
    def same_reply(self) -> bool:
        return self.v1_verdict.allowed and self.v1.reply == self.v2.reply


def review(scenario: Scenario, *, chaos: ChaosFlags | None = None) -> Review:
    """Run v1, and re-read the ledger when a reversal claim is unproved."""
    world = open_world(scenario, chaos=chaos)
    v1 = run_v1(world)
    v1_verdict = verify(v1)
    if v1_verdict.allowed or v1.outcome != "reversed":
        return Review(v1, v1, v1_verdict, v1_verdict)
    v2 = _reread(world, v1)
    return Review(v1, v2, v1_verdict, verify(v2))


def run_v1(world: World) -> AgentResult:
    order: list[str] = []
    reads: list[ReadResult] = []
    for op in READ_OPS:
        order.append(op)
        reads.append(call(world, op))
    packed = tuple(reads)
    action = choose(packed)
    reversal = None
    if action == "reverse":
        order.append("sender.reverse")
        reversal = call(world, "sender.reverse")
        outcome = outcome_after_reversal(reversal)
    else:
        outcome = action
    return AgentResult(
        seed=world.scenario.seed,
        outcome=outcome,
        reply=render(outcome, packed, reversal),
        reads=packed,
        reversal=reversal,
        tool_order=tuple(order),
        ledger_reversal_applied=world.ledger.reversal_applied,
    )


def call(world: World, op: str) -> ReadResult:
    try:
        value = getattr(world, _CALLS[op])()
    except SimError as exc:
        return ReadResult(op=op, ok=False, value=None, error=exc.code)
    return ReadResult(op=op, ok=True, value=value, error=None)


def _reread(world: World, v1: AgentResult) -> AgentResult:
    extra: list[ReadResult] = []
    order = list(v1.tool_order)
    for op in ("sender.get_debit", "sender.get_balance"):
        order.append(op)
        extra.append(call(world, op))
    reads = v1.reads + tuple(extra)
    debit = extra[0]
    if debit.ok and debit.value is not None and debit.value.get("reversal_applied") is True:
        outcome = "reversed"
    elif debit.ok and debit.value is not None:
        outcome = "reversal_not_posted"
    else:
        outcome = "incomplete"
    return AgentResult(
        seed=v1.seed,
        outcome=outcome,
        reply=render(outcome, reads, v1.reversal),
        reads=reads,
        reversal=v1.reversal,
        tool_order=tuple(order),
        ledger_reversal_applied=world.ledger.reversal_applied,
    )
