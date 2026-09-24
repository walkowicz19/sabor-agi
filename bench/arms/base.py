"""Shared types and parsing for evaluation arms.

All arms answer with the same schema so results are comparable::

    ```answer
    {"action": "<one of the options>", "p_event": 0.0-1.0}
    ```

Tool arms (code_interpreter, engine) use fenced blocks as a provider-neutral
tool protocol (works even with local models lacking native tool support):

- ```` ```python ... ``` ```` executes code, stdout is pasted back.
- ```` ```deliberate {"situation": ..., "options": [...], "question_events": [...]}``` ````
  runs the SaborAGI pipeline, the verdict is pasted back.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from bench.problems import Problem
from saboragi.compile.llm import LlmClient

ANSWER_FENCE = re.compile(r"```answer\s*\n(.*?)```", re.DOTALL)
PYTHON_FENCE = re.compile(r"```python\s*\n(.*?)```", re.DOTALL)
DELIBERATE_FENCE = re.compile(r"```deliberate\s*\n(.*?)```", re.DOTALL)


@dataclass
class ArmAnswer:
    action: str | None
    p_event: float | None
    valid: bool
    raw: str = ""


@dataclass
class ArmResult:
    answer: ArmAnswer
    tool_calls: int = 0
    usage: dict = field(default_factory=dict)


def parse_answer(problem: Problem, text: str) -> ArmAnswer:
    matches = ANSWER_FENCE.findall(text)
    if not matches:
        return ArmAnswer(None, None, False, raw=text[-500:])
    try:
        data = json.loads(matches[-1].strip())
    except json.JSONDecodeError:
        return ArmAnswer(None, None, False, raw=text[-500:])
    action, p_event = data.get("action"), data.get("p_event")
    if action not in problem.actions:
        return ArmAnswer(None, None, False, raw=text[-500:])
    if isinstance(p_event, bool) or not isinstance(p_event, (int, float)):
        return ArmAnswer(None, None, False, raw=text[-500:])
    if not 0.0 <= float(p_event) <= 1.0:
        return ArmAnswer(None, None, False, raw=text[-500:])
    return ArmAnswer(action, float(p_event), True, raw=text[-500:])


def problem_prompt(problem: Problem) -> str:
    return (
        f"{problem.description}\n\n"
        "Decide which option to take FIRST to maximize the expected final outcome.\n"
        f"Also estimate {problem.event_description} (a number between 0 and 1).\n"
        "Reply with your final answer as exactly:\n"
        "```answer\n"
        '{"action": "<one of the options>", "p_event": <number>}\n'
        "```"
    )


def snapshot_usage(client: LlmClient) -> dict:
    return {
        "calls": client.calls,
        "in_tokens": client.in_tokens,
        "out_tokens": client.out_tokens,
        "cost": client.cost(),
    }


def usage_delta(client: LlmClient, before: dict) -> dict:
    after = snapshot_usage(client)
    return {k: after[k] - before[k] for k in after}
