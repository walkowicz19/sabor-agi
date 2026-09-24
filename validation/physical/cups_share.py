"""Two cups. Sharing fills the empty cup. Pouring some away does not."""

from saboragi.sim import exchange, transfer
from saboragi.wm import Model


class World(Model):
    horizon = 1
    state_bounds = {"t": (0, 1), "h0": (0, 4), "h1": (0, 4)}

    def initial_state(self):
        return {"t": 0, "h0": 2.0, "h1": 0.0}

    def actions(self, state):
        return ["share", "pour_out"]

    def _next(self, state, action):
        if action == "share":
            levels = exchange([state["h0"], state["h1"]], rate=1.0, dt=1.0)
        else:
            kept, _moved = transfer([state["h0"], 0.0], 0, 1, 0.5)
            levels = [kept[0], state["h1"]]
        return {"t": 1, "h0": levels[0], "h1": levels[1]}

    def transition(self, state, action, rng):
        return self._next(state, action)

    def reward(self, state, action, next_state):
        return next_state["h1"]

    def is_terminal(self, state, t):
        return t >= self.horizon

    def outcomes(self, state, action):
        return [(1.0, self._next(state, action))]
