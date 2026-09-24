"""Aggregate per-model solutions into one decision-ready verdict."""

from __future__ import annotations

import math

from saboragi.analysis.sensitivity import Flip
from saboragi.solve.types import SolveResult


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _epistemic_ci(evs: list[float]) -> tuple[float, float]:
    if len(evs) == 1:
        raise ValueError("single model: use its own CI")
    mean = _mean(evs)
    var = max(0.0, sum((x - mean) ** 2 for x in evs) / len(evs))
    half = 1.96 * math.sqrt(var / len(evs))
    return mean - half, mean + half


def build_verdict(
    results: list[SolveResult],
    options: list[str],
    flips: list[Flip],
    warnings: list[str],
    models_requested: int,
) -> dict:
    """Combine ensemble solutions into the verdict dict served over MCP."""
    if not results:
        raise ValueError("no surviving world models")
    by_action: dict[str, list] = {a: [] for a in options}
    for result in results:
        for option in result.options:
            if option.action in by_action:
                by_action[option.action].append(option)

    verdict_options = []
    for action in options:
        opts = by_action[action]
        if not opts:
            continue
        evs = [o.ev for o in opts]
        mean_ev = _mean(evs)
        if len(evs) == 1:
            ci_lo, ci_hi = opts[0].ci_lo, opts[0].ci_hi
        else:
            ci_lo, ci_hi = _epistemic_ci(evs)
        event_names = sorted({e for o in opts for e in o.p_events})
        verdict_options.append(
            {
                "action": action,
                "ev": mean_ev,
                "ci": [ci_lo, ci_hi],
                "p_events": {e: _mean([o.p_events.get(e, 0.0) for o in opts]) for e in event_names},
                "worst_case_p5": min(o.worst_case_p5 for o in opts),
                "models_ranking_first": sum(1 for r in results if r.best == action),
            }
        )
    verdict_options.sort(key=lambda o: o["ev"], reverse=True)
    recommended = verdict_options[0]["action"]

    agree = all(r.best == recommended for r in results)
    rec_evs = [o.ev for o in by_action[recommended]] if by_action[recommended] else [0.0]
    if len(results) == 1:
        confidence = "medium"
    elif not agree or flips:
        confidence = "low"
    elif warnings or len(results) < models_requested:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "recommended": recommended,
        "confidence": confidence,
        "options": verdict_options,
        "epistemic_spread": {
            "ev_range_across_models": [min(rec_evs), max(rec_evs)],
            "agree_on_best": agree,
        },
        "flip_parameters": [f.to_dict() for f in flips],
        "warnings": list(warnings),
        "models_used": len(results),
    }
