"""Exact finite-horizon solver via enumeration + backward induction.

Eligible only when ``outcomes()`` is defined everywhere reachable and the
enumerated state space stays within ``state_limit``. Otherwise returns None
and the selector falls back to sampling solvers.
"""

from __future__ import annotations

import copy
import random

from saboragi.solve.types import OptionResult, SolveResult
from saboragi.wm.api import Model, State, canonical


def try_exact(
    model: Model,
    first_actions: list[str],
    *,
    state_limit: int = 200_000,
    seed: int = 0,
    p5_samples: int = 20_000,
) -> SolveResult | None:
    s0 = model.initial_state()
    states: dict[tuple[str, int], State] = {(canonical(s0), 0): copy.deepcopy(s0)}
    # (state_key, t, action) -> [(prob, next_key, reward)]
    edges: dict[tuple[str, int, str], list[tuple[float, str, float]]] = {}
    frontier = [(canonical(s0), 0)]
    while frontier:
        key, t = frontier.pop()
        state = states[(key, t)]
        if model.is_terminal(state, t):
            continue
        for action in model.actions(copy.deepcopy(state)):
            dist = model.outcomes(copy.deepcopy(state), action)
            if dist is None:
                return None  # sampling-only region: not exactly solvable
            nxt_edges = []
            for prob, nxt in dist:
                nkey = canonical(nxt)
                nstate = (nkey, t + 1)
                if nstate not in states:
                    if len(states) >= state_limit:
                        return None
                    states[nstate] = copy.deepcopy(nxt)
                    frontier.append(nstate)
                reward = model.reward(state, action, nxt)
                nxt_edges.append((prob, nkey, reward))
            edges[(key, t, action)] = nxt_edges

    event_names = list(model.events)
    value: dict[tuple[str, int], float] = {}
    policy: dict[tuple[str, int], str] = {}
    event_prob: dict[str, dict[tuple[str, int], float]] = {name: {} for name in event_names}

    def state_event(name: str, state: State) -> float:
        return float(model.events[name](copy.deepcopy(state)))

    # Backward induction from the horizon down (t+1 always processed first).
    for key, t in sorted(states, key=lambda kt: -kt[1]):
        state = states[(key, t)]
        if model.is_terminal(state, t):
            value[(key, t)] = 0.0
            for name in event_names:
                event_prob[name][(key, t)] = min(1.0, max(0.0, state_event(name, state)))
            continue
        best_v, best_a = float("-inf"), None
        for action in model.actions(copy.deepcopy(state)):
            q = sum(p * (r + value[(nk, t + 1)]) for p, nk, r in edges[(key, t, action)])
            if q > best_v:
                best_v, best_a = q, action
        value[(key, t)] = best_v
        policy[(key, t)] = best_a  # type: ignore[assignment]
        for name in event_names:
            if state_event(name, state) >= 1.0:
                event_prob[name][(key, t)] = 1.0
            else:
                action = best_a
                event_prob[name][(key, t)] = sum(
                    p * event_prob[name][(nk, t + 1)] for p, nk, _ in edges[(key, t, action)]
                )

    root = (canonical(s0), 0)
    options = []
    for action in first_actions:
        q = sum(p * (r + value[(nk, 1)]) for p, nk, r in edges[(*root, action)])
        probs = {}
        for name in event_names:
            if state_event(name, s0) >= 1.0:
                probs[name] = 1.0
            else:
                probs[name] = sum(
                    p * event_prob[name][(nk, 1)] for p, nk, _ in edges[(*root, action)]
                )
        options.append(
            OptionResult(action=action, ev=q, ci_lo=q, ci_hi=q, p_events=probs, n=len(states))
        )

    # 5th percentile of total return under the optimal policy, via sampling.
    rng = random.Random(seed)
    if p5_samples > 0:
        for opt in options:
            returns = [
                _rollout_optimal(model, s0, opt.action, policy, random.Random(rng.random()))
                for _ in range(p5_samples)
            ]
            returns.sort()
            opt.worst_case_p5 = returns[max(0, int(0.05 * len(returns)) - 1)]

    best = max(options, key=lambda o: o.ev).action
    return SolveResult(
        options=options,
        best=best,
        solver="exact",
        exact=True,
        diagnostics={"states_enumerated": len(states), "p5_samples": p5_samples},
    )


def _rollout_optimal(
    model: Model, s0: State, first_action: str, policy: dict, rng: random.Random
) -> float:
    from saboragi.wm.api import canonical as _canonical

    state = copy.deepcopy(s0)
    total, t, action = 0.0, 0, first_action
    while not model.is_terminal(state, t):
        nxt = model.transition(copy.deepcopy(state), action, rng)
        total += model.reward(state, action, nxt)
        state, t = nxt, t + 1
        if model.is_terminal(state, t):
            break
        action = policy[(_canonical(state), t)]
    return total
