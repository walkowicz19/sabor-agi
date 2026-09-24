"""Straight-road driving. Accelerating is worth 3; holding or steering is worth 0."""

from saboragi.sim import bicycle_step
from saboragi.wm import Model


class World(Model):
    horizon = 2
    state_bounds = {
        "t": (0, 2),
        "x": (0, 30),
        "y": (-5, 5),
        "heading": (-1, 1),
        "speed": (0, 5),
    }

    def initial_state(self):
        return {"t": 0, "x": 0.0, "y": 0.0, "heading": 0.0, "speed": 0.0}

    def actions(self, state):
        return ["accelerate", "hold", "steer"]

    def _next(self, state, action):
        accel = 1.0 if action == "accelerate" else 0.0
        steer = 0.2 if action == "steer" else 0.0
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
        return {
            "t": state["t"] + 1,
            "x": x,
            "y": y,
            "heading": heading,
            "speed": max(0.0, min(5.0, speed)),
        }

    def transition(self, state, action, rng):
        return self._next(state, action)

    def reward(self, state, action, next_state):
        return (next_state["x"] - state["x"]) - abs(next_state["y"])

    def is_terminal(self, state, t):
        return t >= self.horizon

    def outcomes(self, state, action):
        return [(1.0, self._next(state, action))]
