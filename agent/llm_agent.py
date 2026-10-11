"""Model-driven complaint agent.

The model plans and picks tools. Every tool call runs inside its own neatlogs TOOL span
and leaves a receipt whose id is that span's id, so each claim in a reply points at a
span a judge can open. v1 sends whatever the model writes (the verifier runs in shadow
so we can count what it would have blocked). v2 only sends a reply the verifier allows;
a blocked reply goes back to the model with the reasons.
"""

import json
import time
from dataclasses import dataclass, field

import neatlogs

from agent.llm import Usage, complete, make_client, model_name
from agent.llm_prompts import system_prompt
from agent.receipts import ReceiptBook, current_trace_id
from agent.truth import audit
from policy import store
from sim.constants import ESCALATION_LIMIT_KOBO
from sim.errors import SimError
from sim.models import ChaosFlags, Scenario
from sim.world import World, open_world
from verifier.assertions import ASSERTIONS, Claim, verify_reply

MAX_STEPS = 24
MAX_BLOCKS = 3

TOOL_OPS = {
    "sender_get_debit": "sender.get_debit",
    "sender_get_balance": "sender.get_balance",
    "switch_get_status": "switch.get_status",
    "beneficiary_get_credit": "beneficiary.get_credit",
    "sender_reverse": "sender.reverse",
    "escalate": "case.escalate",
    "policy_lookup": "policy.lookup",
}


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required,
                           "additionalProperties": False},
        },
    }


_TRANSFER = {"transfer_id": {"type": "string", "description": "Transfer reference, e.g. TXN-0001"}}


def tool_specs(version: str) -> list[dict]:
    specs = [
        _fn("sender_get_debit", "Sender bank ledger: the debit for a transfer, and whether a reversal "
            "has been applied.", _TRANSFER, ["transfer_id"]),
        _fn("sender_get_balance", "Sender bank ledger: current balance of the sender account.",
            {"account": {"type": "string"}}, ["account"]),
        _fn("switch_get_status", "Payment switch: status of the transfer instruction "
            "(success, failed or pending).", _TRANSFER, ["transfer_id"]),
        _fn("beneficiary_get_credit", "Beneficiary bank: whether the credit posted to the "
            "beneficiary account.", _TRANSFER, ["transfer_id"]),
        _fn("sender_reverse", "Sender bank: reverse the debit back to the customer. This moves money.",
            _TRANSFER, ["transfer_id"]),
        _fn("escalate", "Hand the case to a human with the evidence gathered so far.",
            {"reason": {"type": "string"},
             "case_type": {"type": "string", "enum": list(store.CASE_TYPES)}},
            ["reason", "case_type"]),
        _fn("send_reply", "Send the final reply to the customer. The reply is the claims, in order, "
            "followed by next_step.",
            {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "assertion": {"type": "string", "enum": list(ASSERTIONS)},
                            "receipt_id": {"type": "string",
                                           "description": "receipt_id of the tool result this rests on"},
                            "value": {"type": ["string", "integer", "null"],
                                      "description": "for amount/balance (kobo), switch_status, "
                                                     "tool_failed (error code), policy (rule_id)"},
                            "text": {"type": "string", "description": "the sentence the customer reads"},
                        },
                        "required": ["assertion", "receipt_id", "value", "text"],
                        "additionalProperties": False,
                    },
                },
                "next_step": {"type": "string",
                              "description": "what happens next, with no new facts, amounts or dates"},
            },
            ["claims", "next_step"]),
    ]
    if version in ("v2", "v3"):
        specs.insert(5, _fn("policy_lookup", "Committed policy rules for a case type. Check before acting.",
                            {"case_type": {"type": "string", "enum": list(store.CASE_TYPES)}},
                            ["case_type"]))
    return specs


def _traced(op: str):
    @neatlogs.span(kind="TOOL", name=op, tool_name=op, capture_input=False)
    def run(case: "Case", args: dict) -> dict:
        return case.execute(op, args)

    return run


_RUNNERS = {op: _traced(op) for op in TOOL_OPS.values()}


@dataclass
class Case:
    scenario: Scenario
    world: World
    version: str
    book: ReceiptBook = field(default_factory=ReceiptBook)
    attempts: list[dict] = field(default_factory=list)
    escalation: dict | None = None
    status: str = "open"
    message: str | None = None
    sent_claims: list[dict] = field(default_factory=list)
    shadow_verdict: dict | None = None
    blocks: int = 0

    # Tools -----------------------------------------------------------------

    def execute(self, op: str, args: dict) -> dict:
        if op == "sender.reverse" and self.version == "v3":
            refusal = reversal_refusal(self.book)
            if refusal:
                receipt = self.book.record(op, args, False, None, "refused_by_guard")
                return {**receipt.as_tool_result(), "reason": refusal}
        try:
            value = self._dispatch(op, args)
        except SimError as exc:
            return self.book.record(op, args, False, None, exc.code).as_tool_result()
        return self.book.record(op, args, True, value, None).as_tool_result()

    def _dispatch(self, op: str, args: dict) -> dict:
        w = self.world
        if op == "sender.get_debit":
            return w.get_debit(args.get("transfer_id"))
        if op == "sender.get_balance":
            return w.get_balance(args.get("account"))
        if op == "switch.get_status":
            return w.get_switch_status(args.get("transfer_id"))
        if op == "beneficiary.get_credit":
            return w.get_credit(args.get("transfer_id"))
        if op == "sender.reverse":
            return w.reverse(args.get("transfer_id"))
        if op == "policy.lookup":
            return store.lookup(str(args.get("case_type", "unknown")))
        if op == "case.escalate":
            self.escalation = self._evidence_pack(args)
            return {"escalation_id": self.escalation["escalation_id"], "status": "queued"}
        raise ValueError(op)

    def _evidence_pack(self, args: dict) -> dict:
        return {
            "escalation_id": f"ESC-{self.scenario.seed:04d}",
            "complaint_id": self.scenario.complaint_id,
            "case_type": args.get("case_type", "unknown"),
            "reason": args.get("reason", ""),
            "narrative": self.scenario.narrative,
            "receipts": [r.as_json() for r in self.book.receipts],
        }

    # Reply -----------------------------------------------------------------

    @neatlogs.span(kind="CHAIN", name="verifier.check", capture_input=False)
    def reply(self, args: dict) -> dict:
        claims = [Claim.from_json(c) for c in args.get("claims") or [] if isinstance(c, dict)]
        next_step = str(args.get("next_step") or "")
        verdict = verify_reply(claims, next_step, self.book)
        self.attempts.append({"claims": [c.as_json() for c in claims], "next_step": next_step,
                              "verdict": verdict.as_json()})
        if self.version == "v1" or verdict.allowed:
            self._send(claims, next_step)
            if self.version == "v1":
                self.shadow_verdict = verdict.as_json()
            return {"status": "sent", "verdict": "allowed" if verdict.allowed else "not checked"}
        self.blocks += 1
        if self.blocks >= MAX_BLOCKS:
            self.status = "withheld"
            if self.escalation is None:
                self.escalation = self._evidence_pack({"reason": "reply could not be proved",
                                                       "case_type": "unknown"})
            return {"status": "withheld", "reasons": verdict.reasons,
                    "note": "Reply withheld. The case went to a human with the receipts."}
        return {"status": "blocked", "reasons": verdict.reasons,
                "attempts_left": MAX_BLOCKS - self.blocks}

    def _send(self, claims: list[Claim], next_step: str) -> None:
        self.status = "sent"
        self.message = " ".join([c.text.strip() for c in claims] + [next_step.strip()]).strip()
        for c in claims:
            receipt = self.book.get(c.receipt_id)
            self.sent_claims.append({**c.as_json(), "receipt_ok": receipt.ok if receipt else None})

    @property
    def done(self) -> bool:
        return self.status in ("sent", "withheld")


def reversal_refusal(book: ReceiptBook) -> str | None:
    """Money only moves on receipts: the latest reads must show the debit open, the switch
    failed and the beneficiary not credited. Returns why not, or None."""
    latest: dict[str, dict] = {}
    for r in book.receipts:
        if r.ok and r.value is not None:
            latest[r.op] = r.value
    debit = latest.get("sender.get_debit")
    switch = latest.get("switch.get_status")
    credit = latest.get("beneficiary.get_credit")
    if debit is not None and (not debit.get("debited") or debit.get("reversal_applied")):
        return "the ledger does not show an open debit to reverse"
    amounts = [v.get("amount_kobo") for v in (debit, switch, credit) if v and v.get("amount_kobo")]
    if any(a > ESCALATION_LIMIT_KOBO for a in amounts):
        return "the amount is over the NGN 1,000,000.00 limit; a human decides. Escalate"
    if switch is not None and switch.get("status") != "failed":
        return (f"the switch says {switch.get('status')}, not failed. Only a failed transfer with "
                "no credit is reversed; anything else is escalated")
    if credit is not None and credit.get("credited") is not False:
        return "the beneficiary bank shows the credit posted; reversing would pay twice. Escalate"
    missing = [name for name, read in (("sender_get_debit", debit), ("switch_get_status", switch),
                                       ("beneficiary_get_credit", credit)) if read is None]
    if missing:
        return "no successful read yet from " + ", ".join(missing) + ". Read it, or escalate"
    return None


def _complaint_message(scenario: Scenario) -> str:
    return (f"Complaint {scenario.complaint_id} from {scenario.customer_name}, received "
            f"{scenario.complained_at}:\n\n{scenario.narrative}")


def run_case(scenario: Scenario, version: str, *, chaos: ChaosFlags | None = None, client=None) -> dict:
    runner = {"v1": _run_v1, "v2": _run_v2, "v3": _run_v3}[version]
    return runner(scenario, chaos, client or make_client())


@neatlogs.span(kind="AGENT", name="receipts.case", version="v1", tags=["prompt:v1"],
               capture_input=False, capture_output=False)
def _run_v1(scenario: Scenario, chaos: ChaosFlags | None, client) -> dict:
    return _loop(scenario, "v1", chaos, client)


@neatlogs.span(kind="AGENT", name="receipts.case", version="v2", tags=["prompt:v2"],
               capture_input=False, capture_output=False)
def _run_v2(scenario: Scenario, chaos: ChaosFlags | None, client) -> dict:
    return _loop(scenario, "v2", chaos, client)


@neatlogs.span(kind="AGENT", name="receipts.case", version="v3", tags=["prompt:v3"],
               capture_input=False, capture_output=False)
def _run_v3(scenario: Scenario, chaos: ChaosFlags | None, client) -> dict:
    return _loop(scenario, "v3", chaos, client)


def _loop(scenario: Scenario, version: str, chaos: ChaosFlags | None, client) -> dict:
    started = time.monotonic()
    world = open_world(scenario, chaos=chaos)
    case = Case(scenario, world, version)
    usage = Usage()
    tools = tool_specs(version)
    messages: list[dict] = [
        {"role": "system", "content": system_prompt(version)},
        {"role": "user", "content": _complaint_message(scenario)},
    ]
    transcript: list[dict] = []
    for _ in range(MAX_STEPS):
        response = complete(client, messages, tools)
        usage.add(response.usage)
        msg = response.choices[0].message
        calls = msg.tool_calls or []
        messages.append({
            "role": "assistant",
            "content": msg.content,
            **({"tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.function.name, "arguments": c.function.arguments}}
                               for c in calls]} if calls else {}),
        })
        if msg.content:
            transcript.append({"model": msg.content})
        if not calls:
            messages.append({"role": "user", "content": "Finish by calling send_reply."})
            continue
        for call in calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "send_reply":
                result = case.reply(args)
            elif name in TOOL_OPS and (name != "policy_lookup" or version != "v1"):
                result = _RUNNERS[TOOL_OPS[name]](case, args)
            else:
                result = {"ok": False, "error": f"unknown tool {name}"}
            transcript.append({"tool": name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        if case.done:
            break
    if not case.done:
        case.status = "no_reply"
    ops = [r.op for r in case.book.receipts]
    graded = audit(
        scenario, world,
        sent_claims=case.sent_claims,
        reversed_called=any(r.op == "sender.reverse" and r.ok for r in case.book.receipts),
        escalated=case.escalation is not None,
        reply_sent=case.status == "sent",
        policy_cited=any(c["assertion"] == "policy" for c in case.sent_claims),
        receipts=[r.as_json() for r in case.book.receipts],
    )
    final_verdict = case.attempts[-1]["verdict"] if case.attempts else None
    return {
        "seed": scenario.seed,
        "complaint_id": scenario.complaint_id,
        "pattern": scenario.pattern,
        "version": version,
        "model": model_name(),
        "trace_id": current_trace_id(),
        "status": case.status,
        "message": case.message,
        "claims_sent": case.sent_claims,
        "unproven_claims_sent": (sum(1 for c in (final_verdict or {}).get("claims", []) if not c["proved"])
                                 if case.status == "sent" else 0),
        "attempts": case.attempts,
        "blocks": case.blocks,
        "escalation": case.escalation,
        "receipts": [r.as_json() for r in case.book.receipts],
        "tool_order": ops,
        "transcript": transcript,
        "audit": graded.as_json(),
        "usage": usage.as_json(),
        "latency_s": round(time.monotonic() - started, 2),
    }
