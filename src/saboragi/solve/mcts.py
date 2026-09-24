"""MCTS (UCT) with chance nodes for sequential stochastic problems.

No LLM calls happen here: tree policy is UCT, chance outcomes are sampled from
``transition()``, and leaf evaluation is random rollouts. Returns root-action
values with confidence intervals from visit statistics.
"""

from __future__ import annotations

import copy
import math
import random

from saboragi.solve.montecarlo import _percentile
from saboragi.solve.types import OptionResult, SolveResult
from saboragi.wm.api import Model, State, canonical


class _Scale:
    """Dynamic reward range so UCT exploration works at any reward scale."""

    def __init__(self) -> None:
        self.lo = float("inf")
        self.hi = float("-inf")

    def update(self, x: float) -> None:
        self.lo = min(self.lo, x)
        self.hi = max(self.hi, x)

    def norm(self, x: float) -> float:
        if self.hi <= self.lo:
            return 0.5
        return (x - self.lo) / (self.hi - self.lo)


class _Chance:
    __slots__ = ("action", "visits", "total", "outcomes")

    def __init__(self, action: str):
        self.action = action
        self.visits = 0
        self.total = 0.0
        self.outcomes: list[tuple[State, float]] = []  # (next_state, reward)

    @property
    def mean(self) -> float:
        return self.total / self.visits if self.visits else 0.0


class _Node:
    __slots__ = ("state", "t", "visits", "total", "children", "untried")

    def __init__(self, state: State, t: int, actions: list[str]):
        self.state = state
        self.t = t
        self.visits = 0
        self.total = 0.0
        self.children: dict[str, _Chance] = {}
        self.untried = list(actions)

    @property
    def mean(self) -> float:
        return self.total / self.visits if self.visits else 0.0


def mcts(
    model: Model,
    first_actions: list[str],
    *,
    iterations: int = 20_000,
    seed: int = 0,
    c: float = 1.414,
    widen_c: float = 1.0,
    widen_alpha: float = 0.5,
    eval_rollouts: int = 3_000,
) -> SolveResult:
    s0 = model.initial_state()
    event_names = list(model.events)
    rng = random.Random(seed)
    root = _Node(copy.deepcopy(s0), 0, list(first_actions))
    tree: dict[tuple[str, int], _Node] = {(canonical(s0), 0): root}
    scale = _Scale()
    root_returns: dict[str, list[float]] = {a: [] for a in first_actions}
    root_events: dict[str, dict[str, int]] = {a: {e: 0 for e in event_names} for a in first_actions}
    root_counts = {a: 0 for a in first_actions}

    for _ in range(iterations):
        _simulate(
            model,
            root,
            tree,
            rng,
            c,
            widen_c,
            widen_alpha,
            root_returns,
            root_events,
            root_counts,
            event_names,
            scale,
        )

    # The tree-search averages above mix exploratory play, so they are biased
    # low. Extract the greedy policy (most-visited action = the search's
    # converged choice) and re-evaluate each root action with fresh rollouts
    # for honest estimates and confidence intervals.
    policy = {
        key: max(node.children, key=lambda a: node.children[a].visits)
        for key, node in tree.items()
        if node.children
    }
    options = [
        _evaluate_action(
            model, s0, action, policy, event_names, eval_rollouts, random.Random(rng.random())
        )
        for action in first_actions
    ]
    best = max(options, key=lambda o: o.ev).action
    return SolveResult(
        options=options,
        best=best,
        solver="mcts",
        exact=False,
        diagnostics={
            "iterations": iterations,
            "tree_nodes": len(tree),
            "eval_rollouts": eval_rollouts,
        },
    )


def _simulate(
    model: Model,
    root: _Node,
    tree: dict,
    rng: random.Random,
    c: float,
    widen_c: float,
    widen_alpha: float,
    root_returns: dict,
    root_events: dict,
    root_counts: dict,
    event_names: list[str],
    scale: _Scale,
) -> None:
    node = root
    path: list[_Node | _Chance] = [node]
    first_action = ""
    prefix = 0.0  # rewards of transitions descended through the tree

    # Selection / expansion.
    while not model.is_terminal(node.state, node.t):
        if node.untried:
            action = node.untried.pop()
            chance = _Chance(action)
            node.children[action] = chance
            path.append(chance)
        else:
            action = _uct_pick(node, c, rng, scale)
            chance = node.children[action]
            path.append(chance)
        if node is root:
            first_action = action
        nxt, reward, fresh = _sample_outcome(model, node, chance, rng, widen_c, widen_alpha)
        prefix += reward
        key = (canonical(nxt), node.t + 1)
        child = tree.get(key)
        if child is None and fresh:
            actions = [] if model.is_terminal(nxt, node.t + 1) else model.actions(nxt)
            child = _Node(nxt, node.t + 1, actions)
            tree[key] = child
        if child is None:  # reused outcome whose node was never created; stop descent
            path.append(("leaf-outcome", nxt, reward))
            break
        node = child
        path.append(node)

    # Evaluation: rollout from the leaf.
    leaf_state, leaf_t = node.state, node.t
    if isinstance(path[-1], tuple):  # stopped at a bare outcome
        _, leaf_state, _ = path[-1]
        leaf_t = node.t + 1
    future, fired = _rollout_from(model, leaf_state, leaf_t, rng, event_names)
    ret = prefix + future

    # Backpropagation.
    scale.update(ret)
    for entry in path:
        if isinstance(entry, (_Node, _Chance)):
            entry.visits += 1
            entry.total += ret
    if first_action:
        root_returns[first_action].append(ret)
        root_counts[first_action] += 1
        for name in event_names:
            root_events[first_action][name] += bool(fired[name])


def _evaluate_action(
    model: Model,
    s0: State,
    first_action: str,
    policy: dict,
    event_names: list[str],
    n_rollouts: int,
    rng: random.Random,
) -> OptionResult:
    """Fresh rollouts of ``first_action`` then the greedy tree policy."""
    returns, hits = [], {e: 0 for e in event_names}
    for _ in range(n_rollouts):
        state, t, action, total = copy.deepcopy(s0), 0, first_action, 0.0
        fired = {e: bool(model.events[e](copy.deepcopy(state))) for e in event_names}
        while not model.is_terminal(state, t):
            nxt = model.transition(copy.deepcopy(state), action, rng)
            total += model.reward(state, action, nxt)
            state, t = nxt, t + 1
            for e in event_names:
                fired[e] = fired[e] or bool(model.events[e](copy.deepcopy(state)))
            if model.is_terminal(state, t):
                break
            nxt_actions = model.actions(copy.deepcopy(state))
            action = policy.get((canonical(state), t), rng.choice(nxt_actions))
        returns.append(total)
        for e in event_names:
            hits[e] += fired[e]
    n = len(returns)
    mean = sum(returns) / n
    var = max(0.0, sum(x * x for x in returns) / n - mean * mean)
    half = 1.96 * math.sqrt(var / n)
    ordered = sorted(returns)
    return OptionResult(
        action=first_action,
        ev=mean,
        ci_lo=mean - half,
        ci_hi=mean + half,
        p_events={e: hits[e] / n for e in event_names},
        worst_case_p5=_percentile(ordered, 0.05),
        n=n,
    )


def _uct_pick(node: _Node, c: float, rng: random.Random, scale: _Scale) -> str:
    log_n = math.log(max(1, node.visits))
    best, best_score = "", float("-inf")
    for action in sorted(node.children):
        child = node.children[action]
        if child.visits == 0:
            score = float("inf")
        else:
            score = scale.norm(child.mean) + c * math.sqrt(log_n / child.visits)
        if score > best_score:
            best, best_score = action, score
    return best


def _sample_outcome(
    model: Model,
    node: _Node,
    chance: _Chance,
    rng: random.Random,
    widen_c: float,
    widen_alpha: float,
) -> tuple[State, float, bool]:
    cap = widen_c * (max(1, chance.visits) ** widen_alpha)
    if len(chance.outcomes) < max(1, int(cap)):
        nxt = model.transition(copy.deepcopy(node.state), chance.action, rng)
        reward = model.reward(node.state, chance.action, nxt)
        chance.outcomes.append((copy.deepcopy(nxt), reward))
        return nxt, reward, True
    return (*rng.choice(chance.outcomes), False)


def _rollout_from(
    model: Model, state: State, t: int, rng: random.Random, event_names: list[str]
) -> tuple[float, dict[str, bool]]:
    total = 0.0
    fired = {name: False for name in event_names}
    current = copy.deepcopy(state)
    for name in event_names:
        if model.events[name](copy.deepcopy(current)):
            fired[name] = True
    while not model.is_terminal(current, t):
        actions = model.actions(copy.deepcopy(current))
        policy_action = model.default_policy(copy.deepcopy(current), rng)
        action = policy_action if policy_action in actions else rng.choice(actions)
        nxt = model.transition(copy.deepcopy(current), action, rng)
        total += model.reward(current, action, nxt)
        current, t = nxt, t + 1
        for name in event_names:
            if model.events[name](copy.deepcopy(current)):
                fired[name] = True
    return total, fired
