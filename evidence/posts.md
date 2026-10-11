# #neatHack posts

Drafts. Numbers are from `runs/*-stress-x3.jsonl` (30 seeds × 3 runs per version, gpt-4.1-mini). Attach real screenshots: the neatlogs trace view, and the demo page at https://receipts-tau-liard.vercel.app/#cases (seed 28, run 2, v1 vs v3).

## Post 2: "My agent lied" (thread)

**1/**
Day 2 of #neatHack. My agent lied to a customer.

₦30,000 debited, never credited. The agent called the reversal tool, got back "reversed", and wrote: "We have reversed the debit on your account."

The ledger never posted it. The @neatlogs trace shows why: no read after the write.

[screenshot: neatlogs trace, seed 28 v1, `b2074a54abad39f688ce970efccba7b4`]

**2/**
So Receipts now can't send a sentence it can't prove.

Every claim cites a receipt: the neatlogs span id of the tool call behind it. A deterministic verifier checks:
• the source has authority (an acknowledgement isn't a ledger read)
• the receipt is fresh (a read before a write has expired)
• the sentence doesn't say more than the receipt does

**3/**
Then the traces caught something worse.

With honest replies, v2 got bolder with money. It reversed 15 transfers it shouldn't have, some already credited. That pays the customer twice.

The verifier gated words, not actions.

**4/**
v3 gates the action too: no reversal without receipts for debit open, switch failed, beneficiary not credited, under the limit.

Same 30 seeds, 3 runs each, graded against hidden ground truth:
resolved correctly 58 → 72 → 90/90
false claims sent 30 → 0 → 0
harmful reversals 3 → 15 → 0
$0.0047 per case

**5/**
Every fix commit cites the trace that triggered it, and @EntireHQ checkpoints the session behind it. @arithecfo gets the real cost per case next.

Try a case: https://receipts-tau-liard.vercel.app
Code: https://github.com/Demiladepy/receipts

## Post 3: ask once (after the policy commit lands)

A ₦22,000 transfer. The switch says failed. The beneficiary bank says credited.

My agent doesn't guess. It escalates once with the receipts. I decided: trust the beneficiary bank on whether the credit posted.

Claude Code turned that sentence into a rule + test + commit (@EntireHQ checkpoint). The next case like it resolved itself and cited the rule. #neatHack

## Replies worth making

- Reply to @neatlogs's "what are you building?" post: "Receipts: resolves 'debited but not credited' complaints and can't send a sentence it can't prove from a trace span. v1 → v3: false claims sent 30 → 0, harmful reversals 15 → 0 over 90 runs."
- @devsdv_ offered free First User runs on project URLs: reply with the demo link.
