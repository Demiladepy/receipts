"""Switch. Authoritative for whether the transfer instruction succeeded."""

from sim.errors import SimNotFound
from sim.models import TransferFacts


class Switch:
    def __init__(self, facts: TransferFacts):
        self._facts = facts

    def get_status(
        self,
        transfer_id: str,
        read_at: str,
        *,
        status: str | None = None,
        updated_at: str | None = None,
    ) -> dict:
        if transfer_id != self._facts.transfer_id:
            raise SimNotFound("switch.get_status", transfer_id)
        return {
            "transfer_id": transfer_id,
            "status": self._facts.switch_status if status is None else status,
            "amount_kobo": self._facts.amount_kobo,
            "currency": self._facts.currency,
            "updated_at": self._facts.switch_updated_at if updated_at is None else updated_at,
            "read_at": read_at,
        }
