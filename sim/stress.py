"""A harder chaos profile over the same 30 seeds, derived only from the seed.

The catalog keeps its own light chaos. Stress adds faults a careless agent trips on:
first-call timeouts it should retry, reversals that report success and do not post,
and a switch whose first read is stale. Same seed, same faults, every run.
"""

import random
from dataclasses import replace

from sim.constants import READ_OPS
from sim.models import ChaosFlags, Scenario


def stress_flags(scenario: Scenario) -> ChaosFlags:
    rng = random.Random(f"stress:{scenario.seed}")
    base = scenario.chaos
    flaky = tuple(op for op in READ_OPS if rng.random() < 0.18 and op not in base.timeout_ops)
    lying = base.lying_reversal or (scenario.pattern == "failed_unreversed" and rng.random() < 0.5)
    stale = base.stale_switch_status
    if stale is None and scenario.facts.switch_status != "pending" and rng.random() < 0.25:
        stale = "pending"
    return replace(base, flaky_ops=flaky, lying_reversal=lying, stale_switch_status=stale)


def stressed(scenario: Scenario) -> Scenario:
    return replace(scenario, chaos=stress_flags(scenario))
