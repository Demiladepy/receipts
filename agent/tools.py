"""Tool calls around one world. A raised tool error becomes a failed trace span."""

import neatlogs

from sim.errors import SimError
from sim.world import World


class ToolFailure(Exception):
    def __init__(self, op: str, code: str):
        self.op = op
        self.code = code
        super().__init__(f"{code} during {op}")


class Toolbelt:
    def __init__(self, world: World):
        self.world = world
        self.order: list[str] = []

    @neatlogs.span(
        kind="TOOL",
        name="sender.get_debit",
        tool_name="sender.get_debit",
        capture_input=False,
    )
    def get_debit(self) -> dict:
        return self._call("sender.get_debit", self.world.get_debit)

    @neatlogs.span(
        kind="TOOL",
        name="sender.get_balance",
        tool_name="sender.get_balance",
        capture_input=False,
    )
    def get_balance(self) -> dict:
        return self._call("sender.get_balance", self.world.get_balance)

    @neatlogs.span(
        kind="TOOL",
        name="switch.get_status",
        tool_name="switch.get_status",
        capture_input=False,
    )
    def get_switch_status(self) -> dict:
        return self._call("switch.get_status", self.world.get_switch_status)

    @neatlogs.span(
        kind="TOOL",
        name="beneficiary.get_credit",
        tool_name="beneficiary.get_credit",
        capture_input=False,
    )
    def get_credit(self) -> dict:
        return self._call("beneficiary.get_credit", self.world.get_credit)

    @neatlogs.span(
        kind="TOOL",
        name="sender.reverse",
        tool_name="sender.reverse",
        capture_input=False,
    )
    def reverse(self) -> dict:
        return self._call("sender.reverse", self.world.reverse)

    def _call(self, op: str, fn):
        self.order.append(op)
        try:
            return fn()
        except SimError as exc:
            raise ToolFailure(op, exc.code) from exc
