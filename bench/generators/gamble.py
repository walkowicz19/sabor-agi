"""Repeated lottery choice with a bankroll. Tests EV reasoning under variance."""

from __future__ import annotations

import random

from bench.generators.base import assemble, ground_truth, normalize_dist, prob_words
from bench.problems import Problem


def _render(bank: int, horizon: int, lotteries: dict[str, list]) -> str:
    payoffs = ",\n        ".join(
        f"{name!r}: {[(a, round(p, 6)) for a, p in table]!r}" for name, table in lotteries.items()
    )
    names = list(lotteries)
    lo = bank + horizon * min(a for table in lotteries.values() for a, _ in table) - 5
    hi = bank + horizon * max(a for table in lotteries.values() for a, _ in table) + 5
    return assemble(
        f"""class World(Model):
    horizon = {horizon}
    state_bounds = {{"t": (0, {horizon}), "wealth": ({lo}, {hi})}}
    events = {{"end_down": lambda s: 1.0 if s["wealth"] < {bank} else 0.0}}

    PAYOFFS = {{
        {payoffs}
    }}

    def initial_state(self):
        return {{"t": 0, "wealth": {bank}}}

    def actions(self, state):
        return {names!r}

    def transition(self, state, action, rng):
        r = rng.random()
        delta = 0
        for amount, prob in self.PAYOFFS[action]:
            if r < prob:
                delta = amount
                break
            r -= prob
        return {{"t": state["t"] + 1, "wealth": state["wealth"] + delta}}

    def reward(self, state, action, next_state):
        return float(next_state["wealth"] - state["wealth"])

    def is_terminal(self, state, t):
        return state["t"] >= {horizon}

    def outcomes(self, state, action):
        return [
            (p, {{"t": state["t"] + 1, "wealth": state["wealth"] + a}})
            for a, p in self.PAYOFFS[action]
        ]
"""
    )


def _describe(bank: int, horizon: int, lotteries: dict[str, list]) -> str:
    lines = [
        f"You start with ${bank}.",
        f"Over {horizon} rounds, each round you must pick one lottery. "
        "Winnings add to (and losses subtract from) your wealth.",
    ]
    for name, table in lotteries.items():
        parts = ", then ".join(
            f"{prob_words(p)} win ${a}" if a >= 0 else f"{prob_words(p)} lose ${-a}"
            for a, p in table
        )
        lines.append(f"- {name}: {parts}.")
    lines.append(f"After {horizon} rounds the game ends with whatever wealth you have.")
    return "\n".join(lines)


def generate(rng: random.Random, horizon: int, idx: int, seed: int) -> Problem | None:
    bank = 100
    safe_ev = rng.uniform(8, 12)
    lotteries = {"lottery_A": [(round(safe_ev), 1.0)]}
    win = rng.choice([20, 25, 30, 40])
    p_win = rng.uniform(0.3, 0.55)
    loss = -round((win * p_win - safe_ev * rng.uniform(0.95, 1.05)) / (1 - p_win))
    lotteries["lottery_B"] = normalize_dist([(win, p_win), (loss, 1 - p_win)])
    if rng.random() < 0.6:
        jackpot = rng.choice([80, 100, 120, 150])
        p_jack = rng.uniform(0.03, 0.08)
        consolation = -rng.choice([8, 10, 12])
        lotteries["lottery_C"] = normalize_dist([(jackpot, p_jack), (consolation, 1 - p_jack)])
    code = _render(bank, horizon, lotteries)
    actions = list(lotteries)
    solved = ground_truth(code, actions)
    if solved is None:
        return None
    return Problem(
        id=f"gamble-h{horizon}-{idx:03d}",
        family="gamble",
        horizon=horizon,
        description=_describe(bank, horizon, lotteries),
        actions=actions,
        q_values={o.action: o.ev for o in solved.options},
        optimal=solved.best,
        event_name="end_down",
        event_description=(f"the probability that your wealth drops below ${bank} at any point"),
        event_probs={o.action: o.p_events["end_down"] for o in solved.options},
        model_code=code,
        seed=seed,
    )
