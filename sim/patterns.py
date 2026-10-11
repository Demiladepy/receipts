"""Ground-truth shapes for a debited-but-not-credited complaint.

Chaos is not a pattern. It only changes what a later read is allowed to observe.
"""

PATTERNS: dict[str, dict[str, object]] = {
    "credited": {
        "sender_debited": True,
        "switch_status": "success",
        "beneficiary_credited": True,
        "reversal_applied": False,
    },
    "failed_unreversed": {
        "sender_debited": True,
        "switch_status": "failed",
        "beneficiary_credited": False,
        "reversal_applied": False,
    },
    "failed_reversed": {
        "sender_debited": True,
        "switch_status": "failed",
        "beneficiary_credited": False,
        "reversal_applied": True,
    },
    "switch_success_no_credit": {
        "sender_debited": True,
        "switch_status": "success",
        "beneficiary_credited": False,
        "reversal_applied": False,
    },
    "switch_failed_but_credited": {
        "sender_debited": True,
        "switch_status": "failed",
        "beneficiary_credited": True,
        "reversal_applied": False,
    },
}


def pattern_facts(pattern: str) -> dict[str, object]:
    try:
        return dict(PATTERNS[pattern])
    except KeyError as exc:
        raise ValueError(f"unknown pattern {pattern}") from exc
