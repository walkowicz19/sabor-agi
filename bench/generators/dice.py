"""Stop-or-continue dice game. Tests optimal-stopping reasoning."""

from __future__ import annotations

import random

from bench.generators.base import assemble, ground_truth
from bench.problems import Problem


def _render(horizon: int, sides: int, start: int) -> str:
    faces = ",\n            ".join(
        f'({1 / sides!r}, {{"t": state["t"] + 1, "total": 0, "phase": "done"}})'
        if face == 1
        else f'({1 / sides!r}, {{"t": state["t"] + 1, '
        f'"total": state["total"] + {face}, "phase": "play"}})'
        for face in range(1, sides + 1)
    )
    return assemble(
        f"""class World(Model):
    horizon = {horizon}
    state_bounds = {{"t": (0, {horizon}), "total": (0, {horizon * sides + start})}}
    events = {{"bust": lambda s: 1.0 if s["phase"] == "done" and s["total"] == 0 else 0.0}}

    SIDES = {sides}

    def initial_state(self):
        return {{"t": 0, "total": {start}, "phase": "play"}}

    def actions(self, state):
        return ["roll", "stop"]

    def transition(self, state, action, rng):
        if action == "stop":
            return {{"t": state["t"] + 1, "total": state["total"], "phase": "done"}}
        die = rng.randint(1, self.SIDES)
        if die == 1:
            return {{"t": state["t"] + 1, "total": 0, "phase": "done"}}
        return {{"t": state["t"] + 1, "total": state["total"] + die, "phase": "play"}}

    def reward(self, state, action, next_state):
        if state["phase"] == "play" and next_state["phase"] == "done" and action == "stop":
            return float(next_state["total"])
        return 0.0

    def is_terminal(self, state, t):
        return state["phase"] == "done" or t >= {horizon}

    def outcomes(self, state, action):
        if action == "stop":
            return [(1.0, {{"t": state["t"] + 1, "total": state["total"], "phase": "done"}})]
        return [
            {faces}
        ]
"""
    )


def generate(rng: random.Random, horizon: int, idx: int, seed: int) -> Problem | None:
    sides = rng.choice([4, 6, 8])
    start = rng.choice([0, 2, 4, 6, 8, 10, 12])
    code = _render(horizon, sides, start)
    actions = ["roll", "stop"]
    solved = ground_truth(code, actions)
    if solved is None:
        return None
    description = (
        f"You have banked {start} points with {horizon} rolls left at most.\n"
        f"Each turn you may STOP and keep your banked points, or ROLL a "
        f"{sides}-sided die (faces 1-{sides}). Rolling a 1 busts: you lose "
        f"everything banked and the game ends. Any other face adds its value "
        f"to your bank and you may continue."
    )
    return Problem(
        id=f"dice-h{horizon}-{idx:03d}",
        family="dice_game",
        horizon=horizon,
        description=description,
        actions=actions,
        q_values={o.action: o.ev for o in solved.options},
        optimal=solved.best,
        event_name="bust",
        event_description="the probability you bust (roll a 1 before stopping)",
        event_probs={o.action: o.p_events["bust"] for o in solved.options},
        model_code=code,
        seed=seed,
    )
