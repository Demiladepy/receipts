"""The 30 seeds stay internally consistent and match scenarios/seeds.json."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime

import pytest

from sim.cases import case_type
from sim.catalog import (
    SEEDS_PATH,
    build_catalog,
    document_from,
    load_scenarios,
    loads_document,
    write_seeds,
)
from sim.constants import ESCALATION_LIMIT_KOBO, SEED_COUNT
from sim.models import ChaosFlags
from sim.patterns import PATTERNS
from sim.validate import validate_scenario
from tests.helpers import BY_SEED, CATALOG


def test_catalog_is_thirty_ordered_seeds():
    assert [scenario.seed for scenario in CATALOG] == list(range(1, SEED_COUNT + 1))
    assert len({scenario.complaint_id for scenario in CATALOG}) == SEED_COUNT
    assert len({scenario.facts.transfer_id for scenario in CATALOG}) == SEED_COUNT
    assert {scenario.pattern for scenario in CATALOG} == set(PATTERNS)


def test_every_complaint_was_debited_and_the_case_mix_is_fixed():
    counts: dict[str, int] = {}
    for scenario in CATALOG:
        assert scenario.facts.sender_debited is True
        kind = case_type(scenario.facts)
        counts[kind] = counts.get(kind, 0) + 1
    assert counts == {
        "credited": 10,
        "failed_reverse": 8,
        "reversed": 3,
        "escalate_conflict": 6,
        "escalate_over_limit": 3,
    }
    assert all(scenario.facts.amount_kobo <= ESCALATION_LIMIT_KOBO for scenario in CATALOG[:22])
    assert all(case_type(scenario.facts) != "escalate_over_limit" for scenario in CATALOG[:22])
    assert [case_type(BY_SEED[seed].facts) for seed in (23, 24, 25)] == [
        "escalate_over_limit",
        "escalate_over_limit",
        "escalate_over_limit",
    ]
    assert BY_SEED[23].pattern == "credited"
    assert BY_SEED[24].pattern == "failed_unreversed"
    assert BY_SEED[25].pattern == "switch_success_no_credit"


def test_authored_chaos_is_only_on_the_last_five_seeds():
    for seed, scenario in BY_SEED.items():
        if seed < 26:
            assert scenario.chaos == ChaosFlags()
    assert BY_SEED[26].chaos.timeout_ops == ("switch.get_status",)
    assert BY_SEED[27].chaos.connection_error_ops == ("beneficiary.get_credit",)
    assert BY_SEED[28].chaos.lying_reversal is True
    assert BY_SEED[29].chaos.stale_switch_status == "pending"
    assert BY_SEED[30].chaos.timeout_ops == ("sender.get_debit",)


def test_seed_one_is_a_stable_credited_complaint():
    scenario = BY_SEED[1]
    assert scenario.customer_name == "Ada Musa"
    assert scenario.complaint_id == "CMP-0001"
    assert scenario.facts.transfer_id == "TXN-0001"
    assert scenario.facts.sender_account == "2100000001"
    assert scenario.facts.beneficiary_account == "3100000001"
    assert scenario.facts.sender_bank == "Harbor Bank"
    assert scenario.facts.beneficiary_bank == "Cedar Bank"
    assert scenario.complained_at == "2026-10-10T08:00:00+01:00"
    assert scenario.facts.debit_at == "2026-10-10T03:59:00+01:00"
    assert scenario.facts.switch_updated_at == "2026-10-10T03:59:40+01:00"
    assert scenario.facts.credit_at == "2026-10-10T04:00:30+01:00"
    assert scenario.facts.reversed_at is None
    assert scenario.narrative == (
        "I am Ada Musa. I sent NGN 5,000.00 to account 3100000001 at Cedar Bank. "
        "My account was debited but the beneficiary was not credited. Reference TXN-0001."
    )


def test_timestamps_banks_and_accounts_are_ordered_for_every_seed():
    for scenario in CATALOG:
        facts = scenario.facts
        debit_at = datetime.fromisoformat(facts.debit_at)
        switch_at = datetime.fromisoformat(facts.switch_updated_at)
        complained_at = datetime.fromisoformat(scenario.complained_at)
        assert debit_at < switch_at < complained_at
        assert facts.sender_account != facts.beneficiary_account
        assert len(facts.sender_account) == len(facts.beneficiary_account) == 10
        assert facts.sender_bank != facts.beneficiary_bank
        assert facts.currency == "NGN"
        assert type(facts.amount_kobo) is int
        if facts.beneficiary_credited:
            assert facts.credit_at is not None
            assert switch_at < datetime.fromisoformat(facts.credit_at) < complained_at
        else:
            assert facts.credit_at is None
        if facts.reversal_applied:
            assert facts.reversed_at is not None
            assert switch_at < datetime.fromisoformat(facts.reversed_at) < complained_at
        else:
            assert facts.reversed_at is None
        assert facts.transfer_id in scenario.narrative


def test_scenarios_are_frozen():
    with pytest.raises(FrozenInstanceError):
        BY_SEED[1].seed = 2  # type: ignore[misc]


def test_validation_rejects_broken_seeds():
    base = BY_SEED[1]
    rejected = [
        replace(base, pattern="nope"),
        replace(base, narrative=""),
        replace(base, narrative="I sent the money."),
        replace(base, facts=replace(base.facts, amount_kobo=0)),
        replace(base, facts=replace(base.facts, amount_kobo=1.5)),
        replace(base, facts=replace(base.facts, balance_before_kobo=1)),
        replace(base, facts=replace(base.facts, sender_account=base.facts.beneficiary_account)),
        replace(base, facts=replace(base.facts, beneficiary_bank=base.facts.sender_bank)),
        replace(base, facts=replace(base.facts, credit_at=None)),
        replace(base, facts=replace(base.facts, credit_at=base.facts.debit_at)),
        replace(base, facts=replace(base.facts, debit_at="2026-10-10T03:59:00")),
        replace(base, facts=replace(base.facts, debit_at="yesterday")),
        replace(base, facts=replace(base.facts, sender_debited=False)),
        replace(base, chaos=ChaosFlags(timeout_ops=("switch.get_status", "switch.get_status"))),
        replace(base, chaos=ChaosFlags(timeout_ops=("not.an.op",))),
        replace(
            base,
            chaos=ChaosFlags(
                timeout_ops=("switch.get_status",),
                connection_error_ops=("switch.get_status",),
            ),
        ),
        replace(base, chaos=ChaosFlags(stale_switch_status="success")),
        replace(base, chaos=ChaosFlags(stale_switch_status="settled")),
        replace(base, chaos=ChaosFlags(lying_reversal=1)),  # type: ignore[arg-type]
        replace(base, seed=True),  # type: ignore[arg-type]
    ]
    for scenario in rejected:
        with pytest.raises(ValueError):
            validate_scenario(scenario)

    missing_credit = BY_SEED[9]
    with pytest.raises(ValueError, match="credit_at must be empty"):
        validate_scenario(
            replace(missing_credit, facts=replace(missing_credit.facts, credit_at=missing_credit.facts.debit_at))
        )
    reversed_seed = BY_SEED[15]
    with pytest.raises(ValueError, match="reversed_at is out of order"):
        validate_scenario(
            replace(
                reversed_seed,
                facts=replace(reversed_seed.facts, reversed_at=reversed_seed.facts.debit_at),
            )
        )


def test_seeds_file_matches_the_builder_and_roundtrips(tmp_path):
    document = document_from(CATALOG)
    text = json.dumps(document, indent=2) + "\n"
    assert SEEDS_PATH.read_text(encoding="utf-8") == text
    assert b"\r" not in SEEDS_PATH.read_bytes()
    assert load_scenarios() == CATALOG

    destination = write_seeds(tmp_path / "seeds.json")
    again = write_seeds(tmp_path / "seeds-again.json")
    assert destination.read_text(encoding="utf-8") == again.read_text(encoding="utf-8") == text
    assert loads_document(json.loads(text)) == CATALOG

    def walk(value: object) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(document)
    broken = dict(document)
    broken["version"] = 2
    with pytest.raises(ValueError, match="version"):
        loads_document(broken)
    wrong_limit = dict(document)
    wrong_limit["escalation_limit_kobo"] = 1
    with pytest.raises(ValueError, match="escalation limit"):
        loads_document(wrong_limit)
    short = dict(document)
    short["scenarios"] = document["scenarios"][:1]
    with pytest.raises(ValueError, match="expected 30"):
        loads_document(short)
