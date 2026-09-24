"""2009 clinic book. The stated days, with no extra range."""

from saboragi.wm import Model


class World(Model):
    horizon = 1
    state_bounds = {
        "days": (0.0, 200.0),
        "missed_behavior": (0.0, 1.0),
        "privacy_incident": (0.0, 1.0),
        "done": (0.0, 1.0),
    }
    events = {
        "missed_behavior": lambda s: float(s["missed_behavior"]),
        "privacy_incident": lambda s: float(s["privacy_incident"]),
    }

    def initial_state(self):
        return {"days": 0.0, "missed_behavior": 0.0, "privacy_incident": 0.0, "done": 0.0}

    def actions(self, state):
        return ["start_with_book", "rewrite_everything", "keep_old_desk"]

    def _plan(self, action):
        if action == "start_with_book":
            return 20.0, 0.10, 10.0, 0.05, 20.0
        if action == "rewrite_everything":
            return 28.0, 0.25, 20.0, 0.10, 20.0
        return 24.0, 0.05, 10.0, 0.40, 30.0

    def outcomes(self, state, action):
        base, miss_p, miss_cost, inc_p, inc_cost = self._plan(action)
        branches = []
        for missed in (0.0, 1.0):
            for incident in (0.0, 1.0):
                p_miss = miss_p if missed else 1.0 - miss_p
                p_inc = inc_p if incident else 1.0 - inc_p
                days = base
                days += miss_cost if missed else 0.0
                days += inc_cost if incident else 0.0
                branches.append(
                    (
                        p_miss * p_inc,
                        {
                            "days": days,
                            "missed_behavior": missed,
                            "privacy_incident": incident,
                            "done": 1.0,
                        },
                    )
                )
        return branches

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
