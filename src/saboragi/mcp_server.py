"""SaborAGI MCP server (FastMCP over stdio).

Expose deliberation as coarse tools so callers think twice before acting.
Call `deliberate` whenever a decision involves uncertainty, several steps, or
possibly irreversible outcomes: the server compiles the situation into
executable world models, solves them, and returns a decision-ready verdict.

A model running on this machine compiles first (Ollama, LM Studio, or
whatever is already listening locally). No external API key or model id is
required. If nothing local can be called, the client's own model compiles
via MCP sampling. If the client cannot sample, the tool returns status
"needs_harness" and the caller (or one sub-agent per job) writes the models,
then calls resume_deliberation.
"""

from __future__ import annotations

import asyncio
import os

from mcp.server.fastmcp import Context, FastMCP

from saboragi import pipeline
from saboragi.compile.harness import SamplingChat, compilation_handoff, session_can_sample
from saboragi.compile.llm import ModelUnavailable
from saboragi.config import Settings
from saboragi.sandbox.runner import run_sample

mcp = FastMCP("saboragi")


def _compiler_mode() -> str:
    mode = os.environ.get("SABORAGI_COMPILER", "auto").strip().lower()
    return mode if mode in {"auto", "external", "harness"} else "auto"


def _session(ctx: Context | None) -> object | None:
    if ctx is None:
        return None
    try:
        return ctx.request_context.session
    except (AttributeError, ValueError):
        return None


@mcp.tool()
async def deliberate(
    situation: str,
    options: list[str] | None = None,
    question_events: list[str] | None = None,
    ctx: Context | None = None,
) -> dict:
    """Deliberate before acting under uncertainty.

    Use this when the decision involves randomness, hidden information,
    multiple steps, or outcomes that are expensive or hard to reverse
    (spending money, changing systems, committing to a plan). Describe the
    situation concretely with the numbers you know.

    Returns a verdict: recommended option, expected values with confidence
    intervals, chances of asked-about events, worst cases, which uncertain
    assumptions could flip the decision, and overall confidence.
    Treat the verdict as evidence, not truth: if confidence is "low" or the
    models disagree, say so and do not overstate certainty.

    A local model is used when one is already running on this machine. If none
    is reachable, this tool compiles with the client model via MCP sampling.
    If the client cannot sample, the result has status "needs_harness" and
    one job per ensemble member. You must then write each World model
    yourself, or create one sub-agent per job using that job's messages, and
    call resume_deliberation. Do not pick an option before that verdict
    comes back.
    """
    settings = Settings.from_env()
    mode = _compiler_mode()
    try:
        if mode == "harness":
            raise ModelUnavailable("SABORAGI_COMPILER=harness; external model skipped")
        return await asyncio.to_thread(
            pipeline.deliberate, situation, options, question_events, settings
        )
    except ModelUnavailable as exc:
        if mode == "external":
            return {"error": str(exc)}
        session = _session(ctx)
        if session is not None and session_can_sample(session):
            try:
                return await pipeline.deliberate_with_chat(
                    situation,
                    options,
                    question_events,
                    settings,
                    SamplingChat(session),
                    "harness",
                )
            except ModelUnavailable:
                pass
            except Exception as nested:  # noqa: BLE001 - surfaced to the caller as data
                return {"error": str(nested)}
        return compilation_handoff(str(exc), situation, options, question_events, settings)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as data
        return {"error": str(exc)}


@mcp.tool()
def resume_deliberation(
    codes: list[str],
    options: list[str] | None = None,
    question_events: list[str] | None = None,  # noqa: ARG001 - reserved for parity
) -> dict:
    """Finish a deliberation the harness model or its sub-agents compiled.

    Call this after deliberate returns status "needs_harness". Pass one World
    model source string per job, in index order, and the same options.
    The codes are validated and solved. The verdict is evidence, not truth.
    """
    try:
        return pipeline.deliberate_codes(codes, options, Settings.from_env())
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as data
        return {"error": str(exc)}


@mcp.tool()
def simulate_model(
    code: str,
    options: list[str] | None = None,
    question_events: list[str] | None = None,  # noqa: ARG001 - reserved for parity
) -> dict:
    """Solve a caller-supplied world model (a World(Model) subclass as code).

    Use this when you already formalized the situation yourself and want the
    engine's verdict without recompilation: the code is validated, solved
    (exact/MCTS/Monte Carlo), sensitivity-checked, and returned as a verdict.
    """
    try:
        return pipeline.analyze_code(code, options, Settings.from_env())
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as data
        return {"error": str(exc)}


@mcp.tool()
def explain_last(detail: str = "models") -> dict:
    """Inspect the previous deliberation: "models" for compiled code, "rollouts" for samples."""
    last = pipeline.last_detail()
    if not last:
        return {"error": "no deliberation has run yet in this session"}
    if detail == "models":
        return {"codes": last.get("codes", [])}
    if detail == "rollouts":
        codes = last.get("codes", [])
        if not codes:
            return {"error": "no model code stored"}
        result = run_sample(codes[0], n_trajectories=3)
        if not result.ok:
            return {"error": result.errors[0] if result.errors else "sampling failed"}
        return result.data
    return {"error": f"unknown detail {detail!r}; use 'models' or 'rollouts'"}


def _refresh_tool_list_on_connect() -> None:
    """Ask the client to list tools again after it finishes initializing.

    Cursor keeps the first tools/list for the life of the server entry and
    does not list again when the process restarts. Advertising listChanged
    and sending the notification is what makes a newly registered tool appear.
    """
    from mcp import types
    from mcp.server.lowlevel.server import NotificationOptions
    from mcp.server.session import ServerSession

    server = mcp._mcp_server
    original_create = server.create_initialization_options

    def create_initialization_options(
        notification_options: NotificationOptions | None = None,
        experimental_capabilities: dict[str, dict[str, object]] | None = None,
    ):
        if notification_options is None:
            notification_options = NotificationOptions(tools_changed=True)
        return original_create(notification_options, experimental_capabilities)

    server.create_initialization_options = create_initialization_options  # type: ignore[method-assign]

    if getattr(ServerSession._received_notification, "_saboragi_wrapped", False):
        return

    original_received = ServerSession._received_notification

    async def _received_notification(
        self: ServerSession, notification: types.ClientNotification
    ) -> None:
        await original_received(self, notification)
        if isinstance(notification.root, types.InitializedNotification):
            await self.send_tool_list_changed()

    _received_notification._saboragi_wrapped = True  # type: ignore[attr-defined]
    ServerSession._received_notification = _received_notification  # type: ignore[method-assign]


def main() -> None:
    _refresh_tool_list_on_connect()
    mcp.run()


if __name__ == "__main__":
    main()
