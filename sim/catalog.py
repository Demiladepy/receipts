"""The 30 complaint seeds. Python is the source; scenarios/seeds.json mirrors it."""

import json
from datetime import timedelta
from pathlib import Path
from typing import cast

from sim.clock import isoformat
from sim.constants import (
    BALANCE_BEFORE_KOBO,
    COMPLAINED_AT,
    CURRENCY,
    ESCALATION_LIMIT_KOBO,
    SEED_COUNT,
)
from sim.models import ChaosFlags, Scenario, SwitchStatus, TransferFacts
from sim.money import format_naira
from sim.patterns import pattern_facts
from sim.validate import validate_scenario

ROOT = Path(__file__).resolve().parents[1]
SEEDS_PATH = ROOT / "scenarios" / "seeds.json"
DOCUMENT_VERSION = 1

FIRST = ("Ada", "Chinedu", "Fatima", "Ibrahim", "Ngozi", "Tunde", "Amina", "Emeka", "Zainab", "Kunle")
LAST = ("Okafor", "Balogun", "Adeyemi", "Musa", "Eze", "Lawal", "Okeke", "Bello", "Nwosu", "Yusuf")
BANKS = ("Harbor Bank", "Cedar Bank", "Lumen MFB", "Northline Bank", "Kite Bank", "Orchard MFB")

# seed, pattern, amount in whole naira, chaos flags
SCENARIO_ROWS: tuple[tuple[int, str, int, ChaosFlags], ...] = (
    (1, "credited", 5_000, ChaosFlags()),
    (2, "credited", 15_000, ChaosFlags()),
    (3, "credited", 2_500, ChaosFlags()),
    (4, "credited", 80_000, ChaosFlags()),
    (5, "credited", 120_000, ChaosFlags()),
    (6, "credited", 750, ChaosFlags()),
    (7, "credited", 45_000, ChaosFlags()),
    (8, "credited", 250_000, ChaosFlags()),
    (9, "failed_unreversed", 5_000, ChaosFlags()),
    (10, "failed_unreversed", 20_000, ChaosFlags()),
    (11, "failed_unreversed", 100_000, ChaosFlags()),
    (12, "failed_unreversed", 3_500, ChaosFlags()),
    (13, "failed_unreversed", 60_000, ChaosFlags()),
    (14, "failed_unreversed", 900_000, ChaosFlags()),
    (15, "failed_reversed", 5_000, ChaosFlags()),
    (16, "failed_reversed", 18_000, ChaosFlags()),
    (17, "failed_reversed", 250_000, ChaosFlags()),
    (18, "switch_success_no_credit", 15_000, ChaosFlags()),
    (19, "switch_success_no_credit", 75_000, ChaosFlags()),
    (20, "switch_success_no_credit", 400_000, ChaosFlags()),
    (21, "switch_failed_but_credited", 22_000, ChaosFlags()),
    (22, "switch_failed_but_credited", 64_000, ChaosFlags()),
    (23, "credited", 1_500_000, ChaosFlags()),
    (24, "failed_unreversed", 2_000_000, ChaosFlags()),
    (25, "switch_success_no_credit", 5_000_000, ChaosFlags()),
    (26, "credited", 9_000, ChaosFlags(timeout_ops=("switch.get_status",))),
    (27, "failed_unreversed", 11_000, ChaosFlags(connection_error_ops=("beneficiary.get_credit",))),
    (28, "failed_unreversed", 30_000, ChaosFlags(lying_reversal=True)),
    (29, "switch_success_no_credit", 45_000, ChaosFlags(stale_switch_status="pending")),
    (30, "credited", 7_000, ChaosFlags(timeout_ops=("sender.get_debit",))),
)


def _customer_name(seed: int) -> str:
    return f"{FIRST[(seed - 1) % len(FIRST)]} {LAST[(seed * 3) % len(LAST)]}"


def _narrative(name: str, amount_kobo: int, account: str, bank: str, transfer_id: str) -> str:
    return (
        f"I am {name}. I sent {format_naira(amount_kobo)} to account {account} at {bank}. "
        f"My account was debited but the beneficiary was not credited. Reference {transfer_id}."
    )


def _build_one(seed: int, pattern: str, amount_naira: int, chaos: ChaosFlags) -> Scenario:
    shaped = pattern_facts(pattern)
    amount_kobo = amount_naira * 100
    transfer_id = f"TXN-{seed:04d}"
    sender_account = f"{2100000000 + seed:010d}"
    beneficiary_account = f"{3100000000 + seed:010d}"
    sender_bank = BANKS[(seed - 1) % len(BANKS)]
    beneficiary_bank = BANKS[seed % len(BANKS)]
    debit_at = COMPLAINED_AT - timedelta(hours=4, minutes=seed)
    switch_at = debit_at + timedelta(seconds=40)
    credited = bool(shaped["beneficiary_credited"])
    reversed_ = bool(shaped["reversal_applied"])
    credit_at = switch_at + timedelta(seconds=50) if credited else None
    reversed_at = switch_at + timedelta(minutes=2) if reversed_ else None
    name = _customer_name(seed)
    facts = TransferFacts(
        transfer_id=transfer_id,
        sender_account=sender_account,
        sender_bank=sender_bank,
        beneficiary_account=beneficiary_account,
        beneficiary_bank=beneficiary_bank,
        amount_kobo=amount_kobo,
        currency=CURRENCY,
        balance_before_kobo=BALANCE_BEFORE_KOBO,
        sender_debited=bool(shaped["sender_debited"]),
        debit_at=isoformat(debit_at),
        switch_status=cast(SwitchStatus, shaped["switch_status"]),
        switch_updated_at=isoformat(switch_at),
        beneficiary_credited=credited,
        credit_at=isoformat(credit_at) if credit_at else None,
        reversal_applied=reversed_,
        reversed_at=isoformat(reversed_at) if reversed_at else None,
    )
    return Scenario(
        seed=seed,
        pattern=pattern,
        complaint_id=f"CMP-{seed:04d}",
        customer_name=name,
        narrative=_narrative(name, amount_kobo, beneficiary_account, beneficiary_bank, transfer_id),
        complained_at=isoformat(COMPLAINED_AT),
        facts=facts,
        chaos=chaos,
    )


def build_catalog() -> tuple[Scenario, ...]:
    seeds = [row[0] for row in SCENARIO_ROWS]
    if seeds != list(range(1, SEED_COUNT + 1)):
        raise ValueError("seeds must be 1..30 in order")
    scenarios = tuple(_build_one(*row) for row in SCENARIO_ROWS)
    for scenario in scenarios:
        validate_scenario(scenario)
    return scenarios


def _chaos_to_dict(chaos: ChaosFlags) -> dict:
    return {
        "timeout_ops": list(chaos.timeout_ops),
        "connection_error_ops": list(chaos.connection_error_ops),
        "stale_switch_status": chaos.stale_switch_status,
        "lying_reversal": chaos.lying_reversal,
    }


def _facts_to_dict(facts: TransferFacts) -> dict:
    return {
        "transfer_id": facts.transfer_id,
        "sender_account": facts.sender_account,
        "sender_bank": facts.sender_bank,
        "beneficiary_account": facts.beneficiary_account,
        "beneficiary_bank": facts.beneficiary_bank,
        "amount_kobo": facts.amount_kobo,
        "currency": facts.currency,
        "balance_before_kobo": facts.balance_before_kobo,
        "sender_debited": facts.sender_debited,
        "debit_at": facts.debit_at,
        "switch_status": facts.switch_status,
        "switch_updated_at": facts.switch_updated_at,
        "beneficiary_credited": facts.beneficiary_credited,
        "credit_at": facts.credit_at,
        "reversal_applied": facts.reversal_applied,
        "reversed_at": facts.reversed_at,
    }


def scenario_to_dict(scenario: Scenario) -> dict:
    return {
        "seed": scenario.seed,
        "pattern": scenario.pattern,
        "complaint_id": scenario.complaint_id,
        "customer_name": scenario.customer_name,
        "narrative": scenario.narrative,
        "complained_at": scenario.complained_at,
        "facts": _facts_to_dict(scenario.facts),
        "chaos": _chaos_to_dict(scenario.chaos),
    }


def document_from(scenarios: tuple[Scenario, ...]) -> dict:
    return {
        "version": DOCUMENT_VERSION,
        "escalation_limit_kobo": ESCALATION_LIMIT_KOBO,
        "complained_at": isoformat(COMPLAINED_AT),
        "scenarios": [scenario_to_dict(scenario) for scenario in scenarios],
    }


def _chaos_from_dict(raw: dict) -> ChaosFlags:
    return ChaosFlags(
        timeout_ops=tuple(raw["timeout_ops"]),
        connection_error_ops=tuple(raw["connection_error_ops"]),
        stale_switch_status=raw["stale_switch_status"],
        lying_reversal=raw["lying_reversal"],
    )


def _facts_from_dict(raw: dict) -> TransferFacts:
    return TransferFacts(
        transfer_id=raw["transfer_id"],
        sender_account=raw["sender_account"],
        sender_bank=raw["sender_bank"],
        beneficiary_account=raw["beneficiary_account"],
        beneficiary_bank=raw["beneficiary_bank"],
        amount_kobo=raw["amount_kobo"],
        currency=raw["currency"],
        balance_before_kobo=raw["balance_before_kobo"],
        sender_debited=raw["sender_debited"],
        debit_at=raw["debit_at"],
        switch_status=raw["switch_status"],
        switch_updated_at=raw["switch_updated_at"],
        beneficiary_credited=raw["beneficiary_credited"],
        credit_at=raw["credit_at"],
        reversal_applied=raw["reversal_applied"],
        reversed_at=raw["reversed_at"],
    )


def scenario_from_dict(raw: dict) -> Scenario:
    return Scenario(
        seed=raw["seed"],
        pattern=raw["pattern"],
        complaint_id=raw["complaint_id"],
        customer_name=raw["customer_name"],
        narrative=raw["narrative"],
        complained_at=raw["complained_at"],
        facts=_facts_from_dict(raw["facts"]),
        chaos=_chaos_from_dict(raw["chaos"]),
    )


def loads_document(raw: dict) -> tuple[Scenario, ...]:
    if raw.get("version") != DOCUMENT_VERSION:
        raise ValueError(f"unsupported seeds document version {raw.get('version')}")
    if raw.get("escalation_limit_kobo") != ESCALATION_LIMIT_KOBO:
        raise ValueError("seeds document escalation limit does not match the simulator")
    scenarios = tuple(scenario_from_dict(item) for item in raw["scenarios"])
    if len(scenarios) != SEED_COUNT:
        raise ValueError(f"expected {SEED_COUNT} scenarios")
    if [scenario.seed for scenario in scenarios] != list(range(1, SEED_COUNT + 1)):
        raise ValueError("seeds must be 1..30 in order")
    for scenario in scenarios:
        validate_scenario(scenario)
    return scenarios


def write_seeds(path: Path | None = None) -> Path:
    target = path or SEEDS_PATH
    text = json.dumps(document_from(build_catalog()), indent=2) + "\n"
    target.write_text(text, encoding="utf-8", newline="\n")
    return target


def load_scenarios(path: Path | None = None) -> tuple[Scenario, ...]:
    target = path or SEEDS_PATH
    return loads_document(json.loads(target.read_text(encoding="utf-8")))
