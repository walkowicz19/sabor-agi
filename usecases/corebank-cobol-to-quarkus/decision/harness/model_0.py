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
        "big_bang_base": 30.0,
        "facade_base": 10.0,
        "facade_rewrite": 30.0,
        "miss_repair": 25.0,
        "cred_cost_cutover": 40.0,
        "cred_cost_facade": 80.0,
        "p_miss_strangler": 0.12,
        "p_cred_strangler": 0.05,
        "p_miss_big_bang": 0.35,
        "p_cred_big_bang": 0.08,
        "p_miss_facade": 0.0,
        "p_cred_facade": 0.30,
        "schedule_slack": Uncertain(0.0, 0.0, 5.0),
    }

    state_bounds = {
        "days": (0.0, 300.0),
        "credential_incident": (0.0, 1.0),
        "missed_behavior": (0.0, 1.0),
        "done": (0.0, 1.0),
        "action_id": (0.0, 3.0),
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
            "done": 0.0,
            "action_id": 0.0,
        }

    def actions(self, state):
        return [
            "strangler_registration_first",
            "big_bang_rewrite",
            "facade_keep_cobol",
        ]

    def _action_spec(self, action):
        slack = float(self.param("schedule_slack"))
        if action == "strangler_registration_first":
            return {
                "action_id": 1.0,
                "base": float(self.param("strangler_base")) + slack,
                "p_miss": float(self.param("p_miss_strangler")),
                "p_cred": float(self.param("p_cred_strangler")),
                "miss_cost": float(self.param("miss_repair")),
                "cred_cost": float(self.param("cred_cost_cutover")),
            }
        if action == "big_bang_rewrite":
            return {
                "action_id": 2.0,
                "base": float(self.param("big_bang_base")) + slack,
                "p_miss": float(self.param("p_miss_big_bang")),
                "p_cred": float(self.param("p_cred_big_bang")),
                "miss_cost": float(self.param("miss_repair")),
                "cred_cost": float(self.param("cred_cost_cutover")),
            }
        if action == "facade_keep_cobol":
            return {
                "action_id": 3.0,
                "base": (
                    float(self.param("facade_base"))
                    + float(self.param("facade_rewrite"))
                    + slack
                ),
                "p_miss": float(self.param("p_miss_facade")),
                "p_cred": float(self.param("p_cred_facade")),
                "miss_cost": float(self.param("miss_repair")),
                "cred_cost": float(self.param("cred_cost_facade")),
            }
        raise ValueError(f"unknown action: {action}")

    def transition(self, state, action, rng):
        spec = self._action_spec(action)
        missed = 1.0 if rng.random() < spec["p_miss"] else 0.0
        cred = 1.0 if rng.random() < spec["p_cred"] else 0.0
        days = spec["base"] + missed * spec["miss_cost"] + cred * spec["cred_cost"]
        return {
            "days": float(days),
            "credential_incident": float(cred),
            "missed_behavior": float(missed),
            "done": 1.0,
            "action_id": float(spec["action_id"]),
        }

    def reward(self, state, action, next_state):
        return -float(next_state["days"] - state["days"])

    def is_terminal(self, state, t):
        return bool(t >= self.horizon or state["done"] >= 1.0)

    def outcomes(self, state, action):
        spec = self._action_spec(action)
        out = []
        for miss in (0.0, 1.0):
            for cred in (0.0, 1.0):
                p_miss = spec["p_miss"] if miss == 1.0 else (1.0 - spec["p_miss"])
                p_cred = spec["p_cred"] if cred == 1.0 else (1.0 - spec["p_cred"])
                p = p_miss * p_cred
                if p <= 0.0:
                    continue
                days = spec["base"] + miss * spec["miss_cost"] + cred * spec["cred_cost"]
                next_state = {
                    "days": float(days),
                    "credential_incident": float(cred),
                    "missed_behavior": float(miss),
                    "done": 1.0,
                    "action_id": float(spec["action_id"]),
                }
                out.append((float(p), next_state))
        return out
