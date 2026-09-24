"""Pure step helpers for physical and mathematical world models.

These functions are ordinary Python. A compiled ``World`` calls them inside
``transition`` / ``outcomes``. The solver is unchanged: one call is one
discrete time step, randomness still comes only from the ``rng`` the model
was given, and the state stays a JSON-serializable dict.

Nothing here integrates an open-ended continuum. Grids stay small, each step
is an explicit update, and the identities the tests check (straight-line
motion, conserved liquid, a linear forecast) are exact consequences of the
formulas.
"""

from saboragi.sim.fluid import exchange, transfer
from saboragi.sim.forecast import linear_project
from saboragi.sim.integrate import euler, rk4
from saboragi.sim.loops import agent_step, machine_step
from saboragi.sim.motion import bicycle_step

__all__ = [
    "agent_step",
    "bicycle_step",
    "euler",
    "exchange",
    "linear_project",
    "machine_step",
    "rk4",
    "transfer",
]
