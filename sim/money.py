"""Kobo amounts stay integers. This only formats them for complaint text."""


def format_naira(amount_kobo: int) -> str:
    if not isinstance(amount_kobo, int) or isinstance(amount_kobo, bool):
        raise TypeError("amount_kobo must be an int")
    if amount_kobo < 0:
        raise ValueError("amount_kobo must be >= 0")
    naira, rem = divmod(amount_kobo, 100)
    return f"NGN {naira:,}.{rem:02d}"
