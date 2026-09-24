"""Arm D: a tool-calling loop with the SaborAGI `deliberate` tool.

The compiler model is the shared client (the model under test), so the
comparison against the other arms is fair.
"""

from __future__ import annotations

import json

from bench.arms.base import (
    ANSWER_FENCE,
    DELIBERATE_FENCE,
    ArmResult,
    parse_answer,
    problem_prompt,
    snapshot_usage,
    usage_delta,
)
from bench.problems import Problem
from saboragi import pipeline
from saboragi.compile.llm import LlmClient
from saboragi.config import Settings

SYSTEM = """\
You solve decision problems with a deliberation tool. Emit a ```deliberate block with JSON \
arguments {"situation": "concrete description with the numbers you know", "options": [...], \
"question_events": [...]} to compile the situation into executable world models, solve them, \
and get back a verdict (recommended option, expected values, event chances, worst cases, \
flippable assumptions, confidence). Use the verdict as evidence, not truth: if confidence is \
"low" or models disagree, weigh that in. Finish with a final ```answer block \
{"action": ..., "p_event": ...}. You have at most 8 tool calls.\
"""


def run(problem: Problem, llm: LlmClient, settings: Settings, max_calls: int = 8) -> ArmResult:
    before = snapshot_usage(llm)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": problem_prompt(problem)},
    ]
    tool_calls, answer_text = 0, ""
    for _ in range(max_calls + 1):
        response = llm.chat(messages, temperature=0.0)
        messages.append({"role": "assistant", "content": response.text})
        if ANSWER_FENCE.search(response.text):
            answer_text = response.text
            break
        blocks = DELIBERATE_FENCE.findall(response.text)
        if not blocks or tool_calls >= max_calls:
            answer_text = response.text
            break
        tool_calls += 1
        try:
            args = json.loads(blocks[-1].strip())
        except json.JSONDecodeError:
            output = "ERROR: the deliberate block must contain valid JSON arguments."
        else:
            try:
                verdict = pipeline.deliberate(
                    args.get("situation", problem.description),
                    args.get("options", problem.actions),
                    args.get("question_events", [problem.event_name]),
                    settings,
                    llm,
                )
                output = "VERDICT:\n" + json.dumps(verdict, default=str)
            except Exception as exc:  # noqa: BLE001 - fed back to the model
                output = f"ERROR: {exc}"
        messages.append({"role": "user", "content": f"<tool-output>\n{output}"})
    return ArmResult(
        answer=parse_answer(problem, answer_text),
        tool_calls=tool_calls,
        usage=usage_delta(llm, before),
    )
