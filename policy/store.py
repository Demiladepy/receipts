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


def lookup(case_type: str, rules_dir: Path = RULES_DIR, receipts: list[dict] | None = None) -> dict:
    """Find the committed rule for this case.

    With receipts, a rule applies when its conditions hold on the latest reads, whatever
    the model called the case; the model's case_type is only a fallback. Without
    receipts (tests, the CLI), match by case_type."""
    from policy import license

    rules = load_rules(rules_dir)
    if receipts is not None:
        matches = [r for r in rules if r.get("conditions") and conditions_hold(r["conditions"], receipts)[0]]
    else:
        matches = [r for r in rules if r.get("case_type") == case_type]
    revoked = [r for r in matches if not license.is_active(r["rule_id"])]
    matches = [r for r in matches if license.is_active(r["rule_id"])]
    if revoked and not matches:
        last = license.state(revoked[-1]["rule_id"])
        return {"found": False, "case_type": case_type, "revoked_rule": revoked[-1]["rule_id"],
                "note": f"Rule {revoked[-1]['rule_id']} has lost its license ({last.get('reason', '')}). "
                        "Do not apply it. Escalate this case to a human."}
    if not matches:
        return {"found": False, "case_type": case_type,
                "note": "No committed rule. If you cannot resolve this on the evidence, escalate."}
    rule = matches[-1]
    return {"found": True, **{k: rule[k] for k in ("rule_id", "case_type", "decision", "instructions",
                                                    "customer_line", "conditions", "decided_by",
                                                    "source_case")
                              if k in rule}}


def conditions_hold(conditions: list[dict], receipts: list[dict]) -> tuple[bool, str | None]:
    """Check a rule's conditions against the latest successful read of each source.

    A condition is {"op": "switch.get_status", "field": "status", "equals": "failed"}.
    Returns (holds, why_not)."""
    latest: dict[str, dict] = {}
    for r in receipts:
        if r.get("ok") and r.get("value") is not None:
            latest[r["op"]] = r["value"]
    for cond in conditions:
        value = latest.get(cond["op"])
        if value is None:
            return False, f"no successful {cond['op']} read to check {cond['field']}"
        if value.get(cond["field"]) != cond["equals"]:
            return False, (f"{cond['op']} says {cond['field']}={value.get(cond['field'])!r}, "
                           f"the rule needs {cond['equals']!r}")
    return True, None
