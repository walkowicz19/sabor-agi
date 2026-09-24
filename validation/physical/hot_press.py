"""The press is already at its heat limit. Cooling first is the only way to make a part."""

from saboragi.sim import machine_step
from saboragi.wm import Model


class World(Model):
    horizon = 2
    params = {"heat_limit": 2.0}
    state_bounds = {"t": (0, 2), "parts": (0, 5), "heat": (0, 5), "jammed": (0, 1)}

    def initial_state(self):
        return {"t": 0, "parts": 0.0, "heat": 2.0, "jammed": 0}

    def actions(self, state):
        return ["run", "cool"]

    def _next(self, state, action):
        parts, heat, jammed = machine_step(
            state["parts"], state["heat"], action, self.param("heat_limit")
        )
        return {"t": state["t"] + 1, "parts": parts, "heat": heat, "jammed": 1 if jammed else 0}

    def transition(self, state, action, rng):
        return self._next(state, action)

    def reward(self, state, action, next_state):
        return next_state["parts"] - state["parts"]

    def is_terminal(self, state, t):
        return t >= self.horizon

    def outcomes(self, state, action):
        return [(1.0, self._next(state, action))]
