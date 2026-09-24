"""Benchmark runner: every arm answers every problem; score everything."""

from __future__ import annotations

import time
from dataclasses import dataclass

from bench.arms import code_interpreter, cot, direct, engine
from bench.problems import Problem
from saboragi.compile.llm import LlmClient
from saboragi.config import Settings

ARMS = {
    "direct": direct.run,
    "cot": cot.run,
    "code_interpreter": code_interpreter.run,
    "engine": engine.run,
}


@dataclass
class ScoredRow:
    problem_id: str
    family: str
    horizon: int
    arm: str
    action: str | None
    optimal: str
    correct: bool
    valid: bool
    regret: float
    brier: float
    tool_calls: int
    calls: int
    in_tokens: int
    out_tokens: int
    cost: float
    seconds: float

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "family": self.family,
            "horizon": self.horizon,
            "arm": self.arm,
            "action": self.action,
            "optimal": self.optimal,
            "correct": self.correct,
            "valid": self.valid,
            "regret": self.regret,
            "brier": self.brier,
            "tool_calls": self.tool_calls,
            "calls": self.calls,
            "in_tokens": self.in_tokens,
            "out_tokens": self.out_tokens,
            "cost": self.cost,
            "seconds": self.seconds,
        }


def score(problem: Problem, arm: str, result) -> ScoredRow:
    answer = result.answer
    if answer.valid and answer.action is not None and answer.p_event is not None:
        regret = problem.regret(answer.action)
        true_p = problem.event_probs[answer.action]
        brier = (answer.p_event - true_p) ** 2
        correct = answer.action == problem.optimal
    else:
        regret, brier, correct = 1.0, 1.0, False
    return ScoredRow(
        problem_id=problem.id,
        family=problem.family,
        horizon=problem.horizon,
        arm=arm,
        action=answer.action,
        optimal=problem.optimal,
        correct=correct,
        valid=answer.valid,
        regret=regret,
        brier=brier,
        tool_calls=result.tool_calls,
        calls=result.usage.get("calls", 0),
        in_tokens=result.usage.get("in_tokens", 0),
        out_tokens=result.usage.get("out_tokens", 0),
        cost=result.usage.get("cost", 0.0),
        seconds=0.0,
    )


def run_suite(
    problems: list[Problem],
    arms: list[str],
    settings: Settings,
    llm: LlmClient | None = None,
) -> list[ScoredRow]:
    llm = llm or LlmClient(settings)
    rows: list[ScoredRow] = []
    for problem in problems:
        for arm in arms:
            started = time.time()
            try:
                if arm in ("direct", "cot"):
                    result = ARMS[arm](problem, llm)
                else:
                    result = ARMS[arm](problem, llm, settings)
            except Exception as exc:  # noqa: BLE001 - a crashed arm scores worst
                from bench.arms.base import ArmAnswer, ArmResult

                result = ArmResult(ArmAnswer(None, None, False, raw=repr(exc)[:500]))
            row = score(problem, arm, result)
            row.seconds = time.time() - started
            rows.append(row)
    return rows
