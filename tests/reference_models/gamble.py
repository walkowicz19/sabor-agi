"""One-step lottery choice. EVs: safe=10, risky=10, longshot=-4.5."""

from saboragi.wm import Model


class World(Model):
    horizon = 1
    state_bounds = {"t": (0, 1), "payoff": (-100, 100)}
    events = {"jackpot": lambda s: 1.0 if s["payoff"] >= 100 else 0.0}

    def initial_state(self):
        return {"t": 0, "payoff": 0.0}

    def actions(self, state):
        return ["longshot", "risky", "safe"]

    def transition(self, state, action, rng):
        nxt = {"t": 1, "payoff": 0.0}
        if action == "safe":
            nxt["payoff"] = 10.0
        elif action == "risky":
            nxt["payoff"] = 25.0 if rng.random() < 0.5 else -5.0
        elif action == "longshot":
            nxt["payoff"] = 100.0 if rng.random() < 0.05 else -10.0
        else:
            raise ValueError(f"unknown action {action!r}")
        return nxt

    def reward(self, state, action, next_state):
        return next_state["payoff"] - state["payoff"]

    def is_terminal(self, state, t):
        return state["t"] >= 1

    def outcomes(self, state, action):
        if action == "safe":
            return [(1.0, {"t": 1, "payoff": 10.0})]
        if action == "risky":
            return [(0.5, {"t": 1, "payoff": 25.0}), (0.5, {"t": 1, "payoff": -5.0})]
        if action == "longshot":
            return [(0.05, {"t": 1, "payoff": 100.0}), (0.95, {"t": 1, "payoff": -10.0})]
        raise ValueError(f"unknown action {action!r}")
