"""Arm C: a tool-calling loop with a plain `run_python` tool.

The real rival: the model may write and execute arbitrary analysis code
(expected values, simulations) but gets no world-model API, no validity
checks, no ensemble, and no forced pipeline.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from bench.arms.base import (
    ANSWER_FENCE,
    PYTHON_FENCE,
    ArmResult,
    parse_answer,
    problem_prompt,
    snapshot_usage,
    usage_delta,
)
from bench.problems import Problem
from saboragi.compile.llm import LlmClient
from saboragi.config import Settings
from saboragi.sandbox import guard

SYSTEM = """\
You solve decision problems with a Python tool. Emit ```python blocks to run code; stdout \
comes back as a <tool-output> message. Each block runs fresh (no state kept). \
Available: math, random, numpy, itertools, functools, collections, dataclasses, statistics. \
Print anything you want to see, including a final ```answer block with \
{"action": ..., "p_event": ...} when you are done. You have at most 8 tool calls.\
"""

EXEC_TIMEOUT = 30.0


def run_python(code: str) -> str:
    """Execute untrusted analysis code; returns stdout or an error message."""
    problems = guard.check(code)
    if problems:
        return "GUARD REJECTED:\n" + "\n".join(problems)
    with tempfile.TemporaryDirectory(prefix="saboragi_py_") as tmp:
        script = Path(tmp) / "snippet.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return f"TIMEOUT after {EXEC_TIMEOUT:.0f}s"
        if proc.returncode != 0:
            return "ERROR:\n" + (proc.stderr or "")[-2000:]
        return "OUTPUT:\n" + (proc.stdout or "(no output)")[-4000:]


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
        blocks = PYTHON_FENCE.findall(response.text)
        if not blocks or tool_calls >= max_calls:
            answer_text = response.text
            break
        tool_calls += 1
        output = run_python(blocks[-1])
        messages.append({"role": "user", "content": f"<tool-output>\n{output}"})
    return ArmResult(
        answer=parse_answer(problem, answer_text),
        tool_calls=tool_calls,
        usage=usage_delta(llm, before),
    )
