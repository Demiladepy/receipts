"""Run the naive v1 agent on all 30 seeds."""

from agent.report import format_report
from agent.tracing import init_tracing
from sim.catalog import load_scenarios


def main() -> None:
    init_tracing(tags=["prompt:v1"])
    print(format_report(load_scenarios()), end="")


if __name__ == "__main__":
    main()
