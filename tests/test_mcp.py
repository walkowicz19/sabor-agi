"""Step-5 tests: MCP tools behave over direct calls (no LLM configured)."""

import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import saboragi.pipeline as pipeline_module
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from saboragi.compile.llm import LlmClient, ModelUnavailable
from saboragi.mcp_server import deliberate, explain_last, resume_deliberation, simulate_model

GAMBLE_CODE = (Path(__file__).parent / "reference_models" / "gamble.py").read_text()


def test_simulate_model_returns_verdict():
    verdict = simulate_model(GAMBLE_CODE, ["safe", "risky", "longshot"])
    assert "error" not in verdict, verdict
    assert verdict["recommended"] in {"safe", "risky"}
    assert verdict["models_used"] == 1
    assert {o["action"] for o in verdict["options"]} == {"safe", "risky", "longshot"}


def test_simulate_model_reports_bad_code():
    verdict = simulate_model("import os\n")
    assert "error" in verdict


def test_stdio_server_solves_while_host_holds_stdin():
    """A worker must not inherit the MCP stdin pipe and block on it."""

    async def run():
        root = Path(__file__).resolve().parents[1]
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "saboragi.mcp_server"],
            cwd=root,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                assert init.capabilities.tools is not None
                assert init.capabilities.tools.listChanged is True
                listed = await session.list_tools()
                assert "resume_deliberation" in {tool.name for tool in listed.tools}
                result = await session.call_tool(
                    "simulate_model",
                    {
                        "code": GAMBLE_CODE,
                        "options": ["safe", "risky", "longshot"],
                        "question_events": ["jackpot"],
                    },
                    read_timeout_seconds=timedelta(seconds=20),
                )
        assert not result.isError
        verdict = json.loads(result.content[0].text)
        assert "error" not in verdict, verdict
        assert verdict["recommended"] in {"safe", "risky"}
        assert verdict["options"][0]["ev"] == 10.0

    asyncio.run(run())


def test_explain_last_models_and_rollouts():
    pipeline_module._last.clear()
    assert "error" in explain_last("models")
    simulate_model(GAMBLE_CODE, ["safe", "risky", "longshot"])
    models = explain_last("models")
    assert len(models["codes"]) == 1 and "class World" in models["codes"][0]
    rollouts = explain_last("rollouts")
    assert len(rollouts["trajectories"]) == 3
    assert rollouts["trajectories"][0]["steps"][0]["state"]["t"] == 0
    assert "error" in explain_last("bogus")


def _unavailable(self, messages, temperature, max_tokens=4096):
    raise ModelUnavailable("No LLM configured")


def test_deliberate_without_api_model_asks_the_harness(monkeypatch):
    monkeypatch.delenv("SABORAGI_COMPILER", raising=False)
    monkeypatch.setattr(LlmClient, "chat", _unavailable)
    result = asyncio.run(deliberate("Should I take the safe lottery?", ["safe", "risky"]))
    assert result["status"] == "needs_harness"
    assert result["jobs"]
    assert "resume_deliberation" in result["instruction"]
    assert "sub-agent" in result["instruction"]
    assert result["jobs"][0]["messages"][1]["content"].count("safe lottery") == 1


def test_external_compiler_mode_does_not_hand_off(monkeypatch):
    monkeypatch.setenv("SABORAGI_COMPILER", "external")
    monkeypatch.setattr(LlmClient, "chat", _unavailable)
    result = asyncio.run(deliberate("Should I take the safe lottery?", ["safe", "risky"]))
    assert "error" in result
    assert "status" not in result


def test_deliberate_samples_the_client_model(monkeypatch):
    monkeypatch.setenv("SABORAGI_K", "1")
    monkeypatch.setenv("SABORAGI_MAX_REPAIRS", "0")
    monkeypatch.delenv("SABORAGI_COMPILER", raising=False)
    monkeypatch.setattr(LlmClient, "chat", _unavailable)

    class Session:
        _client_params = SimpleNamespace(capabilities=SimpleNamespace(sampling=object()))

        async def create_message(self, messages, **kwargs):
            assert kwargs["temperature"] == 0.2
            assert messages[0].role == "user"
            return SimpleNamespace(content=SimpleNamespace(text=GAMBLE_CODE), model="harness-test")

    ctx = SimpleNamespace(request_context=SimpleNamespace(session=Session()))
    result = asyncio.run(deliberate("Pick a lottery.", ["safe", "risky", "longshot"], ctx=ctx))
    assert "error" not in result, result
    assert result["compiler"] == "harness"
    assert result["recommended"] in {"safe", "risky"}
    assert pipeline_module.last_detail()["llm"]["model"] == "harness-test"


def test_resume_deliberation_solves_submitted_code():
    verdict = resume_deliberation([GAMBLE_CODE], ["safe", "risky", "longshot"])
    assert "error" not in verdict, verdict
    assert verdict["compiler"] == "harness"
    assert verdict["recommended"] in {"safe", "risky"}


def test_resume_deliberation_reports_bad_code():
    verdict = resume_deliberation(["import os\n"])
    assert "error" in verdict
