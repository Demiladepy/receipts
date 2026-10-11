# Receipts — #neatHack build log

Window opened: Sat 10 Oct 2026. All commits in this repo are dated inside the hackathon window.

Published sources checked Sat 10 Oct 2026, 19:53 WAT: [neatHack](https://neatlogs.com/hackathon) and [Luma](https://luma.com/s5blr882). Luma registration is closed. This log does not add rules that those pages do not state.

## Project

Receipts resolves a "debited but not credited" complaint from simulated bank records, and it is not allowed to tell the customer anything it cannot prove from a trace span.

The problem is a support reply that says the case is done when the ledger does not show it.

## Team

Pending. No team name or public handle has been chosen in this repo. The GitHub remote is `Demiladepy/receipts`.

## Stack

In the repo today:

- Python simulator: sender ledger, switch, beneficiary bank, 30 fixed seeds in `scenarios/seeds.json`
- Naive v1 agent in `agent/`: fixed policy, tool spans through neatlogs, prompt text tagged `v1`
- neatlogs 1.4.26. Tests keep export off and read spans from a local in-memory exporter
- Entire CLI 0.11.4, enabled for Claude Code only. Cursor is not enabled. This machine is not logged in to Entire

Demo: https://receipts-tau-liard.vercel.app

Not used yet: a live neatlogs project, an exported trace.

cfo.ai is connected for the Nithub workspace. The Receipts plan page holds the pricing, cost, revenue, and cash model. Link: https://app.cfo.ai/s/p_AQHSpgYkMmI4ZTE2YjMtM2UwNi00NTk4LTkwNWEtNjhlY2QwOWNlYWFjDWRlZmF1bHRfbGF5ZXI

Crustdata is a published participant credit (5,000 credits), not one of the three required tools. A key is stored only in the gitignored `.env`. Receipts does not call the Crustdata API.

## Build log

### Sat 10 Oct 2026, morning — scaffold (completed)

Claude Code created the repo layout, `agent/tracing.py`, Entire hooks for Claude Code, and commit `b08963c` on `main`. That commit is on `origin` (`https://github.com/Demiladepy/receipts.git`).

### Sat 10 Oct 2026, evening — simulator and v1 agent (completed locally, not committed)

- W1: 30 seeded complaints. Each seed replays. Chaos can be forced off per run.
- v1 agent: reads debit, balance, switch, and beneficiary credit; trusts those payloads; does not read the ledger again after a reversal.
- Seed 28 is the false "processed" case: the reversal span succeeds, the reply says the reversal was processed, and the debit is still open.
- Seeds 26, 27, and 30 name the failed tool instead of inventing the missing fact.
- Tests that ran: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` then `python -m pytest`. Result on this machine: 56 passed in 2.56s (Sat 10 Oct 2026, about 19:34 WAT). An earlier run in this session also passed 56 tests.
- Reproduce: `python -m pytest` with plugin autoload off, and `python -m agent` for one line per seed.

This work is still uncommitted. `git status` shows it as local modifications on `main`. No Entire checkpoint exists for it.

### Sat 10 Oct 2026, 19:53 WAT — Entire remote (not completed)

CLI install was not repeated. `entire --version` is already 0.11.4.

`entire auth status` says not logged in. `entire repo remote add entire /et/receipts/receipts` failed with "not logged in". `origin` was left on GitHub. `entire repo remote add origin --override` was not run, because `--override` repoints an existing remote and the replaced GitHub URL would only be printed once.

### Sat 10 Oct 2026, evening — verifier and demo (completed locally, deployed, not committed)

- A reply is sent only when each claim matches a span. A reversal report is not a ledger read. A debit or balance claim has to be read after `sender.reverse`.
- v1 on the 30 seeds: 7 replies blocked (seeds 9–14 and 28). The other 23 are allowed, including timeouts, the connection error, and the stale pending switch.
- v2 re-reads the debit after a reversal. Seeds 9–14 then have a ledger receipt and are allowed. Seed 28 is allowed only as "the debit is still open." All 30 v2 replies are allowed.
- Tests that ran after this: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` then `python -m pytest`. Latest result: 67 passed in 1.97s.
- Demo page: complaint, v1 reply, v2 reply, and the receipt verdict. FastAPI in `index.py`. Static page in `public/index.html`.
- The landing page links the cfo.ai plan: $2 per proved reply as an assumption, inference at $0, and the Main, Downside, and Upside cash results read back from the model.
- Production: https://receipts-tau-liard.vercel.app — checked `/` (200) and `/api/cases/28` (v1 blocked, v2 allowed, debit still open).
- `.env` is gitignored and listed in `.vercelignore`. It was not part of the deploy.

### Planned, not done

- neatlogs export of a real 30-seed run, then detections
- Entire login, Cursor agent hook, and a checkpoint on the commit that contains this code
- cfo.ai model for pricing, cost, revenue, and runway. Page: https://app.cfo.ai/s/p_AQHSpgYkMmI4ZTE2YjMtM2UwNi00NTk4LTkwNWEtNjhlY2QwOWNlYWFjDWRlZmF1bHRfbGF5ZXI
- Demo video of 3 minutes or less, and #neatHack posts

## Demo

https://receipts-tau-liard.vercel.app

Local check, from this repo:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest
python -m agent
python -m uvicorn index:app --host 127.0.0.1 --port 8787
```

## Known limitations and next steps

- v1 will say a reversal was processed when the reversal tool reports success and the debit was not updated (seed 28). The demo blocks that reply. v2 says the debit is still open.
- Traces in tests are local only. They are not links a judge can open.
- Entire is not recording this Cursor session.
- cfo.ai opening cash, price, volume, and platform cost are planning assumptions. Inference cost is 0 because the agent does not call a model. There is no signed bank and no observed bank balance.
- Team name for the log is still unset.

## Submission

Confirmed from [neatHack](https://neatlogs.com/hackathon) on Sat 10 Oct 2026:

- One track. Build an agent that completes a substantial task. Solo or a team of 1–4. Code must be written 10–12 Oct 2026.
- Required tools: neatlogs, Entire, and cfo.ai. The demo must cover architecture, implementation, runtime, reasoning, and result for each.
- Judging weights: the agent 30%, use of those three tools 25%, demo video 20%, building in public 15%, usefulness and originality 10%.
- Submit one public quote post of the official neatlogs post on X, with team, project name, public repo, and demo. Include a video of 3 minutes or less. Judges must be able to check that commits fall inside the window.
- Submissions open Mon 12 Oct 2026, 7:00 PM IST, planned close 11:55 PM IST. The final cutoff is announced on Discord. The Submit on X control was not live when these pages were read ("Submissions opening soon").
- Luma registration is closed: [event page](https://luma.com/s5blr882).

Outstanding: exported neatlogs traces, an Entire checkpoint, the demo video, public posts tagged #neatHack, and the quote post. Nothing has been submitted.

## Tools

- **Claude Code** — wrote the scaffold. Later simulator and agent code was written in Cursor.
- **Entire** — installed and enabled for Claude Code. No checkpoint yet for the simulator or the agent.
- **neatlogs** — local spans in tests. No hosted trace yet.
- **cfo.ai** — Receipts plan in the Nithub workspace. Main, Downside, and Upside. Read back on Sat 10 Oct 2026: Main October 2026 is 1 bank, $400 revenue, $380 operating profit, $380 ending cash; December 2027 is 15 banks, $6,000 revenue, $47,700 ending cash. Downside cash is −$20 in October 2026. Inference input is 0.

## Failure taxonomy (v1)

_To be filled from hosted v1 traces, with trace IDs. Local result already seen: seed 28 claims a reversal that did not post._

## Before / after (same 30 seeds)

| Metric | v1 | v2 |
|---|---|---|
| Replies the verifier allows, of 30 | 23 | 30 |
| Unproven claims sent | 7 reversal claims (seeds 9–14, 28) | 0 |
| Cost per case | Inference $0. Base October platform $20 across 200 proved replies. | |

## Evidence checklist

| Criterion | Evidence | Link |
|---|---|---|
| Agent (30%) | 30 scenarios + v2 pass rate | https://receipts-tau-liard.vercel.app |
| Agent (30%) | Recovery trace | |
| neatlogs, Entire, cfo.ai (25%) | v1 false "done" vs v2 trace, same seed | |
| neatlogs, Entire, cfo.ai (25%) | Detections firing on v1 | |
| neatlogs, Entire, cfo.ai (25%) | Prompt v1/v2 label move | |
| neatlogs, Entire, cfo.ai (25%) | Entire checkpoint: fix commit citing trace ID | |
| neatlogs, Entire, cfo.ai (25%) | Entire checkpoint: ask-once policy commit | |
| neatlogs, Entire, cfo.ai (25%) | entire-graph output | |
| neatlogs, Entire, cfo.ai (25%) | cfo.ai business plan | https://app.cfo.ai/s/p_AQHSpgYkMmI4ZTE2YjMtM2UwNi00NTk4LTkwNWEtNjhlY2QwOWNlYWFjDWRlZmF1bHRfbGF5ZXI |
| Demo video (20%) | 3-min video | |
| Building in public (15%) | posts tagged #neatHack | |
| Usefulness and originality (10%) | the complaint the agent resolves | |
| Commits inside the window | public repo, dates on the commits | https://github.com/Demiladepy/receipts |
