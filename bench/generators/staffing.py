"""Shift staffing against random arrivals. Tests backlog/capacity trade-offs."""

from __future__ import annotations

import random

from bench.generators.base import assemble, ground_truth, normalize_dist, prob_words
from bench.problems import Problem


def _render(
    horizon: int,
    backlog0: int,
    wage: float,
    penalty: float,
    threshold: int,
    arrivals: list,
    staff: list[int],
) -> str:
    max_backlog = backlog0 + horizon * max(a for a, _ in arrivals)
    return assemble(
        f"""class World(Model):
    horizon = {horizon}
    state_bounds = {{"t": (0, {horizon}), "backlog": (0, {max_backlog})}}
    events = {{"overload": lambda s: 1.0 if s["backlog"] >= {threshold} else 0.0}}

    ARRIVALS = {[(a, round(p, 6)) for a, p in arrivals]!r}
    STAFF = {{{", ".join(f"'staff_{s}': {s}" for s in staff)}}}
    WAGE = {wage!r}
    PENALTY = {penalty!r}

    def initial_state(self):
        return {{"t": 0, "backlog": {backlog0}}}

    def actions(self, state):
        return {sorted(f"staff_{s}" for s in staff)!r}

    def transition(self, state, action, rng):
        crew = self.STAFF[action]
        r = rng.random()
        count = 0
        for amount, prob in self.ARRIVALS:
            count = amount
            if r < prob:
                break
            r -= prob
        left = max(0, state["backlog"] + count - crew)
        return {{"t": state["t"] + 1, "backlog": left}}

    def reward(self, state, action, next_state):
        crew = self.STAFF[action]
        return -(self.WAGE * crew + self.PENALTY * next_state["backlog"])

    def is_terminal(self, state, t):
        return state["t"] >= {horizon}

    def outcomes(self, state, action):
        crew = self.STAFF[action]
        return [
            (p, {{"t": state["t"] + 1,
                  "backlog": max(0, state["backlog"] + a - crew)}})
            for a, p in self.ARRIVALS
        ]
"""
    )


def generate(rng: random.Random, horizon: int, idx: int, seed: int) -> Problem | None:
    backlog0 = rng.choice([0, 1, 2, 3])
    wage = round(rng.uniform(8, 15), 1)
    penalty = round(rng.uniform(4, 10), 1)
    threshold = rng.choice([6, 7, 8, 9, 10])
    levels = sorted(rng.sample([0, 1, 2, 3, 4], k=rng.choice([3, 4])))
    weights = [rng.random() + 0.2 for _ in levels]
    arrivals = normalize_dist([(a, w / sum(weights)) for a, w in zip(levels, weights, strict=True)])
    staff = sorted(rng.sample([1, 2, 3, 4], k=3))
    code = _render(horizon, backlog0, wage, penalty, threshold, arrivals, staff)
    actions = sorted(f"staff_{s}" for s in staff)
    solved = ground_truth(code, actions)
    if solved is None:
        return None
    dist = ", ".join(f"{a} jobs with {prob_words(p)}" for a, p in arrivals)
    description = (
        f"You manage a service desk for {horizon} shifts, starting with "
        f"{backlog0} backlogged jobs.\n"
        f"Each shift you schedule {', '.join(f'{s} staff' for s in staff)} "
        f"(choose one level). Each staff member costs ${wage:g} in wages and "
        f"handles one job that shift.\n"
        f"New jobs arrive randomly each shift: {dist}. Jobs nobody handles "
        f"stay backlogged, costing ${penalty:g} each per shift in penalties."
    )
    return Problem(
        id=f"staffing-h{horizon}-{idx:03d}",
        family="staffing_queue",
        horizon=horizon,
        description=description,
        actions=actions,
        q_values={o.action: o.ev for o in solved.options},
        optimal=solved.best,
        event_name="overload",
        event_description=(f"the probability the backlog reaches {threshold} at any point"),
        event_probs={o.action: o.p_events["overload"] for o in solved.options},
        model_code=code,
        seed=seed,
    )
