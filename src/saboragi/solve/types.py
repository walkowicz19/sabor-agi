"""Common result types returned by every solver."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OptionResult:
    action: str
    ev: float
    ci_lo: float
    ci_hi: float
    p_events: dict[str, float] = field(default_factory=dict)
    worst_case_p5: float = 0.0
    n: int = 0

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "ev": self.ev,
            "ci": [self.ci_lo, self.ci_hi],
            "p_events": dict(self.p_events),
            "worst_case_p5": self.worst_case_p5,
            "n": self.n,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OptionResult:
        ci = data.get("ci", [data.get("ev", 0.0), data.get("ev", 0.0)])
        return cls(
            action=data["action"],
            ev=data["ev"],
            ci_lo=ci[0],
            ci_hi=ci[1],
            p_events=dict(data.get("p_events", {})),
            worst_case_p5=data.get("worst_case_p5", 0.0),
            n=data.get("n", 0),
        )


@dataclass
class SolveResult:
    options: list[OptionResult]
    best: str
    solver: str
    exact: bool = False
    diagnostics: dict = field(default_factory=dict)

    def option(self, action: str) -> OptionResult:
        for opt in self.options:
            if opt.action == action:
                return opt
        raise KeyError(f"unknown action {action!r}")

    def to_dict(self) -> dict:
        return {
            "options": [o.to_dict() for o in self.options],
            "best": self.best,
            "solver": self.solver,
            "exact": self.exact,
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SolveResult:
        return cls(
            options=[OptionResult.from_dict(o) for o in data["options"]],
            best=data["best"],
            solver=data["solver"],
            exact=data.get("exact", False),
            diagnostics=dict(data.get("diagnostics", {})),
        )
