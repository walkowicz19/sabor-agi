"""Physical step helpers and the worlds that decide with them."""

import math
from pathlib import Path

from saboragi.sandbox.runner import run_validate
from saboragi.sim import (
    agent_step,
    bicycle_step,
    euler,
    exchange,
    linear_project,
    machine_step,
    rk4,
    transfer,
)
from saboragi.solve.exact import try_exact

ROOT = Path(__file__).parent / "reference_models"


def _world(name: str):
    namespace: dict = {}
    exec((ROOT / name).read_text(encoding="utf-8"), namespace)
    return namespace["World"]()


def test_rk4_tracks_exponential_decay_closer_than_euler():
    def decay(y):
        return (-y[0],)

    exact = math.exp(-1.0)
    rk = (1.0,)
    eu = (1.0,)
    for _ in range(10):
        rk = rk4(rk, decay, 0.1)
        eu = euler(eu, decay, 0.1)
    assert abs(rk[0] - exact) < 1e-5
    assert abs(rk[0] - exact) < abs(eu[0] - exact)


def test_bicycle_rolls_straight_when_the_wheel_is_centered():
    x, y, heading, speed = 0.0, 0.0, 0.0, 0.0
    for _ in range(2):
        x, y, heading, speed = bicycle_step(x, y, heading, speed, 0.0, 1.0, 1.0, 2.0)
    assert (x, y, heading, speed) == (3.0, 0.0, 0.0, 2.0)


def test_exchange_conserves_liquid_and_levels_a_step():
    leveled = exchange([2.0, 0.0], rate=1.0, dt=1.0)
    assert leveled == [1.0, 1.0]
    assert sum(leveled) == 2.0


def test_transfer_moves_only_what_is_there():
    levels, moved = transfer([0.2, 0.0], 0, 1, 0.5)
    assert moved == 0.2
    assert levels == [0.0, 0.2]


def test_linear_project_reproduces_an_arithmetic_series():
    assert linear_project([0.0, 1.0, 2.0, 3.0], steps=2) == [4.0, 5.0]


def test_agent_and_machine_steps_follow_their_rules():
    assert agent_step(1, "finish", needed=2) == (1, False, True)
    assert agent_step(2, "finish", needed=2) == (2, True, False)
    assert machine_step(1.0, 2.0, "run", heat_limit=2.0) == (1.0, 2.0, True)
    assert machine_step(1.0, 2.0, "cool", heat_limit=2.0) == (1.0, 1.0, False)


def test_physical_worlds_pick_the_exact_action():
    expected = {
        "drive.py": ("accelerate", 3.0),
        "tank.py": ("drain", 0.5),
        "agent_loop.py": ("lookup", 5.0),
        "machine.py": ("run", 3.0),
        "forecast.py": ("trust_trend", 0.0),
    }
    for name, (action, value) in expected.items():
        code = (ROOT / name).read_text(encoding="utf-8")
        checked = run_validate(code, timeout=60)
        assert checked.ok, (name, checked.errors, checked.data)
        model = _world(name)
        solved = try_exact(model, model.actions(model.initial_state()), p5_samples=0)
        assert solved is not None
        assert solved.best == action
        winner = next(option for option in solved.options if option.action == action)
        assert winner.ev == value
