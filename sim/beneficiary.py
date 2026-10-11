"""Beneficiary bank. Authoritative for whether the credit posted."""

from sim.errors import SimNotFound
from sim.models import TransferFacts


class BeneficiaryBank:
    def __init__(self, facts: TransferFacts):
        self._facts = facts

    def get_credit(self, transfer_id: str, read_at: str) -> dict:
        if transfer_id != self._facts.transfer_id:
            raise SimNotFound("beneficiary.get_credit", transfer_id)
        credited = self._facts.beneficiary_credited
        return {
            "transfer_id": transfer_id,
            "account": self._facts.beneficiary_account,
            "bank": self._facts.beneficiary_bank,
            "credited": credited,
            "amount_kobo": self._facts.amount_kobo if credited else None,
            "currency": self._facts.currency,
            "credit_at": self._facts.credit_at if credited else None,
            "read_at": read_at,
        }
