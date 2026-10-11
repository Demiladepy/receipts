"""A reply can be sent only when each claim matches a span, and ledger claims are fresh."""

from dataclasses import dataclass

from agent.result import AgentResult
from verifier.claims import Claim, claims_for, spans_of


@dataclass(frozen=True, slots=True)
class ClaimCheck:
    claim: Claim
    proved: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class Verdict:
    allowed: bool
    checks: tuple[ClaimCheck, ...]

    @property
    def blocks(self) -> tuple[str, ...]:
        return tuple(check.reason for check in self.checks if check.reason)


def verify(result: AgentResult) -> Verdict:
    claims = claims_for(result)
    if not claims:
        reason = "The reply makes no claim a span can prove."
        return Verdict(False, (ClaimCheck(Claim("empty", reason, "", None, False), False, reason),))
    checks = tuple(_check(result, claim) for claim in claims)
    return Verdict(all(check.proved for check in checks), checks)


def _check(result: AgentResult, claim: Claim) -> ClaimCheck:
    read = _match(result, claim)
    if read is None:
        return ClaimCheck(claim, False, "No span supports it.")
    if claim.ledger and claim.op == "sender.reverse":
        return ClaimCheck(
            claim,
            False,
            f"{claim.op} reported success, and that is not a ledger read.",
        )
    action_at = _action_at(result)
    if (
        claim.ledger
        and action_at
        and claim.op in ("sender.get_debit", "sender.get_balance")
        and (claim.read_at or "") <= action_at
    ):
        return ClaimCheck(
            claim,
            False,
            (
                f"The read at {claim.read_at} is not after "
                f"the reversal at {action_at}."
            ),
        )
    return ClaimCheck(claim, True, None)


def _match(result: AgentResult, claim: Claim):
    for read in spans_of(result):
        if read.op != claim.op:
            continue
        if claim.error is not None:
            if not read.ok and read.error == claim.error:
                return read
            continue
        if not read.ok or read.value is None:
            continue
        if read.value.get("read_at") != claim.read_at:
            continue
        if all(read.value.get(key) == expected for key, expected in claim.expect):
            return read
    return None


def _action_at(result: AgentResult) -> str | None:
    if result.reversal is None or not result.reversal.ok or result.reversal.value is None:
        return None
    read_at = result.reversal.value.get("read_at")
    return read_at if isinstance(read_at, str) else None
