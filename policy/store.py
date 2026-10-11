"""Committed policy rules. Each rule is one JSON file a human decision produced.

Rules live in policy/rules/*.json and are read fresh on every lookup, so a rule
committed by the ask-once loop applies to the very next case.
"""

import json
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parent / "rules"

CASE_TYPES = (
    "credited",
    "failed_unreversed",
    "failed_reversed",
    "switch_success_no_credit",
    "switch_failed_but_credited",
    "over_limit",
    "reversal_not_posted",
    "pending",
    "unknown",
)


def load_rules(rules_dir: Path = RULES_DIR) -> list[dict]:
    rules = []
    for path in sorted(rules_dir.glob("*.json")):
        rule = json.loads(path.read_text(encoding="utf-8"))
        rule["file"] = path.name
        rules.append(rule)
    return rules


def lookup(case_type: str, rules_dir: Path = RULES_DIR) -> dict:
    matches = [r for r in load_rules(rules_dir) if r.get("case_type") == case_type]
    if not matches:
        return {"found": False, "case_type": case_type,
                "note": "No committed rule. If you cannot resolve this on the evidence, escalate."}
    rule = matches[-1]
    return {"found": True, **{k: rule[k] for k in ("rule_id", "case_type", "decision", "instructions",
                                                    "customer_line", "decided_by", "source_case")
                              if k in rule}}
