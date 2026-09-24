"""Simulation-engineer framing. The stated days and chances are used as given. Zero-probability branches are omitted."""

from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 1
    params = {
        "strangler_base": 22.0,
        "strangler_later": 0.0,
        "strangler_p_miss": 0.10,
        "strangler_p_inc": 0.06,
        "strangler_repair": 18.0,
        "strangler_incident": 35.0,
        "big_bang_base": 28.0,
        "big_bang_later": 0.0,
        "big_bang_p_miss": 0.32,
        "big_bang_p_inc": 0.09,
        "big_bang_repair": 18.0,
        "big_bang_incident": 35.0,
        "facade_base": 8.0,
        "facade_later": 26.0,
        "facade_p_miss": 0.0,
        "facade_p_inc": 0.28,
        "facade_repair": 0.0,
        "facade_incident": 70.0,
    }
    state_bounds = {
        "t": (0, 1),
        "days": (0, 400),
        "incident": (0, 1),
        "missed": (0, 1),
    }
    events = {
        "credential_incident": lambda s: float(s["incident"]),
        "missed_behavior": lambda s: float(s["missed"]),
    }

    def initial_state(self):
        return {"t": 0, "days": 0.0, "incident": 0, "missed": 0}

    def actions(self, state):
        return [
            "strangler_counter_first",
            "big_bang_rewrite",
            "facade_keep_tomcat",
        ]

    def _plan(self, action):
        if action == "strangler_counter_first":
            prefix = "strangler"
        elif action == "big_bang_rewrite":
            prefix = "big_bang"
        else:
            prefix = "facade"
        return (
            float(self.param(prefix + "_base")),
            float(self.param(prefix + "_later")),
            float(self.param(prefix + "_p_miss")),
            float(self.param(prefix + "_p_inc")),
            float(self.param(prefix + "_repair")),
            float(self.param(prefix + "_incident")),
        )

    def _finish(self, action, missed, incident):
        base, later, _p_miss, _p_inc, repair, incident_cost = self._plan(action)
        days = base + later
        if missed:
            days += repair
        if incident:
            days += incident_cost
        return {
            "t": 1,
            "days": float(days),
            "incident": 1 if incident else 0,
            "missed": 1 if missed else 0,
        }

    def transition(self, state, action, rng):
        _base, _later, p_miss, p_inc, _repair, _cost = self._plan(action)
        missed = rng.random() < p_miss
        incident = rng.random() < p_inc
        return self._finish(action, missed, incident)

    def reward(self, state, action, next_state):
        return float(-next_state["days"])

    def is_terminal(self, state, t):
        return state["t"] >= 1

    def outcomes(self, state, action):
        _base, _later, p_miss, p_inc, _repair, _cost = self._plan(action)
        branches = []
        for missed, p_m in ((True, p_miss), (False, 1.0 - p_miss)):
            for incident, p_i in ((True, p_inc), (False, 1.0 - p_inc)):
                probability = p_m * p_i
                if probability > 0.0:
                    branches.append((probability, self._finish(action, missed, incident)))
        return branches
