"""Hand-written world of the three Oficina Leme plans.

Reward is negative engineer-days. With outcomes() present the solver is exact.
"""

from saboragi.wm import Model

PLANS = {
    "strangler_counter_first": {
        "base": 22,
        "later": 0,
        "p_miss": 0.10,
        "p_incident": 0.06,
        "repair": 18,
        "incident_cost": 35,
    },
    "big_bang_rewrite": {
        "base": 28,
        "later": 0,
        "p_miss": 0.32,
        "p_incident": 0.09,
        "repair": 18,
        "incident_cost": 35,
    },
    "facade_keep_tomcat": {
        "base": 8,
        "later": 26,
        "p_miss": 0.0,
        "p_incident": 0.28,
        "repair": 0,
        "incident_cost": 70,
    },
}


class World(Model):
    horizon = 1
    state_bounds = {"t": (0, 1), "days": (0, 400), "incident": (0, 1), "missed": (0, 1)}
    events = {
        "credential_incident": lambda s: float(s["incident"]),
        "missed_behavior": lambda s: float(s["missed"]),
    }

    def initial_state(self):
        return {"t": 0, "days": 0.0, "incident": 0, "missed": 0}

    def actions(self, state):
        return list(PLANS)

    def _finish(self, plan, missed, incident):
        spec = PLANS[plan]
        days = spec["base"] + spec["later"]
        if missed:
            days += spec["repair"]
        if incident:
            days += spec["incident_cost"]
        return {"t": 1, "days": float(days), "incident": int(incident), "missed": int(missed)}

    def transition(self, state, action, rng):
        spec = PLANS[action]
        missed = rng.random() < spec["p_miss"]
        incident = rng.random() < spec["p_incident"]
        return self._finish(action, missed, incident)

    def reward(self, state, action, next_state):
        return float(-next_state["days"])

    def is_terminal(self, state, t):
        return state["t"] >= 1

    def outcomes(self, state, action):
        spec = PLANS[action]
        branches = []
        for missed, p_miss in ((True, spec["p_miss"]), (False, 1 - spec["p_miss"])):
            for incident, p_inc in ((True, spec["p_incident"]), (False, 1 - spec["p_incident"])):
                probability = p_miss * p_inc
                if probability > 0:
                    branches.append((probability, self._finish(action, missed, incident)))
        return branches
