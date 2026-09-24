"""Solver tests: exact values, sampler consistency, selector routing."""

import pytest

from saboragi.solve.mcts import mcts
from saboragi.solve.montecarlo import monte_carlo
from saboragi.solve.select import solve
from saboragi.solve.types import SolveResult
from tests.reference_models import dice_game, gamble, inventory


def _actions(model):
    import copy

    return model.actions(copy.deepcopy(model.initial_state()))


def test_exact_gamble_values():
    result = solve(gamble.World(), seed=0)
    assert result.solver == "exact" and result.exact
    ev = {o.action: o.ev for o in result.options}
    assert ev["safe"] == pytest.approx(10.0)
    assert ev["risky"] == pytest.approx(10.0)
    assert ev["longshot"] == pytest.approx(-4.5)
    assert result.best in {"safe", "risky"}
    assert result.option("longshot").p_events["jackpot"] == pytest.approx(0.05)
    assert result.option("safe").worst_case_p5 == pytest.approx(10.0)


def test_exact_inventory_values():
    result = solve(inventory.World(), seed=0)
    assert result.solver == "exact"
    assert result.best == "order_20"
    ev = {o.action: o.ev for o in result.options}
    assert ev["order_0"] == pytest.approx(91.06, abs=0.01)
    assert ev["order_20"] == pytest.approx(96.85, abs=0.01)
    assert ev["order_40"] == pytest.approx(68.30, abs=0.01)


def test_exact_dice_values():
    result = solve(dice_game.World(), seed=0)
    assert result.solver == "exact"
    assert result.best == "roll"
    assert result.option("roll").ev == pytest.approx(8.1418, abs=0.001)
    assert result.option("roll").p_events["bust"] == pytest.approx(0.6412, abs=0.001)
    assert result.option("stop").ev == pytest.approx(0.0)


def test_result_roundtrip_json():
    result = solve(gamble.World(), seed=0)
    clone = SolveResult.from_dict(result.to_dict())
    assert clone.best == result.best
    assert [o.ev for o in clone.options] == [o.ev for o in result.options]


def test_montecarlo_matches_exact_on_gamble():
    exact = {o.action: o.ev for o in solve(gamble.World(), seed=0).options}
    mc = monte_carlo(gamble.World(), _actions(gamble.World()), n_rollouts=6000, seed=1)
    assert mc.solver == "montecarlo" and not mc.exact
    for opt in mc.options:
        assert opt.ci_lo <= exact[opt.action] <= opt.ci_hi, opt.action
    assert mc.best in {"safe", "risky"}
    assert mc.option("longshot").p_events["jackpot"] == pytest.approx(0.05, abs=0.02)


def test_mcts_matches_exact_on_inventory():
    exact = {o.action: o.ev for o in solve(inventory.World(), seed=0).options}
    result = mcts(inventory.World(), _actions(inventory.World()), iterations=20000, seed=1)
    assert result.solver == "mcts"
    for opt in result.options:
        assert opt.ci_lo <= exact[opt.action] <= opt.ci_hi, (opt.action, opt.ev)
    assert result.best == "order_20"


def test_mcts_matches_exact_on_dice():
    exact = {o.action: o.ev for o in solve(dice_game.World(), seed=0).options}
    result = mcts(dice_game.World(), _actions(dice_game.World()), iterations=60000, seed=1)
    for opt in result.options:
        assert opt.ci_lo <= exact[opt.action] <= opt.ci_hi, (opt.action, opt.ev)


def test_selector_routes_sampling_only_models():
    class SamplingGamble(gamble.World):
        def outcomes(self, state, action):
            return None

    mc = solve(SamplingGamble(), seed=0)
    assert mc.solver == "montecarlo"
    assert mc.best in {"safe", "risky"}

    class SamplingInventory(inventory.World):
        def outcomes(self, state, action):
            return None

    tree = solve(SamplingInventory(), seed=0)
    assert tree.solver == "mcts"
    assert tree.best == "order_20"


def test_selector_falls_back_when_space_too_large():
    result = solve(inventory.World(), seed=0, exact_state_limit=5, mcts_iterations=20000)
    assert result.solver == "mcts"
    assert result.best == "order_20"


def test_first_actions_restriction():
    result = solve(gamble.World(), ["safe", "longshot"], seed=0)
    assert {o.action for o in result.options} == {"safe", "longshot"}
    assert result.best == "safe"
