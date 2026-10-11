# Demo video: 3:00

**Story:** v1 lies, the traces catch it, v3 can't, and a human decides once.
**Setup before recording:**
- Terminal at about 110 columns, with `PYTHONIOENCODING=utf-8` set.
- Browser tabs: the demo site, the neatlogs trace for `cb094350ed08c4d6b183f83622a8e617`, the neatlogs prompt `receipts-agent`, the GitHub commit `255f3df`, the cfo.ai plan, and the Bachs checkout.
- Run every live command once before recording, so you know roughly what it prints.

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
```

---

**0:00 to 0:15. The problem** (demo site, top of the page)
> "Debited but not credited is one of the most common bank complaints in Nigeria. Support says 'done' without proof. Receipts is an agent that can't send a sentence it can't prove from a trace."

**0:15 to 0:45. v1 lies** (terminal)
```powershell
python -m demo case 28 --version v1 --recorded 3
```
> "The reversal tool said 'reversed'. v1 told the customer the debit was reversed. The ledger never posted it, and the switch status it quoted was stale. Both sentences were false."

Cut to **neatlogs**, trace `cb094350…`: the `sender.reverse` span and no ledger read after it.
> "neatlogs shows why: there is no read after the write."

**0:45 to 1:15. How v3 can't lie** (terminal, live)
```powershell
python -m demo case 28 --version v3
```
> "Every claim cites a receipt: the neatlogs span id of the tool call behind it. A deterministic verifier checks three things: the source has authority (an acknowledgement isn't a ledger read), the receipt is fresh (a read before a write has expired), and the sentence doesn't say more than the receipt proves. Here v3 re-reads the stale switch, reverses, re-reads the ledger, sees the money didn't move, escalates, and tells the truth."

Point at the new trace id it prints. That is a fresh hosted trace.

**1:15 to 1:40. What the traces taught us** (terminal)
```powershell
python -m demo numbers
```
> "Same 30 cases, three runs each, graded against hidden ground truth. v2 made the words honest, and the traces showed it got bolder with money: 11 harmful reversals. So v3 gates the action too: no reversal without receipts. 90 out of 90 resolved, 0 false claims, 0 harmful actions, about half a cent a case."

Cut to **neatlogs**, prompt `receipts-agent`: versions 1 to 3, and the `production` label on v3.

**1:40 to 2:20. Ask once** (terminal and GitHub)
> "v3 was safe, but it sent two thirds of cases to a human. The agent escalates once with an evidence pack. I decide in plain words. Headless Claude Code writes the rule and a test and commits it, and Entire records that session."
```powershell
python -m demo rules
git log -3 --format="%h %s%n   %(trailers:key=Entire-Checkpoint)"
```
Show GitHub commit `255f3df`, then:
```powershell
entire graph checkpoint 01M4NJFY1EXVGPZD7C0G08CQXG
```
> "The checkpoint shows exactly what that session changed: a rule and its tests."
```powershell
python -m demo case 22 --version v3p
```
> "The next case like it resolves on its own and cites the rule. Escalations went from 59 to 39, unnecessary ones from 14 to 2, still with 0 false claims. And if a run under a rule ever fails the audit, the rule loses its license until a person restores it."

**2:20 to 2:50. The business** (terminal, Bachs, cfo.ai)
```powershell
python -m demo bill
```
> "A bank pays only for replies we proved: ₦2,000 per resolution. Escalations are free, and every line names its trace. Our first billing partner couldn't onboard a Nigerian business, the same wall our customers hit, so we collect through Bachs, built for African businesses."

Show the Bachs checkout: ₦102,000, statement hash in the metadata. Cut to **cfo.ai**:
> "Ari's plan uses measured cost, not guesses: half a cent of model cost per case. The lever is the escalation rate, and each decision we ask once moves it."

**2:50 to 3:00. Close** (demo site)
> "Receipts. It doesn't say done until it can prove it."

---

**If something goes wrong live:** every live command has a recorded fallback. Use `python -m demo case <seed> --version v3 --recorded 1`. The page at https://receipts-tau-liard.vercel.app/#cases shows the same runs.
