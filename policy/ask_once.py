"""Ask once, then it is policy.

    python -m policy.ask_once pack --seed 21
        Run the agent on a case it cannot settle. It escalates; the evidence pack
        (every receipt, the conflict, the options) is saved to policy/inbox/.

    python -m policy.ask_once decide ESC-0021 --by "Name" --decision "..."
        A human decides in plain words. Headless Claude Code turns the decision into
        policy/rules/<rule>.json plus a test, runs the tests and commits. Entire
        records that Claude Code session as the commit's checkpoint.

    python -m policy.ask_once replay --seed 22
        The next similar case looks the rule up, follows it and cites it.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sim.money import format_naira

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "policy" / "inbox"

AUTHORITY = {
    "sender.get_debit": "sender ledger (authoritative for the debit and reversal)",
    "sender.get_balance": "sender ledger (authoritative for the balance)",
    "switch.get_status": "payment switch (authoritative for the transfer instruction)",
    "beneficiary.get_credit": "beneficiary bank (authoritative for whether the credit posted)",
}


def _scenario(seed: int):
    from sim.catalog import load_scenarios

    return next(s for s in load_scenarios() if s.seed == seed)


def _run(seed: int, version: str = "v3", profile: str = "catalog") -> dict:
    from agent.llm_agent import run_case
    from agent.tracing import init_tracing

    init_tracing(tags=[f"prompt:{version}", "ask-once"])
    scenario = _scenario(seed)
    chaos = None
    if profile == "stress":
        from sim.stress import stress_flags

        chaos = stress_flags(scenario)
    record = run_case(scenario, version, chaos=chaos)
    import neatlogs

    neatlogs.flush()
    return record


def pack(seed: int, profile: str = "catalog") -> Path:
    record = _run(seed, profile=profile)
    esc = record.get("escalation")
    if not esc:
        print(f"seed {seed} did not escalate (status {record['status']}); nothing to ask.")
        sys.exit(1)
    reads = [r for r in record["receipts"] if r["op"] in AUTHORITY and r["ok"]]
    statements = []
    for r in reads:
        v = r["value"]
        if r["op"] == "switch.get_status":
            said = f"status {v['status']}"
        elif r["op"] == "beneficiary.get_credit":
            said = f"credited={v['credited']}" + (f" at {v['credit_at']}" if v.get("credit_at") else "")
        elif r["op"] == "sender.get_debit":
            said = f"debited={v['debited']}, reversal_applied={v['reversal_applied']}"
        else:
            said = f"balance {format_naira(v['balance_kobo'])}"
        statements.append({"receipt_id": r["receipt_id"], "source": AUTHORITY[r["op"]], "op": r["op"],
                           "says": said})
    evidence = {
        **esc,
        "seed": seed,
        "trace_id": record["trace_id"],
        "amount": format_naira(_scenario(seed).facts.amount_kobo),
        "pattern_seen": esc.get("case_type"),
        "statements": statements,
        "customer_reply_sent": record["message"],
        "options": _options(reads),
        "asked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    INBOX.mkdir(parents=True, exist_ok=True)
    path = INBOX / f"{esc['escalation_id']}.json"
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    _print_pack(evidence)
    print(f"\nsaved {path.relative_to(ROOT)}")
    return path


def _options(reads: list[dict]) -> list[str]:
    latest = {r["op"]: r["value"] for r in reads}
    switch = (latest.get("switch.get_status") or {}).get("status")
    credited = (latest.get("beneficiary.get_credit") or {}).get("credited")
    if switch == "success" and credited:
        return [
            "A. Every source agrees the credit posted: tell the customer it was credited, cite the "
            "beneficiary bank's receipt, ask them to check with the recipient. No reversal, no escalation.",
            "B. As A, but escalate large amounts for a human double-check.",
            "C. Keep escalating every disputed credit to a human.",
        ]
    if switch == "failed" and credited:
        return [
            "A. Trust the beneficiary bank on whether the credit posted: tell the customer it was "
            "credited, do not reverse, do not escalate.",
            "B. Trust the switch: reverse the debit (risk: the customer is paid twice).",
            "C. Keep escalating every case like this to a human.",
        ]
    return ["A. Describe the decision in your own words.", "C. Keep escalating cases like this to a human."]


def _print_pack(e: dict) -> None:
    print(f"ESCALATION {e['escalation_id']}  complaint {e['complaint_id']}  {e['amount']}")
    print(f"trace {e['trace_id']}")
    print(f"agent's reason: {e['reason']}\n")
    for s in e["statements"]:
        print(f"  [{s['receipt_id']}] {s['source']}: {s['says']}")
    print("\nWhat should happen to cases like this?")
    for o in e["options"]:
        print(f"  {o}")


WRITER_PROMPT = """You are the policy writer for the Receipts agent in this repository.
A human has decided how to handle a case type the agent escalated. Turn that decision
into a committed rule. Work only in the files named below.

Escalation pack: {pack_path}
Human decision (verbatim): "{decision}"
Decided by: {by}, at {decided_at}

1. Read the pack and policy/store.py (see conditions_hold) and the receipts in the pack.
2. Write policy/rules/{rule_id}.json with exactly these keys:
   rule_id ("{rule_id}"), case_type (the pack's case_type), decision (the human's words,
   verbatim), instructions (what the agent must do and must not do, in plain imperative
   sentences, consistent with the decision), customer_line (one sentence the agent may
   adapt for the customer, with no amounts or dates), conditions (a list of
   {{"op", "field", "equals"}} checks on the latest reads that identify this case type,
   taken from the pack's receipts), decided_by, decided_at, source_case
   ({{"escalation_id", "seed", "trace_id"}} from the pack).
3. Write tests/policy/test_{rule_id}.py (create tests/policy/__init__.py if missing) that
   checks: the rule loads; policy.store.lookup(case_type) returns it; conditions_hold is
   true for the pack's receipts; conditions_hold is false for a counter-example where the
   switch says failed and the beneficiary was NOT credited.
4. Run: python -m pytest tests/policy -q   and fix your files until it passes.
5. Commit only those files plus the pack:
   git add policy/rules/{rule_id}.json tests/policy {pack_path}
   git commit with subject "Policy {rule_id}: <what the rule does, under 60 chars>" and a
   body that quotes the decision, names {by}, and cites escalation {escalation_id},
   seed {seed} and neatlogs trace {trace_id}. End the message with:
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Do not edit any other file. Do not push.
"""


def decide(escalation_id: str, decision: str, by: str, rule_id: str | None, dry_run: bool) -> None:
    path = INBOX / f"{escalation_id}.json"
    e = json.loads(path.read_text(encoding="utf-8"))
    rule_id = rule_id or f"{e['case_type'].replace('_', '-')}-v1"
    prompt = WRITER_PROMPT.format(
        pack_path=path.relative_to(ROOT).as_posix(), decision=decision.replace('"', "'"), by=by,
        decided_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), rule_id=rule_id,
        escalation_id=escalation_id, seed=e["seed"], trace_id=e["trace_id"],
    )
    if dry_run:
        print(prompt)
        return
    claude = shutil.which("claude")
    if not claude:
        sys.exit("Claude Code CLI not found on PATH")
    cmd = [
        claude, "-p",
        "--permission-mode", "acceptEdits",
        "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep",
        "Bash(python -m pytest:*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)",
        "Bash(git diff:*)", "Bash(mkdir:*)",
    ]
    print(f"Claude Code is writing rule {rule_id} from {escalation_id} ...", flush=True)
    # The prompt goes on stdin: on Windows the claude.cmd shim cuts a multi-line
    # argument at its first newline.
    # A broken third-party pytest plugin on some machines (opik) crashes collection.
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    result = subprocess.run(cmd, cwd=ROOT, input=prompt, text=True, encoding="utf-8", env=env)
    sys.exit(result.returncode)


def replay(seed: int, profile: str = "catalog") -> dict:
    record = _run(seed, profile=profile)
    policy = [c for c in record["claims_sent"] if c["assertion"] == "policy"]
    print(f"seed {seed}: status {record['status']}, resolved_correctly "
          f"{record['audit']['resolved_correctly']}, escalated {bool(record['escalation'])}")
    print(f"trace {record['trace_id']}")
    print(f"cited rule: {policy[0]['value'] if policy else 'none'}")
    print(f"reply: {record['message']}")
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--profile", choices=["catalog", "stress"], default="catalog")
    d = sub.add_parser("decide")
    d.add_argument("escalation_id")
    d.add_argument("--decision", required=True)
    d.add_argument("--by", required=True)
    d.add_argument("--rule-id")
    d.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("replay")
    r.add_argument("--seed", type=int, required=True)
    r.add_argument("--profile", choices=["catalog", "stress"], default="catalog")
    args = parser.parse_args()
    if args.cmd == "pack":
        pack(args.seed, args.profile)
    elif args.cmd == "decide":
        decide(args.escalation_id, args.decision, args.by, args.rule_id, args.dry_run)
    else:
        replay(args.seed, args.profile)


if __name__ == "__main__":
    main()
