"""Fixtures shared by the simulator tests."""

from sim.catalog import build_catalog
from sim.models import TransferFacts

CATALOG = build_catalog()
BY_SEED = {scenario.seed: scenario for scenario in CATALOG}


def facts(**overrides: object) -> TransferFacts:
    base = dict(
        transfer_id="TXN-TEST",
        sender_account="2100000099",
        sender_bank="Harbor Bank",
        beneficiary_account="3100000099",
        beneficiary_bank="Cedar Bank",
        amount_kobo=500_000,
        currency="NGN",
        balance_before_kobo=1_000_000_000,
        sender_debited=True,
        debit_at="2026-10-10T04:00:00+01:00",
        switch_status="success",
        switch_updated_at="2026-10-10T04:00:40+01:00",
        beneficiary_credited=True,
        credit_at="2026-10-10T04:01:30+01:00",
        reversal_applied=False,
        reversed_at=None,
    )
    base.update(overrides)
    return TransferFacts(**base)  # type: ignore[arg-type]
