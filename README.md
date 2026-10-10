# Receipts

**It doesn't say done until it can prove it.**

Receipts resolves "debited but not credited" complaints end to end, and is not allowed to tell the customer anything it cannot prove from a trace span.

## The four rules

1. **Every claim needs a receipt.** Each factual claim in an outgoing reply points to the tool span that proves it. A deterministic verifier blocks the send otherwise.
2. **Receipts expire.** A claim about a balance or status is only valid if its read happened after the last action that could have changed it.
3. **Sources disagree, the agent decides who to trust.** Sender bank, switch and beneficiary bank are queried separately; conflicts are resolved on the record.
4. **Ask once, then it is policy.** A new case type escalates to a human; the decision becomes a committed policy rule plus test.

## Layout

| Dir | What |
|---|---|
| `sim/` | Simulated sender ledger, switch, beneficiary bank, chaos layer |
| `agent/` | Core loop, tools, prompts |
| `verifier/` | Claim schema, span match, freshness check |
| `policy/` | Committed rules + tests (written by the ask-once loop) |
| `scenarios/` | 30 seeded complaint scenarios |
| `evidence/` | Screenshots, numbers |
| `hackathon.md` | Build log, failure taxonomy, evidence links |

## Setup

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env   # fill in keys
```

Built for #neatHack with Claude Code, Entire, neatlogs and cfo.ai.
