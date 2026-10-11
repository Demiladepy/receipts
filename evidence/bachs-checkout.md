# Bachs sandbox checkout (live)

Created Sun 11 Oct 2026 with `python -m billing invoice billing/statements/2026-10-v3-policy-stress-x3.json --provider bachs`, then read back from the Bachs sandbox API.

| Field | Value |
|---|---|
| Checkout | `chk_nQSV66qKn8wfglUE` (status `open`, payment `requires_payment_method`) |
| Checkout URL | https://sandbox-checkout.bachs.io/c/40xe4PEO4F8sZa8 |
| Product | `prod_95d01043db9a42e88b53`, "Receipts: proved resolution", NGN 2,000.00 per unit |
| Line item | 51 × NGN 2,000.00 = **NGN 102,000.00** |
| Reference | `receipts-2026-10-1a8d7c46e04c` |
| `statement_sha256` (in checkout and charge metadata) | `1a8d7c46e04cf0dc8817be05840988b47eb12f8a13e45f571a5b412ca0167225` |

The statement it charges for is `billing/statements/2026-10-v3-policy-stress-x3.json`: 51 proved resolutions from the 90 v3 + rules runs, each with its neatlogs trace id; 39 escalations listed and not charged. `billing.bachs.statement_digest()` recomputes the SHA-256 from that file, so the bank can check the checkout matches the statement line for line.

Sandbox only: the customer is a disposable mailinator.com address for the simulated Harbor Bank.
