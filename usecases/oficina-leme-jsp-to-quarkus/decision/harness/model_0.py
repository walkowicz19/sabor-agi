"""Actuary framing. One step. The same slack sits on every plan. The facade incident cost is the soft number."""

from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 1
    params = {
        "strangler_base": 22.0,
        "big_bang_base": 28.0,
        "facade_base": 8.0,
        "facade_later": 26.0,
        "repair": 18.0,
        "incident_cutover": 35.0,
        "incident_facade": Uncertain(70.0, 45.0, 110.0),
        "p_miss_strangler": 0.10,
        "p_inc_strangler": 0.06,
        "p_miss_big_bang": 0.32,
        "p_inc_big_bang": 0.09,
        "p_miss_facade": 0.0,
        "p_inc_facade": 0.28,
        "schedule_slack": Uncertain(0.0, 0.0, 5.0),
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

    def _spec(self, action):
        slack = float(self.param("schedule_slack"))
        if action == "strangler_counter_first":
            return (
                float(self.param("strangler_base")) + slack,
                0.0,
                float(self.param("p_miss_strangler")),
                float(self.param("p_inc_strangler")),
                float(self.param("repair")),
                float(self.param("incident_cutover")),
            )
        if action == "big_bang_rewrite":
            return (
                float(self.param("big_bang_base")) + slack,
                0.0,
                float(self.param("p_miss_big_bang")),
                float(self.param("p_inc_big_bang")),
                float(self.param("repair")),
                float(self.param("incident_cutover")),
            )
        return (
            float(self.param("facade_base")) + slack,
            float(self.param("facade_later")),
            float(self.param("p_miss_facade")),
            float(self.param("p_inc_facade")),
            0.0,
            float(self.param("incident_facade")),
        )

    def _finish(self, action, missed, incident):
        base, later, _p_miss, _p_inc, repair, incident_cost = self._spec(action)
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
        _base, _later, p_miss, p_inc, _repair, _cost = self._spec(action)
        missed = rng.random() < p_miss
        incident = rng.random() < p_inc
        return self._finish(action, missed, incident)

    def reward(self, state, action, next_state):
        return float(-next_state["days"])

    def is_terminal(self, state, t):
        return state["t"] >= 1

    def outcomes(self, state, action):
        _base, _later, p_miss, p_inc, _repair, _cost = self._spec(action)
        branches = []
        for missed, p_m in ((True, p_miss), (False, 1.0 - p_miss)):
            for incident, p_i in ((True, p_inc), (False, 1.0 - p_inc)):
                probability = p_m * p_i
                if probability > 0.0:
                    branches.append((probability, self._finish(action, missed, incident)))
        return branches
