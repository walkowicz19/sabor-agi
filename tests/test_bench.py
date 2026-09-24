"""Step-3 tests: suite builds, ground truth is consistent, oracle code runs."""

import pytest

from bench.generate import FAMILIES, TIERS, build_suite
from saboragi.sandbox.runner import run_analyze


def test_small_suite_builds():
    problems = build_suite(seed=123, per_family_per_tier=1, tiers=(1, 3))
    assert len(problems) == len(FAMILIES) * 2
    for problem in problems:
        assert problem.optimal == max(problem.q_values, key=lambda a: problem.q_values[a])
        assert problem.ev_range > 0
        assert problem.regret(problem.optimal) == 0.0
        for action in problem.actions:
            assert 0.0 <= problem.event_probs[action] <= 1.0
            assert action in problem.description


def test_default_suite_shape():
    problems = build_suite(seed=0, per_family_per_tier=2, tiers=TIERS)
    by_tier: dict[int, int] = {}
    for problem in problems:
        by_tier[problem.horizon] = by_tier.get(problem.horizon, 0) + 1
    assert by_tier == {1: 10, 3: 10, 10: 10}


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_oracle_code_reproduces_ground_truth(family):
    problems = build_suite(seed=7, per_family_per_tier=1, tiers=(3,))
    problem = next(p for p in problems if p.family == family)
    result = run_analyze(problem.model_code, problem.actions, timeout=120)
    assert result.ok, result.errors
    solved = result.data["result"]
    assert solved["best"] == problem.optimal
    for option in solved["options"]:
        assert option["ev"] == pytest.approx(problem.q_values[option["action"]])
