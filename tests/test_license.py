"""A rule loses its license on a detection and only a person restores it."""

from policy import license


def run(rule="agreed-credit-v1", false=(), harmful=False, seed=3):
    return {"seed": seed, "trace_id": f"t{seed}",
            "claims_sent": [{"assertion": "policy", "value": rule}],
            "audit": {"false_claims": list(false), "harmful_action": harmful}}


def test_clean_runs_keep_the_license(tmp_path):
    log = tmp_path / "l.jsonl"
    assert license.check([run(), run(seed=4)], log) == []
    assert license.is_active("agreed-credit-v1", log)


def test_a_detection_revokes_and_a_person_restores(tmp_path):
    log = tmp_path / "l.jsonl"
    assert license.check([run(), run(false=["credited=None: it was credited"], seed=9)], log) == ["agreed-credit-v1"]
    assert not license.is_active("agreed-credit-v1", log)
    assert license.state("agreed-credit-v1", log)["trace_id"] == "t9"
    assert license.check([run(harmful=True)], log) == []  # already revoked, not revoked twice
    license.restore("agreed-credit-v1", "Demiladepy", "reviewed seed 9", log)
    assert license.is_active("agreed-credit-v1", log)


def test_lookup_refuses_a_revoked_rule(tmp_path, monkeypatch):
    from policy import store

    log = tmp_path / "l.jsonl"
    monkeypatch.setattr(license, "LOG", log)
    monkeypatch.setattr(license.is_active, "__defaults__", (log,))
    monkeypatch.setattr(license.state, "__defaults__", (log,))
    receipts = [
        {"op": "sender.get_debit", "ok": True, "value": {"debited": True, "reversal_applied": False}},
        {"op": "switch.get_status", "ok": True, "value": {"status": "success"}},
        {"op": "beneficiary.get_credit", "ok": True, "value": {"credited": True}},
    ]
    assert store.lookup("credited", receipts=receipts)["found"] is True
    license.check([run(false=["x"])], log)
    result = store.lookup("credited", receipts=receipts)
    assert result["found"] is False and result["revoked_rule"] == "agreed-credit-v1"
