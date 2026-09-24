"""Operations-research framing. Day costs stay as stated. Incident chances are judgments, so they carry a range. The facade rewrite is not folded into the incident cost."""

from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 1
    params = {
        "strangler_base": 22.0,
        "big_bang_base": 28.0,
        "facade_base": 8.0,
        "facade_later": 26.0,
        "repair_if_miss": 18.0,
        "incident_during_cutover": 35.0,
        "incident_if_facade_kept": 70.0,
        "p_miss_strangler": 0.10,
        "p_miss_big_bang": 0.32,
        "p_miss_facade": 0.0,
        "p_inc_strangler": Uncertain(0.06, 0.02, 0.12),
        "p_inc_big_bang": Uncertain(0.09, 0.04, 0.16),
        "p_inc_facade": Uncertain(0.28, 0.15, 0.45),
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

    def _terms(self, action):
        if action == "strangler_counter_first":
            return (
                float(self.param("strangler_base")),
                0.0,
                float(self.param("p_miss_strangler")),
                float(self.param("p_inc_strangler")),
                float(self.param("repair_if_miss")),
                float(self.param("incident_during_cutover")),
            )
        if action == "big_bang_rewrite":
            return (
                float(self.param("big_bang_base")),
                0.0,
                float(self.param("p_miss_big_bang")),
                float(self.param("p_inc_big_bang")),
                float(self.param("repair_if_miss")),
                float(self.param("incident_during_cutover")),
            )
        return (
            float(self.param("facade_base")),
            float(self.param("facade_later")),
            float(self.param("p_miss_facade")),
            float(self.param("p_inc_facade")),
            0.0,
            float(self.param("incident_if_facade_kept")),
        )

    def _finish(self, action, missed, incident):
        base, later, _p_miss, _p_inc, repair, incident_cost = self._terms(action)
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
        _base, _later, p_miss, p_inc, _repair, _cost = self._terms(action)
        missed = rng.random() < p_miss
        incident = rng.random() < p_inc
        return self._finish(action, missed, incident)

    def reward(self, state, action, next_state):
        return float(-next_state["days"])

    def is_terminal(self, state, t):
        return state["t"] >= 1

    def outcomes(self, state, action):
        _base, _later, p_miss, p_inc, _repair, _cost = self._terms(action)
        branches = []
        for missed, p_m in ((True, p_miss), (False, 1.0 - p_miss)):
            for incident, p_i in ((True, p_inc), (False, 1.0 - p_inc)):
                probability = p_m * p_i
                if probability > 0.0:
                    branches.append((probability, self._finish(action, missed, incident)))
        return branches
