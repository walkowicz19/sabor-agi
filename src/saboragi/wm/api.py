"""The world-model API that compiled models are written against.

A model is a finite-horizon, discrete-time stochastic decision process:

- ``initial_state()`` returns the starting state (a JSON-serializable dict).
- ``actions(state)`` lists the legal action names in a non-terminal state.
- ``transition(state, action, rng)`` samples the next state. It must be a pure
  function of its arguments: same inputs plus same ``rng`` state give the same
  outputs. Use *only* ``rng`` for randomness (never the global ``random``
  module, ``time``, etc.), and never mutate the input ``state``.
- ``reward(state, action, next_state)`` is the one-step reward (a finite float).
- ``is_terminal(state, t)`` reports whether ``state`` at step ``t`` ends the
  episode. Every episode must terminate at some ``t <= horizon``.
- ``outcomes(state, action)`` (optional) enumerates ``(probability, next_state)``
  pairs. Defining it enables the exact solver; ``transition`` sampling
  frequencies must then match these probabilities (checked automatically).
- ``events`` (optional) maps names to indicator functions of a state, used for
  calibrated probability questions (e.g. ``"bankrupt"``). Values must be in
  ``[0, 1]``.
- ``params`` holds numeric constants; entries may be :class:`Uncertain` to mark
  parameters the compiler is unsure about, with a plausible ``[low, high]``
  range used by sensitivity analysis. Read them via ``self.param(name)`` so
  that solver overrides keep working.

Physical and mathematical steps (a vehicle, a small liquid grid, a machine,
an agent loop, a short forecast) belong inside ``transition`` and
``outcomes``. Call the pure helpers in ``saboragi.sim``; one call is one
time step. The solver still searches the resulting discrete process.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

State = dict[str, Any]
EventFn = Callable[[State], float]


@dataclass(frozen=True)
class Uncertain:
    """A numeric parameter with a best guess and a plausible range."""

    value: float
    low: float
    high: float

    def __post_init__(self) -> None:
        for name in ("value", "low", "high"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"Uncertain.{name} must be a number, got {v!r}")
        if not self.low <= self.value <= self.high:
            raise ValueError(
                f"Uncertain requires low <= value <= high, got "
                f"({self.low}, {self.value}, {self.high})"
            )


def canonical(state: State) -> str:
    """Stable string key for a state (used to de-duplicate / hash states)."""
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


class Model:
    """Base class for compiled world models. Subclass as ``World``."""

    horizon: int = 10
    params: dict[str, Uncertain | float] = {}
    state_bounds: dict[str, tuple[float, float]] = {}
    events: dict[str, EventFn] = {}

    def __init__(self) -> None:
        self._param_overrides: dict[str, float] = {}

    # -- parameters -----------------------------------------------------
    def param(self, name: str) -> float:
        """Numeric value of a parameter, honoring solver overrides."""
        if name in self._param_overrides:
            return self._param_overrides[name]
        value = self.params[name]
        return value.value if isinstance(value, Uncertain) else value

    def set_param_override(self, name: str, value: float) -> None:
        if name not in self.params:
            raise KeyError(f"unknown param {name!r}")
        self._param_overrides[name] = value

    def clear_param_overrides(self) -> None:
        self._param_overrides.clear()

    def uncertain_params(self) -> dict[str, Uncertain]:
        return {k: v for k, v in self.params.items() if isinstance(v, Uncertain)}

    # -- dynamics (override in subclasses) ------------------------------
    def initial_state(self) -> State:
        raise NotImplementedError

    def actions(self, state: State) -> list[str]:
        raise NotImplementedError

    def transition(self, state: State, action: str, rng: random.Random) -> State:
        raise NotImplementedError

    def reward(self, state: State, action: str, next_state: State) -> float:
        raise NotImplementedError

    def is_terminal(self, state: State, t: int) -> bool:
        raise NotImplementedError

    def outcomes(self, state: State, action: str) -> list[tuple[float, State]] | None:
        """Explicit (probability, next_state) distribution. None = sampling only."""
        return None

    def default_policy(self, state: State, rng: random.Random) -> str | None:
        """Rollout policy for Monte Carlo. None = uniform random over actions."""
        return None
