"""Shared helpers for problem-family generators.

Each family renders a self-contained ``World`` source string (parameters baked
in as literals, zero-arg constructor), then execs it in-process to compute
exact ground truth. The same source is stored on the Problem as oracle code.
"""

from __future__ import annotations

import copy
import random

from saboragi.solve.exact import try_exact
from saboragi.solve.types import SolveResult

HEADER = "from saboragi.wm import Model\n\n\n"

MAX_ENUMERATED_STATES = 100_000


def assemble(class_source: str) -> str:
    return HEADER + class_source.rstrip() + "\n"


def load_world(code: str):
    namespace: dict = {}
    exec(code, namespace)
    return namespace["World"]()


def normalize_dist(levels: list) -> list[tuple]:
    """Scale probabilities to sum to exactly 1 (fix last level)."""
    total = sum(p for _, p in levels)
    scaled = [(v, p / total) for v, p in levels]
    fixed = [(v, p) for v, p in scaled[:-1]]
    fixed.append((scaled[-1][0], 1.0 - sum(p for _, p in fixed)))
    return fixed


def ground_truth(code: str, actions: list[str]) -> SolveResult | None:
    """Exact solution of the rendered model, or None if too large."""
    model = load_world(code)
    result = try_exact(model, actions, state_limit=MAX_ENUMERATED_STATES, p5_samples=0)
    if result is None:
        return None
    if result.diagnostics.get("states_enumerated", 0) > MAX_ENUMERATED_STATES:
        return None
    values = [o.ev for o in result.options]
    if max(values) - min(values) <= 1e-9:
        return None  # degenerate: every choice is equally good
    return result


def prob_words(prob: float) -> str:
    """'0.3' -> '30%' for descriptions."""
    return f"{prob * 100:g}%"


def sampled_actions(model, n: int = 1) -> list[str]:
    return model.actions(copy.deepcopy(model.initial_state()))


def roll_params(rng: random.Random, spec: dict) -> dict:
    """Draw each param: (low, high) tuple -> uniform; list -> choice."""
    out = {}
    for name, value in spec.items():
        if isinstance(value, tuple):
            out[name] = rng.uniform(*value)
        elif isinstance(value, list):
            out[name] = rng.choice(value)
        else:
            out[name] = value
    return out
