import math
import random
import numpy
import itertools
import functools
import collections
import dataclasses
import statistics
from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 1

    params = {
        "strangler_base": 25.0,
        "strangler_p_miss": 0.12,
        "strangler_p_incident": 0.05,
        "strangler_repair": 25.0,
        "strangler_incident_cost": 40.0,
        "strangler_later": 0.0,
        "big_bang_base": 30.0,
        "big_bang_p_miss": 0.35,
        "big_bang_p_incident": 0.08,
        "big_bang_repair": 25.0,
        "big_bang_incident_cost": 40.0,
        "big_bang_later": 0.0,
        "facade_base": 10.0,
        "facade_p_miss": 0.0,
        "facade_p_incident": 0.30,
        "facade_repair": 25.0,
        "facade_incident_cost": 80.0,
        "facade_later": 30.0,
    }

    state_bounds = {
        "days": (0.0, 300.0),
        "missed": (0.0, 1.0),
        "incident": (0.0, 1.0),
        "done": (0.0, 1.0),
        "step": (0.0, 1.0),
    }

    events = {
        "credential_incident": lambda s: float(s.get("incident", 0.0)),
        "missed_behavior": lambda s: float(s.get("missed", 0.0)),
    }

    def initial_state(self):
        return {
            "days": 0.0,
            "missed": 0.0,
            "incident": 0.0,
            "done": 0.0,
            "step": 0.0,
            "action": "",
        }

    def actions(self, state):
        return [
            "strangler_registration_first",
            "big_bang_rewrite",
            "facade_keep_cobol",
        ]

    def _action_params(self, action):
        if action == "strangler_registration_first":
            return (
                self.param("strangler_base"),
                self.param("strangler_later"),
                self.param("strangler_p_miss"),
                self.param("strangler_repair"),
                self.param("strangler_p_incident"),
                self.param("strangler_incident_cost"),
            )
        if action == "big_bang_rewrite":
            return (
                self.param("big_bang_base"),
                self.param("big_bang_later"),
                self.param("big_bang_p_miss"),
                self.param("big_bang_repair"),
                self.param("big_bang_p_incident"),
                self.param("big_bang_incident_cost"),
            )
        if action == "facade_keep_cobol":
            return (
                self.param("facade_base"),
                self.param("facade_later"),
                self.param("facade_p_miss"),
                self.param("facade_repair"),
                self.param("facade_p_incident"),
                self.param("facade_incident_cost"),
            )
        raise ValueError(f"unknown action: {action}")

    def _days(self, base, later, missed, repair, incident, incident_cost):
        return (
            float(base)
            + float(later)
            + (float(repair) if missed else 0.0)
            + (float(incident_cost) if incident else 0.0)
        )

    def _next_state(self, state, action, missed, incident, days):
        return {
            "days": float(days),
            "missed": 1.0 if missed else 0.0,
            "incident": 1.0 if incident else 0.0,
            "done": 1.0,
            "step": float(state.get("step", 0.0)) + 1.0,
            "action": str(action),
        }

    def transition(self, state, action, rng):
        base, later, p_miss, repair, p_incident, incident_cost = self._action_params(action)
        missed = bool(rng.random() < float(p_miss))
        incident = bool(rng.random() < float(p_incident))
        days = self._days(base, later, missed, repair, incident, incident_cost)
        return self._next_state(state, action, missed, incident, days)

    def reward(self, state, action, next_state):
        return -float(next_state["days"])

    def is_terminal(self, state, t):
        return bool(state.get("done", 0.0) >= 1.0) or (t >= self.horizon)

    def outcomes(self, state, action):
        base, later, p_miss, repair, p_incident, incident_cost = self._action_params(action)
        p_miss = float(p_miss)
        p_incident = float(p_incident)
        branches = []
        miss_opts = [False] if p_miss <= 0.0 else [False, True]
        for missed in miss_opts:
            p_m = (1.0 - p_miss) if not missed else p_miss
            if p_m <= 0.0:
                continue
            inc_opts = [False] if p_incident <= 0.0 else [False, True]
            for incident in inc_opts:
                p_i = (1.0 - p_incident) if not incident else p_incident
                if p_i <= 0.0:
                    continue
                prob = p_m * p_i
                days = self._days(base, later, missed, repair, incident, incident_cost)
                branches.append((prob, self._next_state(state, action, missed, incident, days)))
        total = sum(p for p, _ in branches)
        if total <= 0.0:
            raise ValueError("outcomes probabilities sum to zero")
        return [(p / total, s) for p, s in branches]
