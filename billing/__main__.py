"""Dodo Payments setup and billing for Receipts (test mode by default).

    python -m billing setup                      # meters, product, test customer + subscription link
    python -m billing preview runs/v3-stress-x3.jsonl
    python -m billing send runs/v3-stress-x3.jsonl
"""

import argparse
import json
import os
from pathlib import Path

from billing.dodo import (CONFIG_PATH, ESCALATION_EVENT, RESOLUTION_EVENT, bill, billable_event,
                          client, load_config)

PRICE_CENTS = int(os.environ.get("RECEIPTS_PRICE_PER_RESOLUTION_CENTS", "200"))


def _find(pages, **match):
    for item in pages:
        if all(getattr(item, k, None) == v for k, v in match.items()):
            return item
    return None


def setup() -> dict:
    dodo = client()
    meters = {}
    for event, name, unit, desc in (
        (RESOLUTION_EVENT, "Proved resolutions", "resolution",
         "A complaint resolved with every claim proved by a receipt, no human needed."),
        (ESCALATION_EVENT, "Human escalations", "case",
         "A complaint handed to a human with its evidence pack. Metered, not billed."),
    ):
        existing = _find(dodo.meters.list(), event_name=event)
        meter = existing or dodo.meters.create(
            name=name, event_name=event, measurement_unit=unit, description=desc,
            aggregation={"type": "count"},
        )
        meters[event] = meter.meter_id if hasattr(meter, "meter_id") else meter.id
        print(f"meter {event}: {meters[event]}{' (existing)' if existing else ''}")

    product = dodo.products.create(
        name="Receipts: proved resolutions",
        description="Debited-but-not-credited complaints resolved with a receipt for every claim. "
                    "You pay only for replies the verifier proved; escalations are free.",
        tax_category="saas",
        price={
            "type": "usage_based_price",
            "currency": "USD",
            "fixed_price": 0,
            "payment_frequency_count": 1,
            "payment_frequency_interval": "Month",
            "subscription_period_count": 1,
            "subscription_period_interval": "Year",
            "meters": [{"meter_id": meters[RESOLUTION_EVENT], "price_per_unit": str(PRICE_CENTS)}],
        },
    )
    product_id = product.product_id
    print(f"product: {product_id} at {PRICE_CENTS} cents per proved resolution")

    email = "disputes@harborbank.test"
    customer = _find(dodo.customers.list(email=email), email=email) or dodo.customers.create(
        email=email, name="Harbor Bank (test customer)")
    print(f"customer: {customer.customer_id}")

    config = {"environment": os.environ.get("DODO_PAYMENTS_ENVIRONMENT", "test_mode"),
              "meters": meters, "product_id": product_id, "customer_id": customer.customer_id,
              "price_per_resolution_cents": PRICE_CENTS}
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CONFIG_PATH.name} (ids only, no secrets)")
    return config


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def preview(paths: list[Path]) -> None:
    price = PRICE_CENTS / 100
    for path in paths:
        records = _load(path)
        counts: dict[str, int] = {}
        for r in records:
            name = billable_event(r) or "not billed"
            counts[name] = counts.get(name, 0) + 1
        resolved = counts.get(RESOLUTION_EVENT, 0)
        model_cost = sum(r.get("usage", {}).get("cost_usd", 0) for r in records)
        revenue = resolved * price
        print(f"{path.stem}: {len(records)} cases | billed {resolved} x ${price:.2f} = ${revenue:.2f} | "
              f"escalated {counts.get(ESCALATION_EVENT, 0)} (free) | not billed {counts.get('not billed', 0)} | "
              f"model cost ${model_cost:.2f} | gross margin "
              f"{(1 - model_cost / revenue) * 100 if revenue else 0:.1f}% before human cost")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    p = sub.add_parser("preview")
    p.add_argument("paths", nargs="+", type=Path)
    s = sub.add_parser("send")
    s.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.cmd == "setup":
        setup()
    elif args.cmd == "preview":
        preview(args.paths)
    else:
        counts = bill(_load(args.path))
        print(f"sent to Dodo Payments ({load_config()['environment']}): {counts}")


if __name__ == "__main__":
    main()
