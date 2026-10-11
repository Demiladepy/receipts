"""Terminal walkthrough for the demo video.

    python -m demo case 28 --version v1 --recorded 3   # replay the recorded v1 run that lied
    python -m demo case 28 --version v3                # run v3 live (a new neatlogs trace)
    python -m demo numbers                             # v1 -> v2 -> v3 -> v3 + rules
    python -m demo rules                               # committed rules and their licenses
    python -m demo bill                                # statement and the Bachs sandbox checkout
"""

import argparse
import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
RUNS = {"v1": "v1-stress-x3", "v2": "v2-stress-x3", "v3": "v3-stress-x3", "v3p": "v3-policy-stress-x3"}
NAMES = {"v1": "v1 · no gate", "v2": "v2 · reply gate", "v3": "v3 · reply + action gate",
         "v3p": "v3 + 2 committed rules"}
console = Console()


def _load(name: str) -> list[dict]:
    path = ROOT / "runs" / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _said(r: dict) -> str:
    if not r["ok"]:
        return f"[red]{r['error']}[/red]"
    v = r["value"] or {}
    op = r["op"]
    if op == "sender.get_debit":
        return "reversal applied" if v.get("reversal_applied") else "debit open" if v.get("debited") else "not debited"
    if op == "switch.get_status":
        return str(v.get("status"))
    if op == "beneficiary.get_credit":
        return "credited" if v.get("credited") else "not credited"
    if op == "sender.reverse":
        return f"[yellow]acknowledged: {v.get('status')}[/yellow]"
    if op == "policy.lookup":
        return f"rule {v.get('rule_id')}" if v.get("found") else "no rule"
    if op == "case.escalate":
        return f"queued {v.get('escalation_id')}"
    if op == "sender.get_balance":
        return f"NGN {v.get('balance_kobo', 0) / 100:,.2f}"
    return "ok"


def show_case(record: dict, scenario) -> None:
    f = scenario.facts
    console.print(Panel(f"{scenario.narrative}\n\n[dim]{scenario.complaint_id} · hidden truth: switch "
                        f"{f.switch_status}, beneficiary {'credited' if f.beneficiary_credited else 'not credited'}"
                        f"{', already reversed' if f.reversal_applied else ''}[/dim]",
                        title=f"Complaint · seed {scenario.seed}", border_style="blue"))
    tools = Table(box=box.SIMPLE, title=f"{NAMES[record['version']]}: tool calls (each one is a neatlogs span)")
    for col in ("#", "tool", "receipt (span id)", "said"):
        tools.add_column(col)
    for r in record["receipts"]:
        tools.add_row(str(r["seq"]), r["op"], r["receipt_id"], _said(r))
    console.print(tools)
    for i, a in enumerate(record["attempts"][:-1], 1):
        reasons = [f"{c['assertion']}: {c['reason']}" for c in a["verdict"]["claims"] if not c["proved"]]
        if a["verdict"]["next_step_reason"]:
            reasons.append("next step: " + a["verdict"]["next_step_reason"])
        console.print(Panel("\n".join(reasons), title=f"verifier BLOCKED attempt {i}", border_style="red"))
    if record["message"]:
        console.print(Panel(record["message"], title="what the customer receives", border_style="white"))
    else:
        console.print(Panel("Nothing sent: the reply could not be proved. The case went to a human with its receipts.",
                            title="what the customer receives", border_style="yellow"))
    if record["attempts"]:
        title = ("claims and their receipts (v1 sends without checking; verifier shown in shadow)"
                 if record["version"] == "v1" else "claims and their receipts (checked before sending)")
        claims = Table(box=box.SIMPLE, title=title)
        for col in ("", "claim", "receipt", "verifier"):
            claims.add_column(col)
        for c in record["attempts"][-1]["verdict"]["claims"]:
            claims.add_row("[green]✓[/green]" if c["proved"] else "[red]✗[/red]", c["text"], c["receipt_id"],
                           "proved" if c["proved"] else f"[red]{c['reason']}[/red]")
        console.print(claims)
    a = record["audit"]
    if a["false_claims"] or a["harmful_action"]:
        lines = [f"FALSE: {x}" for x in a["false_claims"]]
        if a["harmful_action"]:
            lines.append(f"HARMFUL: {a.get('unconfirmed_reversal') or 'reversal on a case that should not be reversed'}")
        console.print(Panel("\n".join(lines), title="checked against the simulator's hidden truth", border_style="red"))
    else:
        console.print(Panel("Every sentence the customer received is true. No harmful action.",
                            title="checked against the simulator's hidden truth", border_style="green"))
    console.print(f"[dim]neatlogs trace[/dim] [bold]{record['trace_id']}[/bold]   "
                  f"[dim]cost[/dim] ${record['usage']['cost_usd']:.4f}   [dim]status[/dim] {record['status']}")


def cmd_case(seed: int, version: str, recorded: int | None) -> None:
    from sim.catalog import load_scenarios

    scenario = next(s for s in load_scenarios() if s.seed == seed)
    if recorded:
        record = next(r for r in _load(RUNS[version]) if r["seed"] == seed and r.get("rep", 1) == recorded)
        console.print(f"[dim]replaying recorded run {recorded} of seed {seed} ({RUNS[version]}.jsonl)[/dim]")
    else:
        import neatlogs

        from agent.llm_agent import run_case
        from agent.tracing import init_tracing
        from sim.stress import stress_flags

        init_tracing(tags=[f"prompt:{version}", "chaos:stress", "demo"])
        with console.status(f"running {NAMES[version]} live on seed {seed}…"):
            record = run_case(scenario, "v3" if version == "v3p" else version, chaos=stress_flags(scenario))
        neatlogs.flush()
    show_case(record, scenario)


def cmd_numbers() -> None:
    from agent.bench import metrics

    cols = {v: metrics(_load(name)) for v, name in RUNS.items()}
    t = Table(title="Same 30 stress seeds × 3 runs, graded against hidden truth", box=box.SIMPLE_HEAVY)
    t.add_column("metric")
    for v in cols:
        t.add_column(NAMES[v], justify="right")
    rows = [("resolved_correctly", "resolved correctly"), ("false_claims_sent", "false claims sent"),
            ("unproven_claims_sent", "unproven claims sent"), ("harmful_actions", "harmful reversals"),
            ("escalated_to_human", "sent to a human"), ("unnecessary_escalations", "unnecessary escalations"),
            ("cost_usd_per_case", "cost per case (USD)")]
    for key, label in rows:
        t.add_row(label, *[f"${c[key]:.4f}" if key.startswith("cost") else str(c[key]) for c in cols.values()])
    console.print(t)


def cmd_rules() -> None:
    from policy import license
    from policy.store import load_rules

    for rule in load_rules():
        s = license.state(rule["rule_id"])
        cond = " and ".join(f"{c['op']}.{c['field']} = {c['equals']}" for c in rule.get("conditions", []))
        console.print(Panel(f"[bold]“{rule['decision']}”[/bold]\n\ndecided by {rule.get('decided_by')} on "
                            f"{rule['source_case']['escalation_id']} (seed {rule['source_case']['seed']})\n"
                            f"applies when {cond}\nlicense: "
                            + ("[green]active[/green]" if s["event"] != "revoked" else f"[red]revoked[/red] ({s.get('reason')})"),
                            title=rule["rule_id"], border_style="green" if s["event"] != "revoked" else "red"))


def cmd_bill() -> None:
    stmt = json.loads((ROOT / "billing" / "statements" / "2026-10-v3-policy-stress-x3.json").read_text(encoding="utf-8"))
    t = Table(title=f"Usage statement {stmt['period']}: {stmt['customer']}", box=box.SIMPLE)
    for col in ("complaint", "neatlogs trace", "rule", "amount"):
        t.add_column(col)
    for line in stmt["lines"][:8]:
        t.add_row(line["complaint_id"], line["neatlogs_trace_id"], line["policy_rule"] or "",
                  f"NGN {line['amount_kobo'] / 100:,.2f}")
    t.add_row("…", f"{len(stmt['lines']) - 8} more lines", "", "")
    console.print(t)
    console.print(f"[bold]{stmt['proved_resolutions']} proved resolutions = NGN {stmt['total_kobo'] / 100:,.2f}[/bold]   "
                  f"[dim]{stmt['escalated_free']} escalations to your team: not charged[/dim]")
    evidence = (ROOT / "evidence" / "bachs-checkout.md").read_text(encoding="utf-8")
    url = next((l.split("|")[2].strip() for l in evidence.splitlines() if l.startswith("| Checkout URL")), "")
    console.print(Panel(f"Bachs sandbox checkout, NGN, statement SHA-256 pinned in its metadata\n{url}",
                        border_style="blue"))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("case")
    c.add_argument("seed", type=int)
    c.add_argument("--version", choices=list(RUNS), default="v3")
    c.add_argument("--recorded", type=int, help="replay recorded run 1-3 instead of running live")
    sub.add_parser("numbers")
    sub.add_parser("rules")
    sub.add_parser("bill")
    args = parser.parse_args()
    {"case": lambda: cmd_case(args.seed, args.version, args.recorded), "numbers": cmd_numbers,
     "rules": cmd_rules, "bill": cmd_bill}[args.cmd]()


if __name__ == "__main__":
    main()
