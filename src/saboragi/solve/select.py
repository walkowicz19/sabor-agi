"""Automatic solver selection: exact when possible, else MCTS or Monte Carlo."""

from __future__ import annotations

import copy

from saboragi.solve.exact import try_exact
from saboragi.solve.mcts import mcts
from saboragi.solve.montecarlo import monte_carlo
from saboragi.solve.types import SolveResult
from saboragi.wm.api import Model


def solve(
    model: Model,
    first_actions: list[str] | None = None,
    *,
    seed: int = 0,
    exact_state_limit: int = 200_000,
    mcts_iterations: int = 20_000,
    mc_rollouts: int = 5_000,
) -> SolveResult:
    """Solve the model and score each first action.

    - Exact (backward induction) when ``outcomes()`` covers the reachable
      space within ``exact_state_limit`` states.
    - Monte Carlo when ``horizon == 1`` (one-shot choice).
    - MCTS with chance nodes otherwise.
    """
    if first_actions is None:
        first_actions = model.actions(copy.deepcopy(model.initial_state()))

    exact = try_exact(model, first_actions, state_limit=exact_state_limit, seed=seed)
    if exact is not None:
        return exact
    if model.horizon == 1:
        return monte_carlo(model, first_actions, n_rollouts=mc_rollouts, seed=seed)
    return mcts(model, first_actions, iterations=mcts_iterations, seed=seed)
