"""Discrete loops: a tool-using agent, and a machine that heats as it runs."""

from __future__ import annotations


def agent_step(facts: int, action: str, needed: int) -> tuple[int, bool, bool]:
    """One turn of a gather-then-finish loop.

    ``lookup`` adds one fact, capped at ``needed``. ``finish`` completes the
    loop when enough facts are in hand, and is premature otherwise.
    Returns ``(facts, finished, premature)``.
    """
    if action == "lookup":
        return min(facts + 1, needed), False, False
    if action == "finish":
        ready = facts >= needed
        return facts, ready, not ready
    raise ValueError(f"unknown agent action {action!r}")


def machine_step(
    parts: float, heat: float, action: str, heat_limit: float
) -> tuple[float, float, bool]:
    """One cycle of a press.

    ``run`` makes one part and adds one unit of heat, until ``heat`` is
    already at the limit: then it jams, makes nothing, and stays hot.
    ``cool`` sheds one unit of heat and makes nothing.
    Returns ``(parts, heat, jammed)``.
    """
    if action == "run":
        if heat >= heat_limit:
            return parts, heat, True
        return parts + 1.0, heat + 1.0, False
    if action == "cool":
        return parts, max(0.0, heat - 1.0), False
    raise ValueError(f"unknown machine action {action!r}")
