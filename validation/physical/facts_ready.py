"""The facts are already in hand. Finishing is worth more than looking up again."""

from saboragi.sim import agent_step
from saboragi.wm import Model


class World(Model):
    horizon = 1
    params = {"needed": 2}
    state_bounds = {"t": (0, 1), "facts": (0, 2), "finished": (0, 1), "premature": (0, 1)}

    def initial_state(self):
        return {"t": 0, "facts": 2, "finished": 0, "premature": 0}

    def actions(self, state):
        return ["lookup", "finish"]

    def _next(self, state, action):
        facts, finished, premature = agent_step(
            int(state["facts"]), action, int(self.param("needed"))
        )
        return {
            "t": state["t"] + 1,
            "facts": facts,
            "finished": 1 if finished else 0,
            "premature": 1 if premature else 0,
        }

    def transition(self, state, action, rng):
        return self._next(state, action)

    def reward(self, state, action, next_state):
        if action == "lookup":
            return 0.0
        if next_state["finished"]:
            return 5.0
        return -2.0

    def is_terminal(self, state, t):
        return t >= self.horizon or state["finished"] == 1 or state["premature"] == 1

    def outcomes(self, state, action):
        return [(1.0, self._next(state, action))]
