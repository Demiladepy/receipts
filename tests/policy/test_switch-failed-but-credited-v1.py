import copy
import json
from pathlib import Path

from policy import store

ROOT = Path(__file__).resolve().parents[2]
RULE_PATH = ROOT / "policy" / "rules" / "switch-failed-but-credited-v1.json"
PACK_PATH = ROOT / "policy" / "inbox" / "ESC-0021.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_rule_loads():
    rule = load_json(RULE_PATH)
    assert rule["rule_id"] == "switch-failed-but-credited-v1"
    assert rule["case_type"] == "switch_failed_but_credited"
    assert rule["decided_by"] == "Demiladepy"
    assert rule["source_case"] == {"escalation_id": "ESC-0021", "seed": 21,
                                   "trace_id": "d12137202386aec8ce79d8349350cfa8"}


def test_lookup_returns_rule():
    found = store.lookup("switch_failed_but_credited")
    assert found["found"] is True
    assert found["rule_id"] == "switch-failed-but-credited-v1"


def test_conditions_hold_on_pack_receipts():
    rule = load_json(RULE_PATH)
    pack = load_json(PACK_PATH)
    holds, why_not = store.conditions_hold(rule["conditions"], pack["receipts"])
    assert holds, why_not
    found = store.lookup("unknown", receipts=pack["receipts"])
    assert found["rule_id"] == "switch-failed-but-credited-v1"


def test_conditions_fail_when_beneficiary_not_credited():
    rule = load_json(RULE_PATH)
    receipts = copy.deepcopy(load_json(PACK_PATH)["receipts"])
    for r in receipts:
        if r["op"] == "beneficiary.get_credit":
            r["value"]["credited"] = False
            r["value"]["credit_at"] = None
    holds, _ = store.conditions_hold(rule["conditions"], receipts)
    assert not holds
