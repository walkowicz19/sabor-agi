"""Sandbox runner tests: trusted code validates, bad code is contained."""

from pathlib import Path

from saboragi.sandbox.runner import run_analyze, run_validate

GAMBLE_CODE = (Path(__file__).parent / "reference_models" / "gamble.py").read_text()

INFINITE_LOOP = """
from saboragi.wm import Model


class World(Model):
    horizon = 5
    state_bounds = {"t": (0, 5)}

    def initial_state(self):
        return {"t": 0}

    def actions(self, state):
        return ["a"]

    def transition(self, state, action, rng):
        while True:
            pass

    def reward(self, state, action, next_state):
        return 0.0

    def is_terminal(self, state, t):
        return t >= 5
"""

BANNED_IMPORT = "import os\n"


def test_validates_reference_model_in_sandbox():
    result = run_validate(GAMBLE_CODE, timeout=60)
    assert result.ok, result.errors
    assert result.data["report"]["ok"] is True


def test_guard_rejects_before_spawn():
    result = run_validate(BANNED_IMPORT, timeout=10)
    assert not result.ok
    assert result.stage == "guard"


def test_infinite_loop_times_out():
    result = run_validate(INFINITE_LOOP, timeout=8)
    assert not result.ok
    assert result.stage == "timeout"


def test_analyze_returns_exact_solution():
    result = run_analyze(GAMBLE_CODE, ["safe", "risky", "longshot"], timeout=120)
    assert result.ok, result.errors
    solved = result.data["result"]
    assert solved["solver"] == "exact"
    assert solved["best"] in {"safe", "risky"}
    ev = {o["action"]: o["ev"] for o in solved["options"]}
    assert ev["safe"] == 10.0
    assert ev["longshot"] == -4.5
