"""A reply is sent only when its claims match spans. A reversal report is not a ledger read."""

from agent.engine import review, run_v1
from agent.loop import investigate
from sim.models import ChaosFlags
from sim.world import open_world
from tests.helpers import BY_SEED, CATALOG

V1_BLOCKED = {9, 10, 11, 12, 13, 14, 28}
SEED_28_V2 = (
    "The reversal tool reported success for TXN-0028 at 2026-10-10T08:00:05+01:00. "
    "The ledger read at 2026-10-10T08:00:06+01:00 still shows the debit open."
)


def test_engine_matches_traced_v1():
    for scenario in CATALOG:
        traced = investigate(scenario)
        plain = run_v1(open_world(scenario))
        assert plain.outcome == traced.outcome
        assert plain.reply == traced.reply
        assert plain.tool_order == traced.tool_order
        assert plain.ledger_reversal_applied == traced.ledger_reversal_applied


def test_v1_blocks_only_unproved_reversals():
    blocked = set()
    for scenario in CATALOG:
        filed = review(scenario)
        assert filed.v2_verdict.allowed, scenario.seed
        assert not filed.v2_verdict.blocks
        if filed.v1_verdict.allowed:
            assert filed.same_reply
        else:
            blocked.add(scenario.seed)
            assert filed.v1.outcome == "reversed"
            assert "was processed" in filed.v1.reply
    assert blocked == V1_BLOCKED


def test_seed_28_lie_is_blocked_then_told_honestly():
    filed = review(BY_SEED[28])
    assert filed.v1.ledger_reversal_applied is False
    assert filed.v2.ledger_reversal_applied is False
    assert filed.v1_verdict.allowed is False
    assert "not a ledger read" in filed.v1_verdict.blocks[0]
    assert filed.v2.outcome == "reversal_not_posted"
    assert filed.v2.reply == SEED_28_V2
    assert filed.v2_verdict.allowed is True
    assert "was processed" not in filed.v2.reply


def test_honest_reversal_is_unproved_until_the_ledger_is_reread():
    filed = review(BY_SEED[9])
    assert filed.v1_verdict.allowed is False
    assert filed.v1.ledger_reversal_applied is True
    assert filed.v2_verdict.allowed is True
    assert filed.v2.ledger_reversal_applied is True
    assert filed.v2.outcome == "reversed"
    assert filed.v2.tool_order[-2:] == ("sender.get_debit", "sender.get_balance")


def test_seed_28_without_chaos_still_needs_the_second_read():
    filed = review(BY_SEED[28], chaos=ChaosFlags())
    assert filed.v1.ledger_reversal_applied is True
    assert filed.v1_verdict.allowed is False
    assert filed.v2.ledger_reversal_applied is True
    assert filed.v2_verdict.allowed is True
    assert filed.v2.outcome == "reversed"


def test_failed_tools_and_pending_are_proved_by_their_spans():
    for seed in (1, 15, 23, 26, 27, 29, 30):
        filed = review(BY_SEED[seed])
        assert filed.v1_verdict.allowed, seed
        assert filed.same_reply
