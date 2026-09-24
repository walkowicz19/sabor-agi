"""Compile K independent world models for one situation, with repair."""

from __future__ import annotations

from dataclasses import dataclass, field

from saboragi.compile.llm import LlmClient, LlmResponse, ModelUnavailable, extract_code
from saboragi.compile.prompts import FRAMINGS, build_messages, build_repair_messages
from saboragi.config import Settings
from saboragi.sandbox.runner import run_inspect, run_validate
from saboragi.validate.checks import CheckIssue, CheckReport


@dataclass
class CompiledModel:
    index: int
    code: str
    check_warnings: list[str] = field(default_factory=list)


def _issues_to_strings(report: CheckReport) -> list[str]:
    return [f"[{e.code}] {e.message}" for e in report.errors]


def _validate(code: str, settings: Settings) -> CheckReport | None:
    """Sandbox validation; None if the sandbox itself failed (timeout/OOM)."""
    result = run_validate(
        code,
        timeout=settings.validate_timeout,
        memory_mb=settings.memory_mb,
    )
    if not result.ok:
        if result.stage == "guard":
            # Static problems are repairable: hand them back as check issues.
            return CheckReport(errors=[CheckIssue("guard", error) for error in result.errors])
        return None
    return CheckReport.from_dict(result.data["report"])


def _covers_actions(code: str, options: list[str] | None, settings: Settings) -> str | None:
    """None if fine, else a warning describing the action-coverage problem."""
    if not options:
        return None
    result = run_inspect(code, memory_mb=min(512, settings.memory_mb))
    if not result.ok:
        return f"inspect failed: {result.errors[0] if result.errors else 'unknown'}"
    available = set(result.data.get("actions", []))
    missing = [a for a in options if a not in available]
    if missing:
        return f"actions() is missing requested options: {missing}"
    return None


def _attempt(
    code: str,
    settings: Settings,
    options: list[str] | None,
    index: int,
) -> tuple[CompiledModel | None, list[str] | None]:
    """Validate one candidate.

    Returns (model, []) when it passes, (None, problems) when a repair could
    help, and (None, None) when the sandbox itself failed.
    """
    report = _validate(code, settings)
    if report is None:
        return None, None
    problems = _issues_to_strings(report)
    coverage = _covers_actions(code, options, settings)
    if coverage is not None:
        problems.append(coverage)
    if problems:
        return None, problems
    warnings = [f"[{w.code}] {w.message}" for w in report.warnings]
    return CompiledModel(index=index, code=code, check_warnings=warnings), []


def _drop_reason(index: int, problems: list[str] | None, repairs: int) -> str:
    if problems is None:
        return f"model_{index} dropped: sandbox failure"
    if problems:
        return f"model_{index} dropped: " + "; ".join(problems)
    return f"model_{index} dropped: failed to produce a valid model after {repairs} repairs"


def compile_one(
    llm: LlmClient,
    settings: Settings,
    situation: str,
    options: list[str] | None,
    question_events: list[str] | None,
    index: int,
) -> CompiledModel | None:
    temperature, framing = FRAMINGS[index % len(FRAMINGS)]
    response = llm.chat(build_messages(situation, options, question_events, framing), temperature)
    return _repair_loop(
        response.text,
        lambda prompt: llm.chat(prompt, temperature=0.2).text,
        settings,
        options,
        index,
    )


def _repair_loop(
    first_text: str,
    repair_text,
    settings: Settings,
    options: list[str] | None,
    index: int,
) -> CompiledModel | None:
    code = extract_code(first_text)
    if code is None:
        return None
    for _ in range(settings.max_repairs + 1):
        model, problems = _attempt(code, settings, options, index)
        if problems is None or model is not None:
            return model
        fixed = extract_code(repair_text(build_repair_messages(code, problems)))
        if fixed is None:
            return None
        code = fixed
    return None


def compile_ensemble(
    llm: LlmClient,
    settings: Settings,
    situation: str,
    options: list[str] | None = None,
    question_events: list[str] | None = None,
) -> tuple[list[CompiledModel], list[str]]:
    """Compile settings.k models; returns (survivors, warnings for dropped ones)."""
    survivors: list[CompiledModel] = []
    warnings: list[str] = []
    for index in range(settings.k):
        try:
            compiled = compile_one(llm, settings, situation, options, question_events, index)
        except ModelUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - one bad member must not kill the ensemble
            warnings.append(f"model_{index} error: {exc!r}")
            continue
        if compiled is None:
            warnings.append(_drop_reason(index, [], settings.max_repairs))
        else:
            survivors.append(compiled)
    return survivors, warnings


def _as_text(response: LlmResponse | str) -> str:
    return response.text if isinstance(response, LlmResponse) else response


async def compile_ensemble_async(
    chat,
    settings: Settings,
    situation: str,
    options: list[str] | None = None,
    question_events: list[str] | None = None,
) -> tuple[list[CompiledModel], list[str]]:
    """Same as compile_ensemble, but each completion is awaited.

    `chat(messages, temperature)` returns LlmResponse. ModelUnavailable still
    aborts the whole ensemble so the caller can switch compilers.
    """
    survivors: list[CompiledModel] = []
    warnings: list[str] = []
    for index in range(settings.k):
        try:
            compiled = await _compile_one_async(
                chat, settings, situation, options, question_events, index
            )
        except ModelUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - one bad member must not kill the ensemble
            warnings.append(f"model_{index} error: {exc!r}")
            continue
        if compiled is None:
            warnings.append(_drop_reason(index, [], settings.max_repairs))
        else:
            survivors.append(compiled)
    return survivors, warnings


async def _compile_one_async(
    chat,
    settings: Settings,
    situation: str,
    options: list[str] | None,
    question_events: list[str] | None,
    index: int,
) -> CompiledModel | None:
    temperature, framing = FRAMINGS[index % len(FRAMINGS)]
    response = await chat(build_messages(situation, options, question_events, framing), temperature)
    code = extract_code(_as_text(response))
    if code is None:
        return None
    for _ in range(settings.max_repairs + 1):
        model, problems = _attempt(code, settings, options, index)
        if problems is None or model is not None:
            return model
        repaired = await chat(build_repair_messages(code, problems), 0.2)
        fixed = extract_code(_as_text(repaired))
        if fixed is None:
            return None
        code = fixed
    return None
