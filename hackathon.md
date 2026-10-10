# Receipts — #neatHack build log

Window opened: Sat 10 Oct 2026. All commits in this repo are dated inside the hackathon window.

## Tools
- **Claude Code** — writes the code; runtime policy writer for the ask-once loop
- **Entire** — captures Claude Code sessions as checkpoints on commit
- **neatlogs** — traces every agent run; detections; prompt labels v1 → v2
- **cfo.ai** — pricing / unit economics from real neatlogs cost data

## Failure taxonomy (v1)
_To be filled from v1 traces, with trace IDs._

## Before / after (same 30 seeds)
| Metric | v1 | v2 |
|---|---|---|
| Scenarios resolved correctly | | |
| Unproven claims sent | | |
| Cost per case | | |

## Evidence checklist
| Criterion | Evidence | Link |
|---|---|---|
| Agent | 30 scenarios + v2 pass rate | |
| Agent | Recovery trace | |
| Tools | v1 false "done" vs v2 trace, same seed | |
| Tools | Detections firing on v1 | |
| Tools | Prompt v1/v2 label move | |
| Tools | Entire checkpoint: fix commit citing trace ID | |
| Tools | Entire checkpoint: ask-once policy commit | |
| Tools | entire-graph output | |
| Tools | cfo.ai business plan | |
| Demo | 3-min video | |
| Building in public | 4 #neatHack posts | |
