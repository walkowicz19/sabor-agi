"""Planar vehicle step: a kinematic bicycle.

Yaw uses the speed at the beginning of the step, so a stopped vehicle does
not spin in place. Translation uses the updated speed and the heading held
during the step.
"""

from __future__ import annotations

import math


def bicycle_step(
    x: float,
    y: float,
    heading: float,
    speed: float,
    steer: float,
    accel: float,
    dt: float,
    wheelbase: float,
) -> tuple[float, float, float, float]:
    """Return ``(x, y, heading, speed)`` one step later.

    ``steer`` is the front-wheel angle in radians. ``heading`` is radians
    from the +x axis. ``wheelbase`` is the distance between axles.
    """
    if wheelbase <= 0 or dt < 0:
        raise ValueError("wheelbase must be positive and dt must be non-negative")
    new_speed = speed + accel * dt
    yaw = speed * math.tan(steer) / wheelbase * dt
    new_heading = heading + yaw
    new_x = x + new_speed * math.cos(heading) * dt
    new_y = y + new_speed * math.sin(heading) * dt
    return new_x, new_y, new_heading, new_speed
