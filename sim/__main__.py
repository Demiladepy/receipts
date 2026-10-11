"""Run all 30 seeds and print one line each."""

from sim.catalog import load_scenarios
from sim.report import format_report


def main() -> None:
    print(format_report(load_scenarios()), end="")


if __name__ == "__main__":
    main()
