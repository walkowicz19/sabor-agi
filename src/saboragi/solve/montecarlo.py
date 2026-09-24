"""Monte Carlo evaluation of one-shot (or fixed) choices with confidence intervals."""

from __future__ import annotations

import copy
import math
import random

from saboragi.solve.types import OptionResult, SolveResult
from saboragi.wm.api import Model, State

Z95 = 1.96


def _ci_width(sum_x: float, sum_x2: float, n: int) -> float:
    if n < 2:
        return float("inf")
    var = max(0.0, sum_x2 / n - (sum_x / n) ** 2)
    return Z95 * math.sqrt(var / n)


def _percentile(sorted_xs: list[float], q: float) -> float:
    if not sorted_xs:
        return 0.0
    idx = min(len(sorted_xs) - 1, max(0, int(q * len(sorted_xs))))
    return sorted_xs[idx]


def rollout(
    model: Model,
    state: State,
    first_action: str,
    rng: random.Random,
    event_names: list[str],
) -> tuple[float, dict[str, bool]]:
    """One episode; returns (total reward, events fired at least once)."""
    total = 0.0
    fired = {name: False for name in event_names}
    for name in event_names:
        if model.events[name](copy.deepcopy(state)):
            fired[name] = True
    t, action = 0, first_action
    current = copy.deepcopy(state)
    while not model.is_terminal(current, t):
        actions = model.actions(copy.deepcopy(current))
        if action not in actions:
            policy_action = model.default_policy(copy.deepcopy(current), rng)
            action = policy_action if policy_action in actions else rng.choice(actions)
        nxt = model.transition(copy.deepcopy(current), action, rng)
        total += model.reward(current, action, nxt)
        current, t = nxt, t + 1
        for name in event_names:
            if model.events[name](copy.deepcopy(current)):
                fired[name] = True
        action = ""  # subsequent steps follow the rollout policy
    return total, fired


def monte_carlo(
    model: Model,
    first_actions: list[str],
    *,
    n_rollouts: int = 2000,
    batch: int = 200,
    seed: int = 0,
    min_per_action: int = 500,
) -> SolveResult:
    s0 = model.initial_state()
    event_names = list(model.events)
    rng = random.Random(seed)
    sums = {a: 0.0 for a in first_actions}
    sumsq = {a: 0.0 for a in first_actions}
    counts = {a: 0 for a in first_actions}
    event_hits = {a: {e: 0 for e in event_names} for a in first_actions}
    returns: dict[str, list[float]] = {a: [] for a in first_actions}

    done = 0
    while done < n_rollouts:
        for action in first_actions:
            if done >= n_rollouts:
                break
            total, fired = rollout(model, s0, action, random.Random(rng.random()), event_names)
            sums[action] += total
            sumsq[action] += total * total
            counts[action] += 1
            returns[action].append(total)
            for name in event_names:
                event_hits[action][name] += bool(fired[name])
            done += 1
        if (
            done >= batch
            and all(counts[a] >= min_per_action for a in first_actions)
            and _separated(sums, sumsq, counts)
        ):
            break

    options = []
    for action in first_actions:
        n = counts[action]
        mean = sums[action] / n
        half = _ci_width(sums[action], sumsq[action], n)
        ordered = sorted(returns[action])
        options.append(
            OptionResult(
                action=action,
                ev=mean,
                ci_lo=mean - half,
                ci_hi=mean + half,
                p_events={e: event_hits[action][e] / n for e in event_names},
                worst_case_p5=_percentile(ordered, 0.05),
                n=n,
            )
        )
    best = max(options, key=lambda o: o.ev).action
    return SolveResult(
        options=options,
        best=best,
        solver="montecarlo",
        exact=False,
        diagnostics={"rollouts": done, "budget": n_rollouts},
    )


def _separated(sums: dict[str, float], sumsq: dict[str, float], counts: dict[str, int]) -> bool:
    """Early stop when the leader's CI no longer overlaps any rival's."""
    means = {a: sums[a] / counts[a] for a in sums}
    leader = max(means, key=lambda a: means[a])
    lo = means[leader] - _ci_width(sums[leader], sumsq[leader], counts[leader])
    for action, mean in means.items():
        if action == leader:
            continue
        hi = mean + _ci_width(sums[action], sumsq[action], counts[action])
        if hi >= lo:
            return False
    return True
