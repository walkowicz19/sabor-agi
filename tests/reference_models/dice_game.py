"""Stop-or-continue dice game. Rolling a 1 busts (total reset to 0, game over)."""

from saboragi.wm import Model


class World(Model):
    horizon = 10
    state_bounds = {"t": (0, 10), "total": (0, 60)}
    events = {"bust": lambda s: 1.0 if s["phase"] == "done" and s["total"] == 0 else 0.0}

    def initial_state(self):
        return {"t": 0, "total": 0, "phase": "play"}

    def actions(self, state):
        return ["roll", "stop"]

    def transition(self, state, action, rng):
        if action == "stop":
            return {"t": state["t"] + 1, "total": state["total"], "phase": "done"}
        if action == "roll":
            die = rng.randint(1, 6)
            if die == 1:
                return {"t": state["t"] + 1, "total": 0, "phase": "done"}
            return {"t": state["t"] + 1, "total": state["total"] + die, "phase": "play"}
        raise ValueError(f"unknown action {action!r}")

    def reward(self, state, action, next_state):
        if state["phase"] == "play" and next_state["phase"] == "done" and action == "stop":
            return float(next_state["total"])
        return 0.0

    def is_terminal(self, state, t):
        return state["phase"] == "done" or t >= self.horizon

    def outcomes(self, state, action):
        if action == "stop":
            return [(1.0, {"t": state["t"] + 1, "total": state["total"], "phase": "done"})]
        dist = []
        for die in range(1, 7):
            if die == 1:
                dist.append((1 / 6, {"t": state["t"] + 1, "total": 0, "phase": "done"}))
            else:
                dist.append(
                    (1 / 6, {"t": state["t"] + 1, "total": state["total"] + die, "phase": "play"})
                )
        return dist
