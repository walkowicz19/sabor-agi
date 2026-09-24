"""Arm A: answer immediately, no reasoning tools."""

from __future__ import annotations

from bench.arms.base import (
    ArmResult,
    parse_answer,
    problem_prompt,
    snapshot_usage,
    usage_delta,
)
from bench.problems import Problem
from saboragi.compile.llm import LlmClient

SYSTEM = (
    "You answer decision problems directly. Reply with exactly one ```answer "
    "block and no other text."
)


def run(problem: Problem, llm: LlmClient) -> ArmResult:
    before = snapshot_usage(llm)
    response = llm.chat(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": problem_prompt(problem)},
        ],
        temperature=0.0,
    )
    return ArmResult(
        answer=parse_answer(problem, response.text),
        usage=usage_delta(llm, before),
    )
