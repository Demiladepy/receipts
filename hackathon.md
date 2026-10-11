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

- Python simulator: sender ledger, switch, beneficiary bank, 30 fixed seeds (`sim/catalog.py`). `sim/stress.py` adds a harder, seed-derived chaos profile on the same seeds: first-call timeouts, reversals that report success and never post, and a stale first switch read.
- Model-driven agent (`agent/llm_agent.py`): gpt-4.1-mini through the OpenAI SDK (any OpenAI-compatible endpoint via `OPENAI_BASE_URL`). The model plans and picks tools; every tool call runs in its own neatlogs TOOL span.
- Receipts (`agent/receipts.py`): a receipt id **is** the neatlogs span id of the tool call. Every claim in a reply cites one.
- Verifier (`verifier/assertions.py`): deterministic, no model. Source authority, payload match, freshness after writes, switch staleness, policy fit, and a sentence guard against overclaiming.
- Action gate (v3): `sender_reverse` refuses unless the latest receipts show the debit open, the switch failed, the beneficiary not credited, and the amount within the limit.
- Ground-truth audit (`agent/truth.py`): grades every run against the simulator's hidden truth, so the numbers do not rest on our own verifier grading itself.
- Ask-once loop (`policy/ask_once.py`): escalation pack, a human decision, headless Claude Code writes rule + test + commit.
- neatlogs 1.4.26, exporting live (0 export failures). Entire CLI 0.11.4 with `commit_linking: always`; every commit since `094038b` carries an `Entire-Checkpoint` trailer.

Demo: https://receipts-tau-liard.vercel.app

cfo.ai is connected for the Nithub workspace. The Receipts plan page holds the pricing, cost, revenue, and cash model. Link: https://app.cfo.ai/s/p_AQHSpgYkMmI4ZTE2YjMtM2UwNi00NTk4LTkwNWEtNjhlY2QwOWNlYWFjDWRlZmF1bHRfbGF5ZXI

Crustdata is a published participant credit, not one of the three required tools. Receipts does not call it: company and people data does not help settle a payment dispute.

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

### Sun 11 Oct 2026, morning — model-driven agent, three versions, real traces

Read the field first: 236 #neatHack posts from the previous 24 hours. Closest entry is a UPI dispute agent; several projects cite sources per claim. What nobody else posted: proof that **expires** after a write, and a decision that becomes **committed policy**. Those lead.

- Replaced the fixed rule engine with a model that plans and picks tools. The old v1 prompt told the agent "Trust the reversal response. Do not read the ledger again." That plants the failure, so it was dropped; the new v1 prompt is a plain, reasonable first attempt.
- **v1** (no gate). First real trace on seed 28, `b2074a54abad39f688ce970efccba7b4`: "We have reversed the debit", citing the reversal tool's acknowledgement. The ledger never posted it.
- **v2** (reply gate + rules of evidence). Unproven claims sent fell to 0. Reading the v2 traces showed a new failure: it reversed when sources disagreed, and reversed transfers that had succeeded. `4b6e758cf6f4b72f467213ae94942e8f` (seed 18, switch success, no credit), `87a6d6874e3be571dc75ca80ddd592eb` (seed 22, already credited: pays twice). The verifier gated words, not actions.
- **v3** (action gate). Money moves only on receipts. Two further fixes came from v3 traces: `8775a93955168544f031dba65aed24b9` (seed 24, over the limit, reversal let through) and `b58717d2c865bc0f38d3fb1d81203fff` (seed 27, reply withheld because a block reason was not actionable).
- Commits, each with an Entire checkpoint: `094038b`, `d4af7c2`, `6fda35d`, `eaf2d94`, `412d40c`.
- Tests: 75 passed (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`).

### Sun 11 Oct 2026 — ask once

`python -m policy.ask_once pack --seed 21`: the agent escalated seed 21 (switch failed, beneficiary credited), trace `d12137202386aec8ce79d8349350cfa8`, pack in `policy/inbox/ESC-0021.json`. Decision by Demiladepy: option A, trust the beneficiary bank on whether the credit posted. Rule commit: pending (headless Claude Code needs `/login` on this machine).

### Planned, not done

- Ask-once rule commit by headless Claude Code, then `replay --seed 22`
- neatlogs detections on the v1 runs, prompt versions with labels
- cfo.ai: cost per case from the runs below ($0.0047 at gpt-4.1-mini list price, $0.40 / $1.60 per 1M tokens)
- Demo page on the model-driven runs; demo video; posts 2 to 4

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

- The banks and the switch are simulated. Chaos is seed-derived, so every run is reproducible but the faults are ours.
- The verifier's sentence guard is a word list with negation handling. It is deterministic and explainable, not a language model; a sentence can still be misleading without using a guarded word.
- v1 and v2 x3 runs were recorded before the last two v3 fixes (`6fda35d`, `eaf2d94`). v1 has no gate, so they do not change it.
- One model, temperature 0, three repeats per version. Model output still varies between repeats; the counts are over 90 runs per version.

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

- **Claude Code** — wrote the scaffold, the model-driven agent, the verifier, the action gate and the ask-once loop. Saturday's simulator and first demo were written in Cursor (commit `ccff2a5`, no Entire checkpoint for that work). At runtime, headless Claude Code is the ask-once policy writer.
- **Entire** — enabled for Claude Code with `commit_linking: always`. Every commit from `094038b` on carries an `Entire-Checkpoint` trailer; fix commits cite the neatlogs trace that triggered them.
- **neatlogs** — every agent run is a trace: one AGENT span per case, a TOOL span per tool call (its span id is the receipt id), a CHAIN span per verifier check, and the model calls via `neatlogs.wrap`. Runs are tagged `prompt:v1|v2|v3` and `chaos:stress`.
- **cfo.ai** — Receipts plan in the Nithub workspace. Main, Downside, and Upside. Read back on Sat 10 Oct 2026: Main October 2026 is 1 bank, $400 revenue, $380 operating profit, $380 ending cash; December 2027 is 15 banks, $6,000 revenue, $47,700 ending cash. Downside cash is −$20 in October 2026. That plan used inference cost 0; the measured cost is now $0.0047 per case (v3, gpt-4.1-mini) and needs to go into the model.

## Failure taxonomy

Generated by `python -m agent.taxonomy` from the run files. Every trace id is a neatlogs trace.

### v1-stress-x3 (90 runs)

| failure | runs | seeds | example trace |
|---|---|---|---|
| Said the reversal posted, citing the reversal tool's acknowledgement | 15 | 9, 11, 12, 21, 27, 29 | `7114b3729a515d65daf5e12c90dac9ff` (seed 9) |
| Lying reversal: told the customer it was done, the debit was still open | 4 | 14, 28 | `82d6d120c7b95eea39c6375a447ac3c5` (seed 14) |
| Reported a stale 'pending' switch read as the transfer's status | 24 | 1, 10, 15, 17, 23, 25, 28, 29 | `3915d3efdbb82648680a4e96e891ab50` (seed 1) |
| Reversed when sources disagreed (switch vs beneficiary) | 3 | 21, 29 | `8bdac9e2e9621215bfbad2ac9cc9854b` (seed 29) |
| Reversed without a successful read of every source | 4 | 27, 28 | `5b744930b5d6cb52a8c1a7ec33f1abf7` (seed 27) |
| Did not escalate a case that needed a human | 8 | 22, 23, 25, 29 | `db5d73c43a94effd0ad4ad4fe1b6ac66` (seed 22) |
| Other false claim sent | 1 | 30 | `91b7413e9af8f50dd812382a104faded` (seed 30) |

### v2-stress-x3 (90 runs)

| failure | runs | seeds | example trace |
|---|---|---|---|
| Reversed when sources disagreed (switch vs beneficiary) | 11 | 18, 19, 20, 21, 29 | `a9e8854c235f19c41c422d728909dc45` (seed 18) |
| Reversed a transfer that had succeeded and been credited (pays twice) | 4 | 2, 3, 5 | `a68f00583b21c774a91f0e8aa916733d` (seed 3) |
| Reversed without a successful read of every source | 3 | 27 | `be2541f9216568b9d6e7de68b9ae164b` (seed 27) |
| Did not escalate a case that needed a human | 1 | 23 | `1b803ee4263f4de74506d956bae7f149` (seed 23) |
| Reply withheld after three blocked attempts (safe failure) | 2 | 22, 27 | `1a623a5ae73a66cf817333ba5e75deba` (seed 22) |

### v3-stress-x3 (90 runs)

| failure | runs | seeds | example trace |
|---|---|---|---|
| none | 0 | | |

## Before / after (same 30 seeds)

30 stress seeds, three repeats each, gpt-4.1-mini, temperature 0. `python -m agent.bench summary runs/v1-stress-x3.jsonl runs/v2-stress-x3.jsonl runs/v3-stress-x3.jsonl`

| metric | v1-stress-x3 | v2-stress-x3 | v3-stress-x3 |
|---|---|---|---|
| runs | 90 | 90 | 90 |
| crashed | 0 | 0 | 0 |
| resolved_correctly | 58 | 72 | 90 |
| replies_sent | 90 | 88 | 90 |
| false_claims_sent | 30 | 0 | 0 |
| runs_with_false_claim | 28 | 0 | 0 |
| unproven_claims_sent | 50 | 0 | 0 |
| harmful_actions | 3 | 15 | 0 |
| reversals_on_unconfirmed_evidence | 7 | 18 | 0 |
| debits_left_open_silently | 9 | 0 | 0 |
| replies_blocked_then_fixed | 0 | 17 | 32 |
| tool_calls_avg | 3.5 | 6.6 | 6.4 |
| cost_usd_total | 0.1312 | 0.4219 | 0.4249 |
| cost_usd_per_case | 0.00146 | 0.00469 | 0.00472 |
| latency_s_avg | 3.3 | 7.1 | 7.6 |

- *resolved_correctly*: reply sent, no false claim (against hidden truth), no harmful action, and the right action taken or escalated.
- *false_claims_sent*: claims the customer received that the simulator's ground truth contradicts.
- *unproven_claims_sent*: claims the receipt verifier could not prove (v1 runs it in shadow).
- *harmful_actions*: a reversal on a case that should not be reversed.

## Evidence checklist

| Criterion | Evidence | Link |
|---|---|---|
| Agent (30%) | 30 seeds x 3, v3 90/90 resolved | `runs/v3-stress-x3.jsonl`, table above |
| Agent (30%) | Recovery trace | `23e268c66a037086268d7abc3b1badc9` (v3 seed 28: re-reads stale switch, reversal not posted, re-reads ledger, escalates, tells the truth) |
| neatlogs, Entire, cfo.ai (25%) | v1 false "done" vs v3 trace, same seed | v1 `b2074a54abad39f688ce970efccba7b4` vs v3 `23e268c66a037086268d7abc3b1badc9` (seed 28) |
| neatlogs, Entire, cfo.ai (25%) | Detections firing on v1 | |
| neatlogs, Entire, cfo.ai (25%) | Prompt v1/v2 label move | |
| neatlogs, Entire, cfo.ai (25%) | Entire checkpoint: fix commit citing trace ID | `6fda35d` (checkpoint `01M4MQRFKEN8E58195CMYGHFY1`, cites `8775a939…`) |
| neatlogs, Entire, cfo.ai (25%) | Entire checkpoint: ask-once policy commit | |
| neatlogs, Entire, cfo.ai (25%) | entire-graph output | |
| neatlogs, Entire, cfo.ai (25%) | cfo.ai business plan | https://app.cfo.ai/s/p_AQHSpgYkMmI4ZTE2YjMtM2UwNi00NTk4LTkwNWEtNjhlY2QwOWNlYWFjDWRlZmF1bHRfbGF5ZXI |
| Demo video (20%) | 3-min video | |
| Building in public (15%) | posts tagged #neatHack | |
| Usefulness and originality (10%) | the complaint the agent resolves | |
| Commits inside the window | public repo, dates on the commits | https://github.com/Demiladepy/receipts |
