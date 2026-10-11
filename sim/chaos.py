"""Fault switches consulted before a source returns its ground truth."""

from sim.constants import OPS
from sim.errors import SimConnectionError, SimTimeout
from sim.models import ChaosFlags


class ChaosSession:
    def __init__(self, flags: ChaosFlags):
        self.flags = flags
        self.switch_reads = 0

    def before(self, op: str) -> None:
        if op not in OPS:
            raise ValueError(f"unknown op {op}")
        if op in self.flags.connection_error_ops:
            raise SimConnectionError(op)
        if op in self.flags.timeout_ops:
            raise SimTimeout(op)

    def displayed_switch_status(self, actual: str) -> str:
        self.switch_reads += 1
        if self.flags.stale_switch_status and self.switch_reads == 1:
            return self.flags.stale_switch_status
        return actual

    def reversal_should_apply(self) -> bool:
        return not self.flags.lying_reversal
