"""Compile with the MCP client's own model when the API model cannot be called.

Sampling asks the connected client (Cursor, or another MCP host) to run the
completion on the model already driving the session. That call is a separate
context for each ensemble member, so the K models stay independent.

If the client did not declare the sampling capability, the server cannot
borrow its model mid-call. It returns a handoff instead: the harness model,
or one sub-agent per job, writes the code and calls resume_deliberation.
"""

from __future__ import annotations

from mcp import types

from saboragi.compile.llm import LlmResponse, ModelUnavailable
from saboragi.compile.prompts import FRAMINGS, build_messages
from saboragi.config import Settings

INSTRUCTION = (
    "The configured API model is unavailable, so you must compile the world models. "
    "For each job, write one Python World(Model) subclass from that job's messages, "
    "or create one sub-agent per job and give it those messages. Keep the jobs "
    "independent. Then call resume_deliberation with the code strings in job index "
    "order, plus the options and question_events from this result. Do not pick an "
    "option until that tool returns a verdict."
)


def session_can_sample(session: object) -> bool:
    params = getattr(session, "_client_params", None)
    caps = getattr(params, "capabilities", None) if params is not None else None
    return getattr(caps, "sampling", None) is not None


def compilation_handoff(
    reason: str,
    situation: str,
    options: list[str] | None,
    question_events: list[str] | None,
    settings: Settings,
) -> dict:
    jobs = []
    for index in range(settings.k):
        temperature, framing = FRAMINGS[index % len(FRAMINGS)]
        jobs.append(
            {
                "index": index,
                "temperature": temperature,
                "messages": build_messages(situation, options, question_events, framing),
            }
        )
    return {
        "status": "needs_harness",
        "compiler": "harness",
        "reason": reason,
        "instruction": INSTRUCTION,
        "jobs": jobs,
        "options": options,
        "question_events": question_events,
    }


def _as_blocks(content: object) -> list:
    if isinstance(content, list):
        return content
    return [content]


def result_text(result: object) -> str:
    parts: list[str] = []
    for block in _as_blocks(getattr(result, "content", result)):
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


class SamplingChat:
    """Chat backend that asks the MCP client to sample its own model."""

    def __init__(self, session: object):
        self.session = session
        self.calls = 0
        self.in_tokens = 0
        self.out_tokens = 0
        self.model_name = "harness"

    def cost(self) -> float:
        return 0.0

    async def chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int = 4096,
    ) -> LlmResponse:
        system_parts: list[str] = []
        convo: list[types.SamplingMessage] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                system_parts.append(content)
                continue
            if role not in ("user", "assistant"):
                role = "user"
            convo.append(
                types.SamplingMessage(
                    role=role,
                    content=types.TextContent(type="text", text=content),
                )
            )
        if not convo:
            empty = types.TextContent(type="text", text="")
            convo.append(types.SamplingMessage(role="user", content=empty))
        try:
            result = await self.session.create_message(  # type: ignore[attr-defined]
                convo,
                max_tokens=max_tokens,
                system_prompt="\n\n".join(system_parts) or None,
                temperature=temperature,
            )
        except Exception as exc:
            raise ModelUnavailable(type(exc).__name__) from exc
        self.calls += 1
        self.model_name = getattr(result, "model", None) or "harness"
        return LlmResponse(text=result_text(result))
