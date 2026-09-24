from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 1
    params = {
        "strangler_base": 25.0,
        "bigbang_base": 30.0,
        "facade_base": 10.0,
        "facade_later": 30.0,
        "repair_cost": 25.0,
        "incident_cost_cutover": 40.0,
        "incident_cost_facade": Uncertain(80.0, 55.0, 110.0),
        "p_miss_strangler": 0.12,
        "p_inc_strangler": 0.05,
        "p_miss_bigbang": 0.35,
        "p_inc_bigbang": 0.08,
        "p_miss_facade": 0.0,
        "p_inc_facade": 0.30,
    }
    state_bounds = {
        "days": (0.0, 300.0),
        "credential_incident": (0.0, 1.0),
        "missed_behavior": (0.0, 1.0),
        "step": (0.0, 1.0),
    }
    events = {
        "credential_incident": lambda s: float(s["credential_incident"]),
        "missed_behavior": lambda s: float(s["missed_behavior"]),
    }

    def initial_state(self):
        return {
            "days": 0.0,
            "credential_incident": 0.0,
            "missed_behavior": 0.0,
            "step": 0.0,
        }

    def actions(self, state):
        return [
            "strangler_registration_first",
            "big_bang_rewrite",
            "facade_keep_cobol",
        ]

    def _plan(self, action):
        if action == "strangler_registration_first":
            return (
                self.param("strangler_base"),
                0.0,
                self.param("p_miss_strangler"),
                self.param("p_inc_strangler"),
                self.param("incident_cost_cutover"),
            )
        if action == "big_bang_rewrite":
            return (
                self.param("bigbang_base"),
                0.0,
                self.param("p_miss_bigbang"),
                self.param("p_inc_bigbang"),
                self.param("incident_cost_cutover"),
            )
        return (
            self.param("facade_base"),
            self.param("facade_later"),
            self.param("p_miss_facade"),
            self.param("p_inc_facade"),
            self.param("incident_cost_facade"),
        )

    def transition(self, state, action, rng):
        base, later, p_miss, p_inc, inc_cost = self._plan(action)
        repair = self.param("repair_cost")
        missed = 1.0 if rng.random() < p_miss else 0.0
        incident = 1.0 if rng.random() < p_inc else 0.0
        days = base + later
        if missed:
            days += repair
        if incident:
            days += inc_cost
        return {
            "days": float(days),
            "credential_incident": float(incident),
            "missed_behavior": float(missed),
            "step": 1.0,
        }

    def reward(self, state, action, next_state):
        return -float(next_state["days"])

    def is_terminal(self, state, t):
        return t >= self.horizon

    def outcomes(self, state, action):
        base, later, p_miss, p_inc, inc_cost = self._plan(action)
        repair = self.param("repair_cost")
        results = []
        for miss, p_m in ((0.0, 1.0 - p_miss), (1.0, p_miss)):
            for inc, p_i in ((0.0, 1.0 - p_inc), (1.0, p_inc)):
                p = p_m * p_i
                if p <= 0.0:
                    continue
                days = base + later
                if miss:
                    days += repair
                if inc:
                    days += inc_cost
                results.append(
                    (
                        p,
                        {
                            "days": float(days),
                            "credential_incident": float(inc),
                            "missed_behavior": float(miss),
                            "step": 1.0,
                        },
                    )
                )
        return results
