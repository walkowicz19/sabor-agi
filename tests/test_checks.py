"""Validity-check tests: reference models pass, broken models fail loudly."""

import copy

from saboragi.validate.checks import run_checks
from tests.reference_models import dice_game, gamble, inventory


def test_reference_models_pass():
    for module in (gamble, inventory, dice_game):
        report = run_checks(module.World())
        assert report.ok, (module.__name__, report.to_dict())
        assert report.errors == []


def test_rejects_out_of_bounds():
    class Bad(gamble.World):
        def transition(self, state, action, rng):
            nxt = super().transition(state, action, rng)
            nxt = copy.deepcopy(nxt)
            nxt["payoff"] = 10_000.0
            return nxt

    report = run_checks(Bad())
    assert not report.ok
    assert any(e.code == "out_of_bounds" for e in report.errors)


def test_rejects_never_terminal():
    class Bad(gamble.World):
        def is_terminal(self, state, t):
            return False

    report = run_checks(Bad(), n_rollouts=5)
    assert not report.ok
    assert any(e.code == "never_terminal" for e in report.errors)


def test_rejects_ineffective_action():
    class Bad(gamble.World):
        def actions(self, state):
            return super().actions(state) + ["noop"]

        def transition(self, state, action, rng):
            if action == "noop":
                return copy.deepcopy(state)
            return super().transition(state, action, rng)

    report = run_checks(Bad())
    assert not report.ok
    assert any(e.code == "action_no_effect" for e in report.errors)


def test_rejects_bad_outcomes_sum():
    class Bad(gamble.World):
        def outcomes(self, state, action):
            return [(0.5, {"t": 1, "payoff": 10.0})]

    report = run_checks(Bad())
    assert not report.ok
    assert any(e.code == "bad_outcomes" for e in report.errors)


def test_rejects_outcomes_mismatch():
    class Bad(gamble.World):
        def outcomes(self, state, action):
            if action == "safe":
                return [(0.5, {"t": 1, "payoff": 10.0}), (0.5, {"t": 1, "payoff": 11.0})]
            return super().outcomes(state, action)

    report = run_checks(Bad())
    assert not report.ok
    assert any(e.code == "outcomes_mismatch" for e in report.errors)
