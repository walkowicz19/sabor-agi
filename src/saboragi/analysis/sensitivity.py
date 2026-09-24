"""One-at-a-time sensitivity: which uncertain params flip the decision?"""

from __future__ import annotations

from dataclasses import dataclass

from saboragi.config import Settings
from saboragi.sandbox.runner import run_analyze, run_inspect


@dataclass
class Flip:
    param: str
    flips_at: str  # "low" | "high"
    new_best: str

    def to_dict(self) -> dict:
        return {"param": self.param, "flips_at": self.flips_at, "new_best": self.new_best}


def uncertain_params(code: str, settings: Settings) -> dict[str, dict]:
    result = run_inspect(code, memory_mb=min(512, settings.memory_mb))
    if not result.ok:
        return {}
    return {
        name: info for name, info in result.data.get("params", {}).items() if info.get("uncertain")
    }


def find_flips(
    code: str,
    options: list[str],
    baseline_best: str,
    settings: Settings,
    *,
    seed: int = 0,
) -> tuple[list[Flip], list[str]]:
    """Re-solve with each Uncertain param at low/high; report decision flips."""
    warnings: list[str] = []
    params = uncertain_params(code, settings)
    names = list(params)[: settings.max_sensitivity_params]
    if len(params) > len(names):
        warnings.append(f"sensitivity capped at {len(names)}/{len(params)} uncertain params")
    flips: list[Flip] = []
    for name in names:
        for side in ("low", "high"):
            value = params[name][side]
            result = run_analyze(
                code,
                options,
                timeout=settings.analyze_timeout,
                memory_mb=settings.memory_mb,
                seed=seed,
                param_overrides={name: value},
            )
            if not result.ok:
                warnings.append(f"sensitivity {name}={side} failed: {result.errors[0]}")
                continue
            from saboragi.solve.types import SolveResult

            solved = SolveResult.from_dict(result.data["result"])
            if solved.best != baseline_best:
                flips.append(Flip(param=name, flips_at=side, new_best=solved.best))
    return flips, warnings
