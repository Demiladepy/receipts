"""Sender ledger. Authoritative for the debit, the reversal, and the balance."""

from sim.errors import SimNotFound
from sim.models import TransferFacts


class SenderLedger:
    def __init__(self, facts: TransferFacts):
        self._facts = facts
        self.reversal_applied = facts.reversal_applied
        self.reversed_at = facts.reversed_at

    def balance_kobo(self) -> int:
        balance = self._facts.balance_before_kobo
        if self._facts.sender_debited and not self.reversal_applied:
            balance -= self._facts.amount_kobo
        return balance

    def get_debit(self, transfer_id: str, read_at: str) -> dict:
        self._require(transfer_id, "sender.get_debit")
        return {
            "transfer_id": transfer_id,
            "account": self._facts.sender_account,
            "bank": self._facts.sender_bank,
            "amount_kobo": self._facts.amount_kobo,
            "currency": self._facts.currency,
            "debited": self._facts.sender_debited,
            "debit_at": self._facts.debit_at,
            "reversal_applied": self.reversal_applied,
            "reversed_at": self.reversed_at,
            "read_at": read_at,
        }

    def get_balance(self, account: str, read_at: str) -> dict:
        if account != self._facts.sender_account:
            raise SimNotFound("sender.get_balance", account)
        return {
            "account": account,
            "bank": self._facts.sender_bank,
            "currency": self._facts.currency,
            "balance_kobo": self.balance_kobo(),
            "read_at": read_at,
        }

    def reverse(self, transfer_id: str, read_at: str, *, apply: bool) -> dict:
        self._require(transfer_id, "sender.reverse")
        if not self._facts.sender_debited:
            return {
                "transfer_id": transfer_id,
                "status": "rejected",
                "reason": "not_debited",
                "read_at": read_at,
            }
        if self.reversal_applied:
            return {
                "transfer_id": transfer_id,
                "status": "reversed",
                "already_applied": True,
                "reversed_at": self.reversed_at,
                "read_at": read_at,
            }
        if apply:
            self.reversal_applied = True
            self.reversed_at = read_at
        return {
            "transfer_id": transfer_id,
            "status": "reversed",
            "already_applied": False,
            "reversed_at": read_at,
            "read_at": read_at,
        }

    def _require(self, transfer_id: str, op: str) -> None:
        if transfer_id != self._facts.transfer_id:
            raise SimNotFound(op, transfer_id)
