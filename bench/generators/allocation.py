"""Safe vs bold projects with a rare catastrophe. Tests tail-risk reasoning."""

from __future__ import annotations

import random

from bench.generators.base import assemble, ground_truth, prob_words
from bench.problems import Problem


def _render(
    horizon: int,
    capital0: int,
    safe_yield: int,
    bold_yield: int,
    cata_p: float,
    cata_loss: int,
) -> str:
    lo = capital0 - cata_loss - 5
    hi = capital0 + horizon * bold_yield + 5
    return assemble(
        f"""class World(Model):
    horizon = {horizon}
    state_bounds = {{"t": (0, {horizon}), "capital": ({lo}, {hi}), "ruined": (0, 1)}}
    events = {{"catastrophe": lambda s: 1.0 if s["ruined"] == 1 else 0.0}}

    SAFE_YIELD = {safe_yield}
    BOLD_YIELD = {bold_yield}
    CATA_P = {cata_p!r}
    CATA_LOSS = {cata_loss}

    def initial_state(self):
        return {{"t": 0, "capital": {capital0}, "ruined": 0}}

    def actions(self, state):
        return ["project_safe", "project_bold"]

    def transition(self, state, action, rng):
        if action == "project_safe":
            return {{
                "t": state["t"] + 1,
                "capital": state["capital"] + self.SAFE_YIELD,
                "ruined": 0,
            }}
        if rng.random() < self.CATA_P:
            return {{
                "t": state["t"] + 1,
                "capital": state["capital"] - self.CATA_LOSS,
                "ruined": 1,
            }}
        return {{
            "t": state["t"] + 1,
            "capital": state["capital"] + self.BOLD_YIELD,
            "ruined": 0,
        }}

    def reward(self, state, action, next_state):
        return float(next_state["capital"] - state["capital"])

    def is_terminal(self, state, t):
        return state["ruined"] == 1 or state["t"] >= {horizon}

    def outcomes(self, state, action):
        if action == "project_safe":
            return [(
                1.0,
                {{"t": state["t"] + 1,
                  "capital": state["capital"] + self.SAFE_YIELD,
                  "ruined": 0}},
            )]
        return [
            (
                self.CATA_P,
                {{"t": state["t"] + 1,
                  "capital": state["capital"] - self.CATA_LOSS,
                  "ruined": 1}},
            ),
            (
                1 - self.CATA_P,
                {{"t": state["t"] + 1,
                  "capital": state["capital"] + self.BOLD_YIELD,
                  "ruined": 0}},
            ),
        ]
"""
    )


def generate(rng: random.Random, horizon: int, idx: int, seed: int) -> Problem | None:
    capital0 = rng.choice([100, 150, 200])
    safe_yield = rng.choice([8, 10, 12, 15])
    bold_yield = safe_yield + rng.choice([8, 10, 12, 15, 20])
    cata_p = round(rng.uniform(0.005, 0.03), 4)
    cata_loss = rng.choice([100, 150, 200, 250])
    code = _render(horizon, capital0, safe_yield, bold_yield, cata_p, cata_loss)
    actions = ["project_safe", "project_bold"]
    solved = ground_truth(code, actions)
    if solved is None:
        return None
    description = (
        f"You run a venture with ${capital0} capital for {horizon} seasons.\n"
        f"Each season you back one project. Project Safe pays ${safe_yield} "
        f"with no risk. Project Bold pays ${bold_yield}, but each season "
        f"there is a {prob_words(cata_p)} chance of a catastrophe that costs "
        f"${cata_loss} and ends the venture immediately."
    )
    return Problem(
        id=f"allocation-h{horizon}-{idx:03d}",
        family="resource_allocation",
        horizon=horizon,
        description=description,
        actions=actions,
        q_values={o.action: o.ev for o in solved.options},
        optimal=solved.best,
        event_name="catastrophe",
        event_description="the probability a catastrophe ends the venture",
        event_probs={o.action: o.p_events["catastrophe"] for o in solved.options},
        model_code=code,
        seed=seed,
    )
