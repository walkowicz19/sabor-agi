"""Fixed-step integrators for a small ordinary differential equation.

``y`` is a tuple of floats. ``deriv(y)`` returns a tuple of the same length.
"""

from __future__ import annotations

from collections.abc import Callable

Deriv = Callable[[tuple[float, ...]], tuple[float, ...]]


def _scaled(y: tuple[float, ...], k: tuple[float, ...], scale: float) -> tuple[float, ...]:
    return tuple(yi + scale * ki for yi, ki in zip(y, k, strict=True))


def euler(y: tuple[float, ...], deriv: Deriv, dt: float) -> tuple[float, ...]:
    """One forward-Euler step."""
    return _scaled(y, deriv(y), dt)


def rk4(y: tuple[float, ...], deriv: Deriv, dt: float) -> tuple[float, ...]:
    """One classical fourth-order Runge-Kutta step."""
    k1 = deriv(y)
    k2 = deriv(_scaled(y, k1, dt / 2))
    k3 = deriv(_scaled(y, k2, dt / 2))
    k4 = deriv(_scaled(y, k3, dt))
    return tuple(
        yi + dt * (a + 2 * b + 2 * c + d) / 6
        for yi, a, b, c, d in zip(y, k1, k2, k3, k4, strict=True)
    )
