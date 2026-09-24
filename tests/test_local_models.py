"""Local model discovery stays on this machine, and the bench can use the harness."""

import json
from pathlib import Path

from bench.cli import main
from saboragi.compile.llm import LlmResponse
from saboragi.config import Settings
from saboragi.local_models import (
    LocalModel,
    choose_local_model,
    is_local_base_url,
    resolve_settings,
)

_ENV = (
    "SABORAGI_BASE_URL",
    "SABORAGI_MODEL",
    "SABORAGI_API_KEY",
    "SABORAGI_COMPILER",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENAI_API_KEY",
    "MODEL",
    "MODEL_ID",
)


def _clear_env(monkeypatch) -> None:
    monkeypatch.setattr("saboragi.config.load_dotenv", lambda: None)
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)


def test_local_hosts():
    assert is_local_base_url("http://localhost:11434/v1")
    assert is_local_base_url("http://127.0.0.1:1234/v1")
    assert is_local_base_url("http://[::1]:11434/v1")
    assert not is_local_base_url("https://openrouter.ai/api/v1")


def test_choose_prefers_the_named_model_then_a_code_model_then_the_newest():
    general = LocalModel("http://127.0.0.1:11434/v1", "general", created=50)
    coder = LocalModel("http://127.0.0.1:11434/v1", "demo-coder", created=10)
    older = LocalModel("http://127.0.0.1:11434/v1", "older", created=1)
    assert choose_local_model([general, coder], "older") == coder
    named = LocalModel("http://127.0.0.1:11434/v1", "older", created=1)
    assert choose_local_model([general, coder, named], "older") == named
    assert choose_local_model([general, coder], None) == coder
    assert choose_local_model([general, older], None) == general
    assert choose_local_model([], None) is None


def test_resolve_keeps_an_explicit_remote_endpoint():
    seen = {"called": False}

    def discover():
        seen["called"] = True
        return [LocalModel("http://127.0.0.1:11434/v1", "local")]

    settings = Settings(base_url="https://example.com/v1", model="cloud-model")
    resolved = resolve_settings(settings, discover)
    assert resolved.model == "cloud-model"
    assert resolved.base_url == "https://example.com/v1"
    assert seen["called"] is False


def test_resolve_keeps_an_explicit_local_port():
    def discover():
        raise AssertionError("an explicit local endpoint is not probed")

    settings = Settings(model="m", base_url="http://127.0.0.1:9/v1")
    assert resolve_settings(settings, discover) == settings


def test_resolve_fills_a_local_model_and_drops_a_name_with_no_server():
    found = [
        LocalModel("http://127.0.0.1:11434/v1", "desk", created=2),
        LocalModel("http://127.0.0.1:11434/v1", "py-coder", created=1),
    ]
    filled = resolve_settings(Settings(), lambda: found)
    assert filled.model == "py-coder"
    assert filled.base_url == "http://127.0.0.1:11434/v1"

    named = resolve_settings(Settings(model="desk"), lambda: found)
    assert named.model == "desk"

    swapped = resolve_settings(Settings(model="cloud-id"), lambda: found)
    assert swapped.model == "py-coder"

    quiet = resolve_settings(Settings(model="cloud-id"), lambda: [])
    assert quiet.model is None
    assert quiet.base_url == "http://localhost:11434/v1"


def test_api_key_alone_stays_on_localhost(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    settings = Settings.from_env()
    assert settings.base_url == "http://localhost:11434/v1"
    assert settings.model is None


def _tiny_suite(path: Path) -> None:
    problem = {
        "id": "p1",
        "family": "gamble",
        "horizon": 1,
        "description": "Choose hold or go.",
        "actions": ["hold", "go"],
        "q_values": {"hold": 1.0, "go": 0.0},
        "optimal": "hold",
        "event_name": "win",
        "event_description": "the chance of a win",
        "event_probs": {"hold": 0.5, "go": 0.5},
        "model_code": "class World: pass",
        "seed": 0,
        "extra": {},
    }
    path.write_text(json.dumps(problem) + "\n", encoding="utf-8")


def test_bench_uses_harness_when_no_model_is_served(monkeypatch, capsys, tmp_path):
    _clear_env(monkeypatch)
    suite = tmp_path / "suite.jsonl"
    _tiny_suite(suite)
    main(
        ["--suite", str(suite), "--limit", "1", "--runs-dir", str(tmp_path / "runs")],
        discover=lambda: [],
    )
    captured = capsys.readouterr()
    assert "status: needs_harness" in captured.out
    assert "compiler: harness" in captured.out
    assert list((tmp_path / "runs").glob("*")) == []


def test_bench_calls_the_discovered_local_model(monkeypatch, capsys, tmp_path):
    _clear_env(monkeypatch)
    suite = tmp_path / "suite.jsonl"
    _tiny_suite(suite)
    seen: list[str] = []

    def chat(self, messages, temperature, max_tokens=4096):
        seen.append(self.settings.model)
        return LlmResponse('```answer\n{"action": "hold", "p_event": 0.5}\n```')

    monkeypatch.setattr("saboragi.compile.llm.LlmClient.chat", chat)
    models = [LocalModel("http://127.0.0.1:11434/v1", "unit-local", created=3)]
    main(
        [
            "--suite",
            str(suite),
            "--arms",
            "direct",
            "--runs-dir",
            str(tmp_path / "runs"),
        ],
        discover=lambda: models,
    )
    assert seen == ["unit-local"]
    err = capsys.readouterr().err
    assert "unit-local" in err
    assert "127.0.0.1:11434" in err
