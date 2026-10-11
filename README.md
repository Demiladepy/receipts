# Receipts

**It doesn't say done until it can prove it.**

Receipts resolves "debited but not credited" complaints end to end. It asks the sender bank, the payment switch and the beneficiary bank separately, and it cannot tell the customer anything it cannot prove from a trace span.

Live demo, built from the recorded runs: https://receipts-tau-liard.vercel.app

## The four rules, enforced in code

1. **Every claim needs a receipt.** A reply is a list of claims from a fixed vocabulary. Each one cites a receipt id, and that id *is* the neatlogs span id of the tool call that proves it. A deterministic verifier (`verifier/assertions.py`) blocks the reply otherwise.
2. **Receipts expire.** A claim about the debit, a reversal or the balance must cite a read made after the last write. A "pending" switch status must be confirmed by a second read.
3. **Sources have authority.** The ledger owns the debit, the switch owns the instruction, the beneficiary bank owns the credit. A write's acknowledgement owns nothing. Money only moves on receipts: the reversal tool refuses unless the latest reads show the debit open, the switch failed, no credit, and the amount within the limit.
4. **Ask once, then it is policy.** A case the agent cannot settle escalates with an evidence pack. A human decides; Claude Code turns the decision into a rule plus a test and commits it, and Entire records that session. The next similar case cites the rule.

## Results

30 seeded complaints under stress chaos (first calls time out, reversals report success and never post, the first switch read is stale), three runs per version, gpt-4.1-mini, graded against the simulator's hidden truth:

| | v1 · no gate | v2 · reply gate | v3 · reply + action gate |
|---|---|---|---|
| Resolved correctly | 58/90 | 79/90 | **90/90** |
| False claims sent | 31 | 0 | **0** |
| Unproven claims sent | 55 | 0 | **0** |
| Harmful reversals | 3 | 11 | **0** |
| Cost per case | $0.0015 | $0.0046 | **$0.0047** |

The full table, the failure taxonomy with neatlogs trace ids, and the build log are in [hackathon.md](hackathon.md).

## Run it

Python 3.11+.

```bash
git clone https://github.com/Demiladepy/receipts.git
cd receipts
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # then fill in OPENAI_API_KEY and NEATLOGS_API_KEY
```

No keys are needed for the tests or the demo page:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m uvicorn index:app --port 8787      # demo page on the recorded runs
```

With keys, run the agent (each run is a neatlogs trace):

```bash
python -m agent.bench run --version v3 --profile stress --seeds 28            # one case
python -m agent.bench run --version production --repeats 3                    # whatever the neatlogs "production" label points at
python -m agent.bench summary runs/v1-stress-x3.jsonl runs/v3-stress-x3.jsonl
python -m agent.taxonomy runs/v1-stress-x3.jsonl
```

Ask once:

```bash
python -m policy.ask_once pack --seed 21                                      # agent escalates, evidence pack saved
python -m policy.ask_once decide ESC-0021 --by "you" --decision "..."         # headless Claude Code writes rule + test + commit
python -m policy.ask_once replay --seed 22                                    # the next case cites the rule
```

## Layout

| Path | What |
|---|---|
| `sim/` | Simulated sender ledger, switch and beneficiary bank; 30 seeds (`catalog.py`); stress chaos (`stress.py`) |
| `agent/llm_agent.py` | The agent loop: model plans, tools leave receipts, v3 action gate |
| `agent/receipts.py` | Receipt book; receipt id = neatlogs span id |
| `agent/truth.py` | Grades a run against hidden ground truth |
| `agent/bench.py`, `agent/taxonomy.py` | Runs versions over the seeds; classifies failures |
| `verifier/assertions.py` | Deterministic reply verifier |
| `policy/` | Committed rules, the rule store, the ask-once loop and its inbox |
| `runs/` | Recorded runs the numbers come from |
| `public/`, `index.py`, `webapp_runs.py` | Demo page and API |

## Tools

- **neatlogs**: every run is a trace (AGENT case span, a TOOL span per tool call, a CHAIN span per verifier check, model calls via `neatlogs.wrap`). The three prompts are versions of the managed prompt `receipts-agent`, and the `production` label moved v1 → v2 → v3.
- **Entire**: every commit carries an `Entire-Checkpoint` trailer. Fix commits cite the neatlogs trace that triggered them.
- **cfo.ai**: pricing, cost and runway, with cost per case measured from these runs.
- **Billing**: a bank pays per proved resolution; every statement line names its neatlogs trace. Collection runs on Bachs (NGN checkout for each monthly statement); Paystack and Dodo Payments adapters are also built. Dodo could not onboard a Nigerian business.
- **Claude Code**: wrote most of this repo, and at runtime it is the ask-once policy writer.

The banks are simulated. Chaos comes from the seed, so every run is reproducible.
