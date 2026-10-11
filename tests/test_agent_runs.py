"""Every seed finishes, and the lying reversal is the one false 'processed'."""

import subprocess
import sys

from agent.loop import investigate
from agent.report import format_report
from sim.catalog import load_scenarios
from sim.models import ChaosFlags
from tests.helpers import BY_SEED, CATALOG

EXPECTED = {
    **{seed: "credited" for seed in range(1, 9)},
    **{seed: "reversed" for seed in range(9, 15)},
    **{seed: "already_reversed" for seed in range(15, 18)},
    **{seed: "escalate_conflict" for seed in range(18, 23)},
    **{seed: "escalate_over_limit" for seed in range(23, 26)},
    26: "incomplete",
    27: "incomplete",
    28: "reversed",
    29: "pending",
    30: "incomplete",
}


def test_authored_outcomes_and_whether_the_reversal_really_posted():
    assert set(EXPECTED) == set(range(1, 31))
    for scenario in CATALOG:
        result = investigate(scenario)
        again = investigate(scenario)
        assert result.outcome == EXPECTED[scenario.seed]
        assert result.reply == again.reply
        assert result.tool_order[0:4] == (
            "sender.get_debit",
            "sender.get_balance",
            "switch.get_status",
            "beneficiary.get_credit",
        )
        if scenario.seed == 28:
            assert result.ledger_reversal_applied is False
            assert result.tool_order.count("sender.get_debit") == 1
            assert result.tool_order[-1] == "sender.reverse"
            assert "was processed" in result.reply
            assert result.reply == (
                "The reversal for TXN-0028 was processed at 2026-10-10T08:00:05+01:00."
            )
        elif scenario.facts.reversal_applied:
            assert result.outcome == "already_reversed"
            assert result.ledger_reversal_applied is True
            assert "sender.reverse" not in result.tool_order
        elif result.outcome == "reversed":
            assert result.ledger_reversal_applied is True
            assert result.tool_order[-1] == "sender.reverse"
            assert "was processed" in result.reply
        else:
            assert result.ledger_reversal_applied is scenario.facts.reversal_applied
            assert "sender.reverse" not in result.tool_order


def test_chaos_off_uses_ground_truth_for_the_faulted_seeds():
    assert investigate(BY_SEED[26], chaos=ChaosFlags()).outcome == "credited"
    honest = investigate(BY_SEED[28], chaos=ChaosFlags())
    assert honest.outcome == "reversed"
    assert honest.ledger_reversal_applied is True
    assert investigate(BY_SEED[29], chaos=ChaosFlags()).outcome == "escalate_conflict"
    assert investigate(BY_SEED[30], chaos=ChaosFlags()).outcome == "credited"
    missed = investigate(BY_SEED[26])
    dropped = investigate(BY_SEED[27])
    unread = investigate(BY_SEED[30])
    assert missed.reply == "I could not resolve TXN-0026. switch.get_status failed with timeout."
    assert dropped.reply == (
        "I could not resolve TXN-0027. beneficiary.get_credit failed with connection_error."
    )
    assert unread.reply == "I could not resolve TXN-0030. sender.get_debit failed with timeout."
    for result in (missed, dropped, unread):
        assert "was processed" not in result.reply
        assert "was credited" not in result.reply


def test_an_already_reversed_debit_is_not_reversed_again():
    result = investigate(BY_SEED[15])
    assert result.reply == (
        "The debit for TXN-0015 was already reversed at 2026-10-10T03:47:40+01:00."
    )
    assert "was processed" not in result.reply


def test_module_runs_all_thirty_seeds():
    completed = subprocess.run(
        [sys.executable, "-m", "agent"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    seed_lines = [line for line in completed.stdout.splitlines() if line.startswith("seed=")]
    assert seed_lines == format_report(load_scenarios()).splitlines()
