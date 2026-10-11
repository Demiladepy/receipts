import copy
import json
from pathlib import Path

from policy import store

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "policy" / "rules" / "agreed-credit-v1.json"
PACK_PATH = ROOT / "policy" / "inbox" / "ESC-0002.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_rule_loads():
    rule = load_json(RULE_PATH)
    assert rule["rule_id"] == "agreed-credit-v1"
    assert rule["case_type"] == "switch_success_no_credit"
    assert rule["decided_by"] == "Demiladepy"
    assert rule["source_case"] == {"escalation_id": "ESC-0002", "seed": 2,
                                   "trace_id": "9aaad966f3d49a681adb31eea6f34fde"}


def test_lookup_returns_rule():
    found = store.lookup("switch_success_no_credit")
    assert found["found"] is True
    assert found["rule_id"] == "agreed-credit-v1"


def test_conditions_hold_on_pack_receipts():
    rule = load_json(RULE_PATH)
    pack = load_json(PACK_PATH)
    holds, why_not = store.conditions_hold(rule["conditions"], pack["receipts"])
    assert holds, why_not
    found = store.lookup("unknown", receipts=pack["receipts"])
    assert found["rule_id"] == "agreed-credit-v1"


def test_conditions_fail_when_switch_failed_and_beneficiary_not_credited():
    rule = load_json(RULE_PATH)
    receipts = copy.deepcopy(load_json(PACK_PATH)["receipts"])
    for r in receipts:
        if r["op"] == "switch.get_status" and r["ok"]:
            r["value"]["status"] = "failed"
        if r["op"] == "beneficiary.get_credit":
            r["value"]["credited"] = False
            r["value"]["credit_at"] = None
    holds, _ = store.conditions_hold(rule["conditions"], receipts)
    assert not holds
