"""Case type derived from ground truth, never from a chaotic read."""

from sim.constants import ESCALATION_LIMIT_KOBO
from sim.models import TransferFacts


def sources_conflict(facts: TransferFacts) -> bool:
    if facts.switch_status == "pending":
        return True
    if (facts.switch_status == "success") != facts.beneficiary_credited:
        return True
    if facts.beneficiary_credited and not facts.sender_debited:
        return True
    if facts.switch_status == "success" and not facts.sender_debited:
        return True
    return False


def case_type(facts: TransferFacts) -> str:
    """Resolution class for the true ledger state.

    An amount strictly above the escalation limit wins over every other class.
    """
    if facts.amount_kobo > ESCALATION_LIMIT_KOBO:
        return "escalate_over_limit"
    if sources_conflict(facts):
        return "escalate_conflict"
    if (
        facts.sender_debited
        and facts.switch_status == "success"
        and facts.beneficiary_credited
        and not facts.reversal_applied
    ):
        return "credited"
    if facts.reversal_applied and facts.sender_debited and not facts.beneficiary_credited:
        return "reversed"
    if facts.sender_debited and not facts.beneficiary_credited and not facts.reversal_applied:
        return "failed_reverse"
    if not facts.sender_debited and not facts.beneficiary_credited:
        return "no_debit"
    raise ValueError(f"unclassified facts for {facts.transfer_id}")
