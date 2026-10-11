"""The demo payload is the complaint, both replies, and the receipt verdicts."""

from webapp import case_payload, page_html, scenario_index


def test_index_lists_every_seed():
    rows = scenario_index()
    assert [row["seed"] for row in rows] == list(range(1, 31))
    assert rows[27]["chaos"] == ["reversal reports success without posting"]


def test_case_file_for_the_lying_reversal():
    payload = case_payload(28)
    assert payload is not None
    assert payload["transfer_id"] == "TXN-0028"
    assert payload["v1"]["allowed"] is False
    assert payload["v2"]["allowed"] is True
    assert payload["v2"]["ledger_reversal_applied"] is False
    assert "still shows the debit open" in payload["v2"]["reply"]
    assert payload["same_reply"] is False


def test_honest_reversal_keeps_the_sentence_and_adds_the_receipt():
    payload = case_payload(9)
    assert payload is not None
    assert payload["v1"]["allowed"] is False
    assert payload["v2"]["allowed"] is True
    assert payload["v1"]["reply"] == payload["v2"]["reply"]
    assert payload["v2"]["ledger_reversal_applied"] is True
    assert payload["same_reply"] is False


def test_missing_seed_is_absent():
    assert case_payload(0) is None
    assert case_payload(31) is None


def test_page_is_a_case_file():
    html = page_html()
    assert "Receipts" in html
    assert 'id="seeds"' in html
    assert "/api/runs/" in html
    assert "Four rules" in html
    assert "cfo.ai" in html
    assert "Open the model" in html


def test_recorded_runs_payloads():
    import webapp_runs

    summary = webapp_runs.summary()
    assert set(summary) == {"v1", "v2", "v3"}
    case = webapp_runs.case(28, rep=1)
    assert set(case["runs"]) == {"v1", "v2", "v3"}
    v3 = case["runs"]["v3"]
    assert v3["trace_id"] and v3["steps"] and v3["attempts"]
    assert webapp_runs.case(99) is None
