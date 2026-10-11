"""Run the model-driven agent over the 30 seeds and compare versions.

    python -m agent.bench run --version v1 --profile stress
    python -m agent.bench run --version v2 --profile stress
    python -m agent.bench summary runs/v1-stress.jsonl runs/v2-stress.jsonl
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import neatlogs

from agent.tracing import init_tracing
from sim.catalog import load_scenarios
from sim.stress import stress_flags

RUNS = Path(__file__).resolve().parent.parent / "runs"


def parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            seeds.extend(range(int(lo), int(hi) + 1))
        elif part:
            seeds.append(int(part))
    return seeds


def run(version: str, profile: str, seeds: list[int], workers: int, out: Path) -> list[dict]:
    from agent.llm import make_client
    from agent.llm_agent import run_case

    init_tracing(tags=[f"prompt:{version}", f"chaos:{profile}"])
    client = make_client()
    scenarios = [s for s in load_scenarios() if s.seed in seeds]

    def one(scenario):
        chaos = stress_flags(scenario) if profile == "stress" else None
        try:
            record = run_case(scenario, version, chaos=chaos, client=client)
        except Exception as exc:  # a crashed run is a result too
            record = {"seed": scenario.seed, "version": version, "status": "crashed", "error": repr(exc)}
        record["profile"] = profile
        print(_line(record), flush=True)
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = sorted(pool.map(one, scenarios), key=lambda r: r["seed"])
    neatlogs.flush()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    print(f"wrote {out}")
    return records


def _line(r: dict) -> str:
    if r.get("status") == "crashed":
        return f"seed={r['seed']:02d} CRASHED {r.get('error')}"
    a = r["audit"]
    flags = []
    if a["false_claims"]:
        flags.append(f"FALSE x{len(a['false_claims'])}")
    if r["unproven_claims_sent"]:
        flags.append(f"unproven x{r['unproven_claims_sent']}")
    if a["harmful_action"]:
        flags.append("HARMFUL")
    if a.get("unconfirmed_reversal"):
        flags.append("RISKY-REVERSAL")
    if r["blocks"]:
        flags.append(f"blocked x{r['blocks']}")
    ok = "ok " if a["resolved_correctly"] else "BAD"
    return (f"seed={r['seed']:02d} {ok} {r['status']:<8} expected={a['expected']:<8} "
            f"tools={len(r['tool_order'])} ${r['usage']['cost_usd']:.4f} {' '.join(flags)}")


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def metrics(records: list[dict]) -> dict:
    done = [r for r in records if r.get("status") != "crashed"]
    n = len(records)
    cost = sum(r["usage"]["cost_usd"] for r in done)
    return {
        "runs": n,
        "crashed": n - len(done),
        "resolved_correctly": sum(r["audit"]["resolved_correctly"] for r in done),
        "replies_sent": sum(r["status"] == "sent" for r in done),
        "false_claims_sent": sum(len(r["audit"]["false_claims"]) for r in done),
        "runs_with_false_claim": sum(bool(r["audit"]["false_claims"]) for r in done),
        "unproven_claims_sent": sum(r["unproven_claims_sent"] for r in done),
        "harmful_actions": sum(r["audit"]["harmful_action"] for r in done),
        "reversals_on_unconfirmed_evidence": sum(bool(r["audit"].get("unconfirmed_reversal")) for r in done),
        "debits_left_open_silently": sum(
            r["audit"]["debit_left_open"] and not r.get("escalation") for r in done),
        "replies_blocked_then_fixed": sum(r["blocks"] > 0 and r["status"] == "sent" for r in done),
        "tool_calls_avg": round(sum(len(r["tool_order"]) for r in done) / max(len(done), 1), 1),
        "cost_usd_total": round(cost, 4),
        "cost_usd_per_case": round(cost / max(len(done), 1), 5),
        "latency_s_avg": round(sum(r["latency_s"] for r in done) / max(len(done), 1), 1),
    }


def summary(paths: list[Path]) -> str:
    cols = {p.stem: metrics(load(p)) for p in paths}
    keys = list(next(iter(cols.values())))
    lines = ["| metric | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for k in keys:
        lines.append(f"| {k} | " + " | ".join(str(c[k]) for c in cols.values()) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--version", choices=["v1", "v2", "v3"], required=True)
    r.add_argument("--profile", choices=["catalog", "stress"], default="stress")
    r.add_argument("--seeds", default="1-30")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--out", type=Path)
    s = sub.add_parser("summary")
    s.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    if args.cmd == "run":
        out = args.out or RUNS / f"{args.version}-{args.profile}.jsonl"
        run(args.version, args.profile, parse_seeds(args.seeds), args.workers, out)
    else:
        print(summary(args.paths))


if __name__ == "__main__":
    main()
