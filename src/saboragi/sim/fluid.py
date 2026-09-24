"""Liquid on a short row of cells.

``exchange`` moves volume between neighbors and cannot overshoot, so a step
never reverses the slope of a pair. ``transfer`` moves a requested amount
from one cell to another. Both conserve the total.
"""

from __future__ import annotations


def exchange(heights: list[float], rate: float, dt: float) -> list[float]:
    """One explicit exchange across every shared wall."""
    levels = [float(value) for value in heights]
    for index in range(len(levels) - 1):
        diff = levels[index] - levels[index + 1]
        limit = abs(diff) / 2
        flow = rate * diff * dt
        if flow > limit:
            flow = limit
        elif flow < -limit:
            flow = -limit
        levels[index] -= flow
        levels[index + 1] += flow
    return levels


def transfer(heights: list[float], src: int, dst: int, amount: float) -> tuple[list[float], float]:
    """Move up to ``amount`` from ``src`` to ``dst``. Returns levels and the amount moved."""
    levels = [float(value) for value in heights]
    moved = min(max(0.0, amount), levels[src])
    levels[src] -= moved
    levels[dst] += moved
    return levels, moved
