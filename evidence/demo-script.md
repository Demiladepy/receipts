# Demo video: 3:00, browser only

**Story:** v1 lies, the traces catch it, v3 can't, and a human decides once.

Open these tabs before you record, in this order:

1. **Demo site:** https://receipts-tau-liard.vercel.app
2. **neatlogs trace of v1's lie:** in app.neatlogs.com, open your project, go to Traces, and search for `cb094350ed08c4d6b183f83622a8e617`
3. **neatlogs prompts:** in the same app, open Prompts, then `receipts-agent` (versions 1 to 3; the `production` label is on version 3)
4. **GitHub commit written by Claude Code:** https://github.com/Demiladepy/receipts/commit/255f3df
5. **Bachs checkout:** https://sandbox-checkout.bachs.io/c/40xe4PEO4F8sZa8
6. **cfo.ai:** your Receipts plan, after Ari has built it (see `evidence/cfo-inputs.md`)

---

**0:00 to 0:15. The problem** (tab 1, top of the page)
> "Debited but not credited is one of the most common bank complaints in Nigeria. Support says 'done' without proof. Receipts is an agent that can't send a sentence it can't prove from a trace."

**0:15 to 0:45. v1 lies** (tab 1, "Open a case": seed **28**, run **3**, **v1 vs v3**)
Point at the left card (v1): the red boxes and the sentence "We have reversed the debit…".
> "The reversal tool said 'reversed'. v1 told the customer the debit was reversed. It never posted, and the hidden truth catches both false sentences."

Switch to tab 2 (neatlogs trace): the `sender.reverse` step, and no ledger read after it.
> "neatlogs shows why: there is no read after the write."

**0:45 to 1:15. v3 can't lie** (tab 1, right card)
> "In v3 every sentence cites a receipt: the neatlogs span id of the tool call that proves it. A verifier checks the source, that the proof isn't stale, and that the sentence doesn't overclaim. v3 re-reads the ledger, sees the money didn't move, escalates, and tells the truth."

Point at the green dots next to each claim and the receipt ids.

**1:15 to 1:40. What the traces taught us** (tab 1, scroll to "Numbers")
> "Same 30 cases, three runs each, graded against hidden truth. v2 made the words honest, and the traces showed it got bolder with money: 11 harmful reversals. So v3 gates the action too. 90 of 90 resolved, 0 false claims, 0 harmful actions."

Switch to tab 3 (neatlogs prompts): versions 1 to 3, with production on v3.

**1:40 to 2:20. Ask once** (tab 1, scroll to "Ask once", then tab 4)
> "v3 was safe, but it sent two thirds of cases to a human. The agent escalates once with its evidence. I decided in plain words. Claude Code wrote the rule and a test and committed it, and Entire recorded that session."

Tab 4: point at the `Entire-Checkpoint` line in the commit message.
Back on tab 1: "Open a case", seed **22**, compare **v3 vs v3 + rules**.
> "The next case like it resolves on its own and cites my rule. Escalations went from 59 to 39, with still 0 false claims."

**2:20 to 2:50. The business** (tab 5, then tab 6)
> "A bank pays only for replies we proved: ₦2,000 each, and escalations are free. Our first billing partner couldn't onboard a Nigerian business, the same wall our customers hit, so we collect through Bachs, built for African businesses. Here's the checkout: 51 proved resolutions, ₦102,000."

Tab 6:
> "Ari built the plan from measured cost: half a cent per case. The lever is how many cases still need a human."

**2:50 to 3:00. Close** (tab 1, top)
> "Receipts. It doesn't say done until it can prove it."

---

Optional: if you want a live run on camera, `python -m demo case 28 --version v3` runs one in the terminal and prints a fresh trace id.
