"""The same seed produces the same run, and chaos is a switch on that run."""

import subprocess
import sys
from datetime import datetime, timedelta

from sim.catalog import build_catalog, load_scenarios
from sim.constants import READ_OPS
from sim.models import ChaosFlags
from sim.report import format_report
from sim.world import open_world, run_scenario
from tests.helpers import BY_SEED, CATALOG

SEED_ONE_LINE = (
    "seed=001 case=credited chaos=off "
    "sender.get_debit=debited sender.get_balance=999500000 "
    "switch.get_status=success beneficiary.get_credit=credited"
)


def test_every_seed_replays_and_a_clean_pass_reads_four_later_timestamps():
    for scenario in CATALOG:
        assert run_scenario(scenario) == run_scenario(scenario)
        clean = run_scenario(scenario, chaos=ChaosFlags())
        again = run_scenario(scenario, chaos=ChaosFlags())
        assert clean == again
        assert [step.op for step in clean.steps] == list(READ_OPS)
        assert all(step.ok and step.value is not None for step in clean.steps)
        start = datetime.fromisoformat(scenario.complained_at)
        for offset, step in enumerate(clean.steps, start=1):
            assert step.value["read_at"] == (start + timedelta(seconds=offset)).isoformat(
                timespec="seconds"
            )
            walk(step.value)


def walk(value: object) -> None:
    assert not isinstance(value, float)
    if isinstance(value, dict):
        for item in value.values():
            walk(item)
    elif isinstance(value, list):
        for item in value:
            walk(item)


def test_mutating_one_world_does_not_change_the_next_run():
    scenario = BY_SEED[9]
    world = open_world(scenario, chaos=ChaosFlags())
    world.reverse()
    assert world.get_debit()["reversal_applied"] is True
    fresh = run_scenario(scenario)
    assert fresh == run_scenario(scenario)
    debit = next(step for step in fresh.steps if step.op == "sender.get_debit")
    assert debit.value["reversal_applied"] is False


def test_report_lists_ground_truth_cases_and_observed_faults():
    report = format_report(CATALOG)
    assert report == format_report(load_scenarios())
    lines = report.splitlines()
    assert len(lines) == 30
    assert lines[0] == SEED_ONE_LINE
    assert "case=credited" in lines[25]
    assert "chaos=timeout:switch.get_status" in lines[25]
    assert "switch.get_status=timeout" in lines[25]
    assert "case=escalate_conflict" in lines[28]
    assert "chaos=stale:pending" in lines[28]
    assert "switch.get_status=pending" in lines[28]
    assert "chaos=lying_reversal" in lines[27]
    assert "sender.get_debit=debited" in lines[27]
    assert lines[29].startswith("seed=030 case=credited chaos=timeout:sender.get_debit ")
    assert "sender.get_debit=timeout" in lines[29]


def test_module_runs_all_thirty_seeds():
    completed = subprocess.run(
        [sys.executable, "-m", "sim"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == format_report(build_catalog()).splitlines()
