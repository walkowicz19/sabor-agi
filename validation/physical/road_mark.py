"""Already rolling. A mark sits ahead and to the side. Turning beats another burst of speed."""

import math

from saboragi.sim import bicycle_step
from saboragi.wm import Model

MARK = (3.0, 1.0)


class World(Model):
    horizon = 2
    state_bounds = {
        "t": (0, 2),
        "x": (0, 20),
        "y": (-5, 5),
        "heading": (-2, 2),
        "speed": (0, 8),
    }

    def initial_state(self):
        return {"t": 0, "x": 1.0, "y": 0.0, "heading": 0.0, "speed": 1.0}

    def actions(self, state):
        return ["accelerate", "hold", "steer"]

    def _next(self, state, action):
        accel = 1.0 if action == "accelerate" else 0.0
        steer = 0.6 if action == "steer" else 0.0
        x, y, heading, speed = bicycle_step(
            state["x"],
            state["y"],
            state["heading"],
            state["speed"],
            steer,
            accel,
            1.0,
            2.0,
        )
        return {"t": state["t"] + 1, "x": x, "y": y, "heading": heading, "speed": speed}

    def transition(self, state, action, rng):
        return self._next(state, action)

    def reward(self, state, action, next_state):
        if next_state["t"] < self.horizon:
            return 0.0
        return -math.hypot(next_state["x"] - MARK[0], next_state["y"] - MARK[1])

    def is_terminal(self, state, t):
        return t >= self.horizon

    def outcomes(self, state, action):
        return [(1.0, self._next(state, action))]
