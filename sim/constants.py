"""Fixed simulator bounds. Nothing here is read from the clock or the network."""

from datetime import datetime, timedelta, timezone

LAGOS = timezone(timedelta(hours=1))
COMPLAINED_AT = datetime(2026, 10, 10, 8, 0, tzinfo=LAGOS)

# Amounts are integer kobo. 100 kobo = 1 NGN.
ESCALATION_LIMIT_KOBO = 100_000_000  # 1,000,000.00 NGN
BALANCE_BEFORE_KOBO = 1_000_000_000  # 10,000,000.00 NGN
CURRENCY = "NGN"
SEED_COUNT = 30

READ_OPS = (
    "sender.get_debit",
    "sender.get_balance",
    "switch.get_status",
    "beneficiary.get_credit",
)
OPS = READ_OPS + ("sender.reverse",)

SWITCH_STATUSES = ("pending", "success", "failed")
GROUND_SWITCH_STATUSES = ("success", "failed")
