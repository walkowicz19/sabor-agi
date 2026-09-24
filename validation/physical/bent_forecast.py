"""The series bends at the end. Repeating the last number beats the fitted line."""

from saboragi.sim import linear_project
from saboragi.wm import Model

SERIES = [0.0, 1.0, 2.0, 9.0]
ACTUAL_NEXT = 9.0


class World(Model):
    horizon = 1
    state_bounds = {"t": (0, 1), "error": (0, 20)}

    def initial_state(self):
        return {"t": 0, "error": 0.0}

    def actions(self, state):
        return ["trust_trend", "repeat_last"]

    def _next(self, state, action):
        if action == "trust_trend":
            predicted = linear_project(SERIES, steps=1)[0]
        else:
            predicted = SERIES[-1]
        return {"t": 1, "error": abs(predicted - ACTUAL_NEXT)}

    def transition(self, state, action, rng):
        return self._next(state, action)

    def reward(self, state, action, next_state):
        return -next_state["error"]

    def is_terminal(self, state, t):
        return t >= self.horizon

    def outcomes(self, state, action):
        return [(1.0, self._next(state, action))]
