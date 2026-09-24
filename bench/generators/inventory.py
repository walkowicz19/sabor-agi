"""Inventory ordering under stochastic demand. Tests multi-step planning."""

from __future__ import annotations

import random

from bench.generators.base import assemble, ground_truth, normalize_dist, prob_words
from bench.problems import Problem


def _render(
    horizon: int,
    stock0: int,
    price: float,
    cost: float,
    holding: float,
    demand: list,
    orders: list[int],
) -> str:
    max_stock = stock0 + horizon * max(orders)
    max_unmet = max(d for d, _ in demand)
    return assemble(
        f"""class World(Model):
    horizon = {horizon}
    state_bounds = {{"t": (0, {horizon}), "stock": (0, {max_stock}), "unmet": (0, {max_unmet})}}
    events = {{"stockout": lambda s: 1.0 if s["unmet"] > 0 else 0.0}}

    DEMAND = {[(d, round(p, 6)) for d, p in demand]!r}
    PRICE = {price!r}
    UNIT_COST = {cost!r}
    HOLDING = {holding!r}

    def initial_state(self):
        return {{"t": 0, "stock": {stock0}, "unmet": 0}}

    def actions(self, state):
        return {[f"order_{q}" for q in orders]!r}

    @staticmethod
    def _qty(action):
        return int(action.split("_")[1])

    def _settle(self, state, order, level):
        sold = min(state["stock"] + order, level)
        return {{
            "t": state["t"] + 1,
            "stock": state["stock"] + order - sold,
            "unmet": level - sold,
        }}

    def transition(self, state, action, rng):
        order = self._qty(action)
        r = rng.random()
        level = 0
        for amount, prob in self.DEMAND:
            level = amount
            if r < prob:
                break
            r -= prob
        return self._settle(state, order, level)

    def reward(self, state, action, next_state):
        order = self._qty(action)
        sold = state["stock"] + order - next_state["stock"]
        return self.PRICE * sold - self.UNIT_COST * order - self.HOLDING * next_state["stock"]

    def is_terminal(self, state, t):
        return state["t"] >= {horizon}

    def outcomes(self, state, action):
        order = self._qty(action)
        return [(p, self._settle(state, order, d)) for d, p in self.DEMAND]
"""
    )


def _describe(
    horizon: int,
    stock0: int,
    price: float,
    cost: float,
    holding: float,
    demand: list,
    orders: list[int],
) -> str:
    dist = ", ".join(f"demand {d} with {prob_words(p)}" for d, p in demand)
    return (
        f"You run a shop for {horizon} days. You start with {stock0} units in stock.\n"
        f"Each morning you order {', '.join(f'{q} units' for q in orders)} "
        f"(choose one amount). Each unit ordered costs ${cost:g}.\n"
        f"During the day, customer demand is random: {dist}. "
        f"You sell at most what you have (stock plus order), earning ${price:g} "
        f"per unit sold. Demand you cannot meet is lost.\n"
        f"Each evening you pay ${holding:g} holding cost per unit left in stock."
    )


def generate(rng: random.Random, horizon: int, idx: int, seed: int) -> Problem | None:
    stock0 = rng.choice([5, 8, 10, 12, 15])
    price = round(rng.uniform(4, 6), 1)
    cost = round(rng.uniform(1.5, 2.5), 1)
    holding = round(rng.uniform(0.3, 0.7), 2)
    if horizon >= 10:
        demand_menu, order_menu, n_levels = [0, 5, 10, 15], [10, 20], 3
    else:
        demand_menu, order_menu, n_levels = (
            [0, 5, 10, 15, 20, 25],
            [10, 20, 30, 40],
            rng.choice([3, 4]),
        )
    levels = sorted(rng.sample(demand_menu, k=n_levels))
    weights = [rng.random() + 0.2 for _ in levels]
    demand = normalize_dist([(d, w / sum(weights)) for d, w in zip(levels, weights, strict=True)])
    order_levels = sorted(rng.sample(order_menu, k=2))
    orders = [0, *order_levels]
    code = _render(horizon, stock0, price, cost, holding, demand, orders)
    actions = [f"order_{q}" for q in orders]
    solved = ground_truth(code, actions)
    if solved is None:
        return None
    return Problem(
        id=f"inventory-h{horizon}-{idx:03d}",
        family="inventory",
        horizon=horizon,
        description=_describe(horizon, stock0, price, cost, holding, demand, orders),
        actions=actions,
        q_values={o.action: o.ev for o in solved.options},
        optimal=solved.best,
        event_name="stockout",
        event_description="the probability of at least one day with unmet demand",
        event_probs={o.action: o.p_events["stockout"] for o in solved.options},
        model_code=code,
        seed=seed,
    )
