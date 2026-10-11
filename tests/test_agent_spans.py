"""Timeouts and connection errors end as failed tool spans. A lie stays a successful span."""

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from agent.loop import investigate
from agent.tracing import init_tracing
from sim.models import ChaosFlags
from tests.helpers import BY_SEED

EXPORTER = InMemorySpanExporter()
PROVIDER = TracerProvider()
PROVIDER.add_span_processor(SimpleSpanProcessor(EXPORTER))
init_tracing(
    disable_export=True,
    tracer_provider=PROVIDER,
    tags=["prompt:v1"],
    register_shutdown_handlers=False,
)


@pytest.fixture(autouse=True)
def _clear_spans():
    EXPORTER.clear()
    yield


def _finished():
    return list(EXPORTER.get_finished_spans())


def _status(name: str):
    matches = [span for span in _finished() if span.name == name]
    assert len(matches) == 1, [span.name for span in _finished()]
    return matches[0].status.status_code


def test_a_clean_case_nests_four_successful_tool_spans():
    result = investigate(BY_SEED[1])
    spans = _finished()
    agent = next(span for span in spans if span.name == "receipts.investigate")
    assert agent.status.status_code == StatusCode.OK
    assert agent.attributes.get("neatlogs.version") == "v1"
    tools = sorted(
        (span for span in spans if span.name in result.tool_order),
        key=lambda span: span.start_time,
    )
    assert [span.name for span in tools] == list(result.tool_order)
    assert all(span.status.status_code == StatusCode.OK for span in tools)
    assert all(span.parent is not None and span.parent.span_id == agent.context.span_id for span in tools)


def test_timeout_and_connection_error_are_failed_spans():
    investigate(BY_SEED[26])
    assert _status("switch.get_status") == StatusCode.ERROR
    assert _status("sender.get_debit") == StatusCode.OK
    assert _status("receipts.investigate") == StatusCode.OK

    EXPORTER.clear()
    investigate(BY_SEED[27])
    assert _status("beneficiary.get_credit") == StatusCode.ERROR
    assert _status("switch.get_status") == StatusCode.OK

    EXPORTER.clear()
    investigate(BY_SEED[30])
    assert _status("sender.get_debit") == StatusCode.ERROR
    assert _status("beneficiary.get_credit") == StatusCode.OK


def test_the_lying_reversal_span_succeeds_and_is_not_followed_by_another_debit_read():
    result = investigate(BY_SEED[28])
    assert result.outcome == "reversed"
    assert result.ledger_reversal_applied is False
    names = [span.name for span in sorted(_finished(), key=lambda span: span.start_time)]
    assert names.count("sender.get_debit") == 1
    assert names.count("sender.reverse") == 1
    assert _status("sender.reverse") == StatusCode.OK


def test_a_stale_switch_read_is_a_successful_span():
    investigate(BY_SEED[29])
    assert _status("switch.get_status") == StatusCode.OK


def test_a_reversal_timeout_is_a_failed_span():
    result = investigate(BY_SEED[9], chaos=ChaosFlags(timeout_ops=("sender.reverse",)))
    assert result.outcome == "incomplete"
    assert _status("sender.reverse") == StatusCode.ERROR
    assert _status("sender.get_debit") == StatusCode.OK
