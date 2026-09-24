"""Multi-step inventory ordering under stochastic demand (horizon 3)."""

from saboragi.wm import Model

PRICE = 5.0
UNIT_COST = 2.0
HOLDING_COST = 0.5
DEMAND = [(0, 0.2), (10, 0.4), (20, 0.3), (30, 0.1)]


class World(Model):
    horizon = 3
    state_bounds = {"t": (0, 3), "stock": (0, 200), "unmet": (0, 30)}
    events = {"stockout": lambda s: 1.0 if s["unmet"] > 0 else 0.0}

    def initial_state(self):
        return {"t": 0, "stock": 10, "unmet": 0}

    def actions(self, state):
        return ["order_0", "order_20", "order_40"]

    @staticmethod
    def _order_of(action):
        return int(action.split("_")[1])

    def _settle(self, state, order, demand):
        sold = min(state["stock"] + order, demand)
        stock = state["stock"] + order - sold
        return {"t": state["t"] + 1, "stock": stock, "unmet": demand - sold}

    def transition(self, state, action, rng):
        order = self._order_of(action)
        r, demand = rng.random(), 0
        for level, prob in DEMAND:
            demand = level
            if r < prob:
                break
            r -= prob
        return self._settle(state, order, demand)

    def reward(self, state, action, next_state):
        order = self._order_of(action)
        sold = state["stock"] + order - next_state["stock"]
        return PRICE * sold - UNIT_COST * order - HOLDING_COST * next_state["stock"]

    def is_terminal(self, state, t):
        return state["t"] >= 3

    def outcomes(self, state, action):
        order = self._order_of(action)
        return [(p, self._settle(state, order, d)) for d, p in DEMAND]
