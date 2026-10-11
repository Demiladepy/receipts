# cfo.ai inputs: measured, not assumed

Every number marked **measured** comes from the run files in `runs/` (90 runs per version on the 30 stress seeds, gpt-4.1-mini at OpenAI list price, $0.40 / $1.60 per 1M tokens). Everything else is marked as an assumption.

## Per case (measured)

| Input | Before ask-once (v3) | After 2 decisions (v3 + rules) | Source |
|---|---|---|---|
| Model cost per case, mean | $0.0047 | **$0.0045** | `runs/v3-stress-x3.jsonl`, `runs/v3-policy-stress-x3.jsonl` |
| Escalated to a human | 66% (59 / 90) | **43% (39 / 90)** | `escalated_to_human` |
| Unnecessary escalations | 14 / 90 | **2 / 90** | `unnecessary_escalations` |
| Proved resolutions (billable) | 31 / 90 | **51 / 90** | billing rule: verifier allowed, no human |
| False claims sent / harmful reversals | 0 / 0 | 0 / 0 | ground-truth audit |
| Tokens per case | ~9,900 in, ~470 out, 5.5 model calls | similar | token usage |

Floor for escalations: about 30% of cases genuinely need a person in this mix (over the limit, a reversal that did not post, a source that never answers). Each ask-once decision moves the rate toward that floor. The next one, large agreed credits (seed 23), is already identified.

## Billing (how the money is collected)

- **Unit:** one proved resolution. A bank pays only when the verifier allowed the reply and no human was needed; escalations are free and listed on the statement, so the bank sees its own human queue.
- **Statement:** `python -m billing statement` lists every billable case with its neatlogs trace id. Example from the 90 policy runs: 51 × NGN 2,000.00 = **NGN 102,000.00**, 39 escalations free (`billing/statements/2026-10-v3-policy-stress-x3.json`).
- **Provider:** Paystack Payment Requests (invoices in NGN). Dodo Payments was the first choice and is integrated, but it could not onboard a Nigerian business. The same "not available in your country" wall is one Nigerian customers hit every day, so the billing layer is provider-independent.
- **Payment fee (assumption from published third-party guides; confirm on paystack.com/pricing):** local card 1.5% + NGN 100, capped at NGN 2,000 per payment. On a monthly invoice of NGN 102,000 that is about NGN 1,630.

## Assumptions to set in the model (label them as assumptions)

- Price per proved resolution: NGN 2,000 (planning figure).
- USD/NGN rate for the model and tooling costs, which are in USD.
- Human reviewer cost per escalated case (minutes × loaded hourly cost).
- Complaints per bank per month, banks onboarded per month, churn.
- Platform cost (hosting, neatlogs plan).

## Paste this into Ari

> I'm planning Receipts, an AI agent that resolves "debited but not credited" bank-transfer complaints for Nigerian banks. It can only send a customer reply when every claim is proved by a trace of the tool call behind it, and it hands the case to a human otherwise.
>
> Measured from 90 test runs: model cost per case is $0.0045. 43% of cases still go to a human after two policy decisions (66% before them), and the floor is about 30%. There were 0 false claims sent and 0 harmful reversals.
>
> Pricing: the bank pays NGN 2,000 per proved resolution (assumption). Escalations are free. Invoices go out monthly through Paystack at 1.5% + NGN 100 per payment, capped at NGN 2,000 (assumption, from published rates).
>
> Please build a monthly model with Base, Downside and Upside scenarios from October 2026 to December 2027, with my assumptions marked: complaints per bank per month, banks added per month, churn, human reviewer cost per escalated case, platform cost, USD/NGN rate.
>
> Questions:
> 1. Which price per proved resolution keeps gross margin above 80% in the Downside, where escalations stay at 66% and the bank's human cost is ours?
> 2. How many months of runway does each 10-point drop in escalation rate buy?
> 3. Is "per proved resolution" or "per complaint received" the better pricing unit for a bank, and why?
