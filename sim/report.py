"""Text report of one clean read pass per seed."""

from sim.cases import case_type
from sim.models import ChaosFlags, Scenario, ScenarioRun, StepResult
from sim.world import run_scenario


def chaos_label(chaos: ChaosFlags) -> str:
    parts: list[str] = []
    if chaos.timeout_ops:
        parts.append("timeout:" + ",".join(chaos.timeout_ops))
    if chaos.connection_error_ops:
        parts.append("connection_error:" + ",".join(chaos.connection_error_ops))
    if chaos.stale_switch_status:
        parts.append("stale:" + chaos.stale_switch_status)
    if chaos.lying_reversal:
        parts.append("lying_reversal")
    return "+".join(parts) if parts else "off"


def summarize_step(step: StepResult) -> str:
    if not step.ok:
        return step.error or "error"
    assert step.value is not None
    if step.op == "sender.get_debit":
        return "debited" if step.value["debited"] else "not_debited"
    if step.op == "sender.get_balance":
        return str(step.value["balance_kobo"])
    if step.op == "switch.get_status":
        return str(step.value["status"])
    if step.op == "beneficiary.get_credit":
        return "credited" if step.value["credited"] else "not_credited"
    return "ok"


def format_run(scenario: Scenario, run: ScenarioRun) -> str:
    parts = [
        f"seed={scenario.seed:03d}",
        f"case={case_type(scenario.facts)}",
        f"chaos={chaos_label(scenario.chaos)}",
    ]
    parts.extend(f"{step.op}={summarize_step(step)}" for step in run.steps)
    return " ".join(parts)


def format_report(scenarios: tuple[Scenario, ...] | list[Scenario]) -> str:
    lines = [format_run(scenario, run_scenario(scenario)) for scenario in scenarios]
    return "\n".join(lines) + "\n"
