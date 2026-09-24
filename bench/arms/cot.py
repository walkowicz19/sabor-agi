"""Arm B: reason step by step about probabilities, then answer."""

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
    "You solve decision problems by reasoning step by step about the "
    "probabilities and expected values of each option, then commit to a "
    "final answer as exactly one ```answer block."
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
