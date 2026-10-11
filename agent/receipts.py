"""Every tool call leaves a receipt. A receipt id is the neatlogs span id of that call."""

from dataclasses import dataclass, field

from opentelemetry import trace

WRITE_OPS = ("sender.reverse",)


@dataclass(frozen=True, slots=True)
class Receipt:
    receipt_id: str
    seq: int
    op: str
    args: dict
    ok: bool
    value: dict | None
    error: str | None

    @property
    def is_write(self) -> bool:
        return self.op in WRITE_OPS

    def as_tool_result(self) -> dict:
        body: dict = {"receipt_id": self.receipt_id, "op": self.op, "ok": self.ok}
        if self.ok:
            body["result"] = self.value
        else:
            body["error"] = self.error
        return body

    def as_json(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "seq": self.seq,
            "op": self.op,
            "args": self.args,
            "ok": self.ok,
            "value": self.value,
            "error": self.error,
        }


@dataclass(slots=True)
class ReceiptBook:
    receipts: list[Receipt] = field(default_factory=list)

    def record(self, op: str, args: dict, ok: bool, value: dict | None, error: str | None) -> Receipt:
        seq = len(self.receipts) + 1
        receipt = Receipt(
            receipt_id=current_span_id() or f"R{seq}",
            seq=seq,
            op=op,
            args=args,
            ok=ok,
            value=value,
            error=error,
        )
        self.receipts.append(receipt)
        return receipt

    def get(self, receipt_id: str) -> Receipt | None:
        for receipt in self.receipts:
            if receipt.receipt_id == receipt_id:
                return receipt
        return None

    def last_write_seq(self, before: int | None = None) -> int:
        """Sequence number of the last successful write, optionally before a given seq."""
        last = 0
        for receipt in self.receipts:
            if before is not None and receipt.seq >= before:
                break
            if receipt.is_write and receipt.ok:
                last = receipt.seq
        return last


def _active_span_context():
    """neatlogs keeps its active span on a private context key (it never takes over the
    global OTel current span), so ask neatlogs first and fall back to plain OTel."""
    try:
        from neatlogs._wrap_utils import _current_neatlogs_parent

        span = _current_neatlogs_parent()
    except Exception:
        span = None
    if span is None:
        span = trace.get_current_span()
    context = span.get_span_context()
    return context if context.is_valid else None


def current_span_id() -> str | None:
    context = _active_span_context()
    return format(context.span_id, "016x") if context else None


def current_trace_id() -> str | None:
    context = _active_span_context()
    return format(context.trace_id, "032x") if context else None
