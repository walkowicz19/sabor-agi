"""Least-squares line through a series, then the next points on that line."""

from __future__ import annotations


def linear_project(values: list[float], steps: int = 1) -> list[float]:
    """Project ``steps`` values past the end of ``values``.

    A single observation repeats. Two or more fit ``y = intercept + slope * index``
    with indexes ``0 .. n-1``, then evaluate indexes ``n .. n+steps-1``.
    An arithmetic sequence is reproduced exactly.
    """
    if steps < 1:
        return []
    count = len(values)
    if count == 0:
        return []
    if count == 1:
        return [float(values[0])] * steps
    mean_x = (count - 1) / 2
    mean_y = sum(values) / count
    var_x = sum((index - mean_x) ** 2 for index in range(count))
    cov = sum((index - mean_x) * (float(values[index]) - mean_y) for index in range(count))
    slope = cov / var_x
    intercept = mean_y - slope * mean_x
    return [intercept + slope * (count - 1 + ahead) for ahead in range(1, steps + 1)]
