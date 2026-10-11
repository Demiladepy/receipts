"""One line per complaint for the v1 run."""

from agent.loop import AgentResult, investigate
from sim.models import Scenario


def format_result(result: AgentResult) -> str:
    tools = ",".join(result.tool_order)
    return f"seed={result.seed:03d} outcome={result.outcome} tools={tools}"


def format_report(scenarios: tuple[Scenario, ...] | list[Scenario]) -> str:
    lines = [format_result(investigate(scenario)) for scenario in scenarios]
    return "\n".join(lines) + "\n"
