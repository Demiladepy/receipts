"""What one investigation returns. This module does not import neatlogs."""

from dataclasses import dataclass

from agent.decide import ReadResult


@dataclass(frozen=True, slots=True)
class AgentResult:
    seed: int
    outcome: str
    reply: str
    reads: tuple[ReadResult, ...]
    reversal: ReadResult | None
    tool_order: tuple[str, ...]
    ledger_reversal_applied: bool
