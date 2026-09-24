"""Rent looks cheaper in this picture. Late means the delivery is late."""

from saboragi.wm import Model


class World(Model):
    horizon = 1
    state_bounds = {"cost": (0.0, 40.0), "late": (0.0, 1.0), "done": (0.0, 1.0)}
    events = {"late": lambda s: float(s["late"])}

    def initial_state(self):
        return {"cost": 0.0, "late": 0.0, "done": 0.0}

    def actions(self, state):
        return ["rent", "buy"]

    def outcomes(self, state, action):
        if action == "rent":
            cost, late = 5.0, 0.0
        else:
            cost, late = 9.0, 1.0
        return [(1.0, {"cost": cost, "late": late, "done": 1.0})]

    def transition(self, state, action, rng):
        return self.outcomes(state, action)[0][1]

    def reward(self, state, action, next_state):
        return -next_state["cost"]

    def is_terminal(self, state, t):
        return t >= self.horizon
