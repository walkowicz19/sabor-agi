"""Find a model on this machine before any external API is considered.

Ollama (port 11434) and LM Studio (port 1234) are the servers we look at.
A call to one of them stays on localhost. An external endpoint is used only
when ``SABORAGI_BASE_URL`` points at one.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from saboragi.config import Settings

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_PROBE_URLS = (
    "http://127.0.0.1:11434/v1/models",
    "http://127.0.0.1:1234/v1/models",
)
_CODE_HINTS = ("coder", "code", "instruct")


@dataclass(frozen=True)
class LocalModel:
    base_url: str
    name: str
    created: int = 0


def is_local_base_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in _LOCAL_HOSTS


def choose_local_model(models: list[LocalModel], preferred: str | None) -> LocalModel | None:
    """Pick the named model, else a code-oriented one, else the newest."""
    if not models:
        return None
    if preferred:
        for model in models:
            if model.name == preferred:
                return model
    newest_first = sorted(models, key=lambda model: model.created, reverse=True)
    for hint in _CODE_HINTS:
        for model in newest_first:
            if hint in model.name.lower():
                return model
    return newest_first[0]


def _opener() -> urllib.request.OpenerDirector:
    # Local probes must not go through an HTTP proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _read_json(url: str, timeout: float) -> dict | None:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with _opener().open(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _models_from_openai_list(url: str, timeout: float) -> list[LocalModel]:
    payload = _read_json(url, timeout)
    if not payload:
        return []
    base = url[: -len("/models")] if url.endswith("/models") else url
    found: list[LocalModel] = []
    for item in payload.get("data") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        created = item.get("created") or 0
        try:
            created_at = int(created)
        except (TypeError, ValueError):
            created_at = 0
        found.append(LocalModel(base, str(item["id"]), created_at))
    return found


def _models_from_ollama_tags(timeout: float) -> list[LocalModel]:
    payload = _read_json("http://127.0.0.1:11434/api/tags", timeout)
    if not payload:
        return []
    found: list[LocalModel] = []
    for item in payload.get("models") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if not name:
            continue
        found.append(LocalModel("http://127.0.0.1:11434/v1", str(name), 0))
    return found


def discover_local_models(timeout: float = 2.0) -> list[LocalModel]:
    """Every model served on a local OpenAI-compatible port."""
    found: list[LocalModel] = []
    seen: set[tuple[str, str]] = set()
    batches = [_models_from_openai_list(url, timeout) for url in _PROBE_URLS]
    batches.append(_models_from_ollama_tags(timeout))
    for batch in batches:
        for model in batch:
            key = (model.base_url, model.name)
            if key in seen:
                continue
            seen.add(key)
            found.append(model)
    return found


def resolve_settings(
    settings: Settings,
    discover=discover_local_models,
) -> Settings:
    """Fill a missing model from localhost. Leave an explicit remote endpoint alone."""
    if not is_local_base_url(settings.base_url):
        return settings
    if settings.model and not _is_default_local(settings.base_url):
        return settings
    found = discover()
    if not found:
        # No server answered, so a leftover model name is dropped and the
        # caller uses the harness.
        return settings.with_overrides(model=None)
    chosen = choose_local_model(found, settings.model)
    if chosen is None:
        return settings
    return settings.with_overrides(base_url=chosen.base_url, model=chosen.name)


def _is_default_local(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path.rstrip("/")
    return host in _LOCAL_HOSTS and port == 11434 and path in {"", "/v1"}
