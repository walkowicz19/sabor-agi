"""A warehouse move. At the stated stockout chance, phasing wins. The low end flips it."""

from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 1
    params = {"stockout_p": Uncertain(0.40, 0.05, 0.70)}
    state_bounds = {
        "days": (0.0, 80.0),
        "stockout": (0.0, 1.0),
        "done": (0.0, 1.0),
    }
    events = {"stockout": lambda s: float(s["stockout"])}

    def initial_state(self):
        return {"days": 0.0, "stockout": 0.0, "done": 0.0}

    def actions(self, state):
        return ["phased_move", "weekend_move"]

    def outcomes(self, state, action):
        if action == "phased_move":
            base, chance, blow = 10.0, 0.10, 20.0
        else:
            base, chance, blow = 4.0, self.param("stockout_p"), 30.0
        quiet = {
            "days": base,
            "stockout": 0.0,
            "done": 1.0,
        }
        hit = {
            "days": base + blow,
            "stockout": 1.0,
            "done": 1.0,
        }
        return [(1.0 - chance, quiet), (chance, hit)]

    def transition(self, state, action, rng):
        roll = rng.random()
        cursor = 0.0
        chosen = None
        for prob, nxt in self.outcomes(state, action):
            cursor += prob
            chosen = nxt
            if roll <= cursor:
                return nxt
        return chosen

    def reward(self, state, action, next_state):
        return -next_state["days"]

    def is_terminal(self, state, t):
        return t >= self.horizon
