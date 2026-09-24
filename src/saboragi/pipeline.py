"""The fixed deliberation pipeline shared by the MCP server and the benchmark.

deliberate(): situation -> K compiled models -> sandbox solves ->
sensitivity -> verdict. No LLM calls happen inside any solve loop.

The benchmark always calls deliberate() with the model under test. Harness
fallback (client sampling, or a handoff to the caller and its sub-agents)
lives in the MCP server so an unavailable API model does not change the eval.
"""

from __future__ import annotations

import asyncio

from saboragi.analysis.sensitivity import find_flips
from saboragi.analysis.verdict import build_verdict
from saboragi.compile.compiler import (
    CompiledModel,
    _attempt,
    compile_ensemble,
    compile_ensemble_async,
)
from saboragi.compile.llm import LlmClient
from saboragi.config import Settings
from saboragi.sandbox.runner import run_analyze
from saboragi.solve.types import SolveResult

_last: dict = {}


def last_detail() -> dict:
    """Inspectable state for the explain_last tool (codes, solves, verdict)."""
    return dict(_last)


def _solve_code(code: str, options: list[str] | None, settings: Settings, seed: int) -> SolveResult:
    result = run_analyze(
        code,
        options,
        timeout=settings.analyze_timeout,
        memory_mb=settings.memory_mb,
        seed=seed,
    )
    if not result.ok:
        raise RuntimeError(f"solve failed: {result.errors[0]}")
    return SolveResult.from_dict(result.data["result"])


def _usage_of(llm: object) -> dict:
    cost = llm.cost() if hasattr(llm, "cost") else 0.0
    return {
        "calls": getattr(llm, "calls", 0),
        "in_tokens": getattr(llm, "in_tokens", 0),
        "out_tokens": getattr(llm, "out_tokens", 0),
        "cost": cost,
        "model": getattr(llm, "model_name", None),
    }


def _assemble(
    compiled: list[CompiledModel],
    warnings: list[str],
    options: list[str] | None,
    settings: Settings,
    llm_meta: dict,
    compiler: str,
) -> dict:
    warnings = list(warnings)
    if len(compiled) < 1:
        raise RuntimeError(
            "no surviving world models: " + "; ".join(warnings) if warnings else "no models"
        )
    if len(compiled) < 2:
        warnings.append("only one model survived; uncertainty is understated")

    if options is None:
        first = _solve_code(compiled[0].code, None, settings, seed=0)
        options = [o.action for o in first.options]

    results: list[SolveResult] = []
    flips_all = []
    for member in compiled:
        solved = _solve_code(member.code, options, settings, seed=member.index)
        if {o.action for o in solved.options} < set(options):
            warnings.append(f"model_{member.index} dropped: missing options after solve")
            continue
        results.append(solved)
        flips, flip_warnings = find_flips(
            member.code, options, solved.best, settings, seed=member.index
        )
        flips_all.extend(flips)
        warnings.extend(f"model_{member.index}: {w}" for w in flip_warnings)
        warnings.extend(f"model_{member.index}: {w}" for w in member.check_warnings)
    if not results:
        raise RuntimeError("no surviving world models after solving")

    verdict = build_verdict(results, options, flips_all, warnings, settings.k)
    verdict["compiler"] = compiler
    _last.clear()
    _last.update(
        {
            "verdict": verdict,
            "codes": [m.code for m in compiled],
            "results": [r.to_dict() for r in results],
            "llm": llm_meta,
            "compiler": compiler,
        }
    )
    return verdict


def deliberate(
    situation: str,
    options: list[str] | None = None,
    question_events: list[str] | None = None,
    settings: Settings | None = None,
    llm: LlmClient | None = None,
) -> dict:
    settings = settings or Settings.from_env()
    llm = llm or LlmClient(settings)
    compiled, warnings = compile_ensemble(llm, settings, situation, options, question_events)
    return _assemble(compiled, warnings, options, settings, _usage_of(llm), "external")


async def deliberate_with_chat(
    situation: str,
    options: list[str] | None,
    question_events: list[str] | None,
    settings: Settings,
    chat: object,
    compiler: str,
) -> dict:
    """Compile by awaiting `chat`, then solve. Used for the harness model.

    `chat` may be an async callable or an object with an async `chat` method
    (so token counters on that object still get recorded).
    """
    complete = chat.chat if hasattr(chat, "chat") else chat
    compiled, warnings = await compile_ensemble_async(
        complete, settings, situation, options, question_events
    )
    return await asyncio.to_thread(
        _assemble, compiled, warnings, options, settings, _usage_of(chat), compiler
    )


def deliberate_codes(
    codes: list[str],
    options: list[str] | None = None,
    settings: Settings | None = None,
) -> dict:
    """Solve world models the harness or its sub-agents already wrote."""
    settings = settings or Settings.from_env()
    compiled: list[CompiledModel] = []
    warnings: list[str] = []
    for index, code in enumerate(codes):
        model, problems = _attempt(code, settings, options, index)
        if model is not None:
            compiled.append(model)
            continue
        if problems is None:
            warnings.append(f"model_{index} dropped: sandbox failure")
        else:
            warnings.append(f"model_{index} dropped: " + "; ".join(problems))
    return _assemble(compiled, warnings, options, settings, _usage_of(object()), "harness")


def analyze_code(
    code: str,
    options: list[str] | None = None,
    settings: Settings | None = None,
) -> dict:
    """Deliberation for caller-supplied model code (skips compilation)."""
    settings = settings or Settings.from_env()
    solved = _solve_code(code, options, settings, seed=0)
    resolved = options or [o.action for o in solved.options]
    flips, warnings = find_flips(code, resolved, solved.best, settings)
    verdict = build_verdict([solved], resolved, flips, warnings, 1)
    _last.clear()
    _last.update({"verdict": verdict, "codes": [code], "results": [solved.to_dict()]})
    return verdict
