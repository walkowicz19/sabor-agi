"""A benchmark problem: description, choices, and exact ground truth."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Problem:
    id: str
    family: str
    horizon: int
    description: str
    actions: list[str]
    q_values: dict[str, float]
    optimal: str
    event_name: str
    event_description: str
    event_probs: dict[str, float]
    model_code: str
    seed: int
    extra: dict = field(default_factory=dict)

    @property
    def ev_range(self) -> float:
        values = list(self.q_values.values())
        return max(values) - min(values)

    def regret(self, action: str) -> float:
        """Normalized regret of choosing ``action`` (0 = optimal)."""
        span = self.ev_range
        if span <= 0:
            return 0.0
        return (self.q_values[self.optimal] - self.q_values[action]) / span

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "family": self.family,
            "horizon": self.horizon,
            "description": self.description,
            "actions": self.actions,
            "q_values": self.q_values,
            "optimal": self.optimal,
            "event_name": self.event_name,
            "event_description": self.event_description,
            "event_probs": self.event_probs,
            "model_code": self.model_code,
            "seed": self.seed,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Problem:
        return cls(**data)


def dump_jsonl(problems: list[Problem], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for problem in problems:
            fh.write(json.dumps(problem.to_dict()) + "\n")


def load_jsonl(path: str) -> list[Problem]:
    with open(path, encoding="utf-8") as fh:
        return [Problem.from_dict(json.loads(line)) for line in fh if line.strip()]
