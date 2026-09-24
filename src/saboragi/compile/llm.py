"""Thin OpenAI-compatible chat client with disk cache and cost tracking.

Works with OpenAI, any OpenAI-compatible proxy, OpenRouter, or local servers
(Ollama / LM Studio). The cache (keyed by model + messages + temperature)
makes benchmark runs reproducible and cheap to re-run.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from saboragi.config import Settings

_CODE_FENCE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str | None:
    """Pull the ```python block out of a response (fallback: raw text)."""
    matches = _CODE_FENCE.findall(text)
    for match in matches:
        if "class World" in match or "Model" in match:
            return match.strip()
    if matches:
        return matches[0].strip()
    if "class World" in text:
        return text.strip()
    return None


class ModelUnavailable(RuntimeError):
    """The configured API model cannot be called.

    Raised for a missing model, auth failure, rate limit, or an unreachable
    endpoint. Callers may compile with the harness model instead. The message
    is only the error type and status, never the provider body.
    """


_UNAVAILABLE_STATUS = {401, 402, 403, 404, 408, 409, 429, 500, 502, 503, 529}
_UNAVAILABLE_TYPES = {
    "APIConnectionError",
    "APITimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "InternalServerError",
    "ConnectError",
    "ReadTimeout",
    "ConnectTimeout",
}


def is_model_unavailable(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status in _UNAVAILABLE_STATUS:
        return True
    if type(exc).__name__ in _UNAVAILABLE_TYPES:
        return True
    cause = exc.__cause__
    return cause is not None and cause is not exc and is_model_unavailable(cause)


def _public_error(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    if status:
        return f"{type(exc).__name__} HTTP {status}"
    return type(exc).__name__


@dataclass
class LlmResponse:
    text: str
    in_tokens: int = 0
    out_tokens: int = 0


@dataclass
class LlmClient:
    settings: Settings
    calls: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    cache_hits: int = 0
    _client: object = field(default=None, repr=False)

    def _get_client(self):
        if self._client is None:
            import httpx
            from openai import OpenAI

            limit = self.settings.llm_timeout
            self._client = OpenAI(
                base_url=self.settings.base_url,
                api_key=self.settings.api_key,
                timeout=httpx.Timeout(limit, connect=min(15.0, limit)),
                max_retries=0,
            )
        return self._client

    @staticmethod
    def cache_key(model: str, messages: list[dict], temperature: float) -> str:
        blob = json.dumps(
            {"model": model, "messages": messages, "temperature": temperature},
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    def cost(self) -> float:
        return (
            self.in_tokens / 1e6 * self.settings.price_in_per_m
            + self.out_tokens / 1e6 * self.settings.price_out_per_m
        )

    def chat(self, messages: list[dict], temperature: float, max_tokens: int = 4096) -> LlmResponse:
        try:
            model = self.settings.require_model()
        except RuntimeError as exc:
            raise ModelUnavailable(str(exc)) from exc
        key = self.cache_key(model, messages, temperature)
        cached = self._read_cache(key)
        if cached is not None:
            self.cache_hits += 1
            self.in_tokens += cached.in_tokens
            self.out_tokens += cached.out_tokens
            return cached
        try:
            completion = self._get_client().chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ModelUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - provider SDK errors are a wide tree
            if is_model_unavailable(exc):
                raise ModelUnavailable(_public_error(exc)) from exc
            raise
        message = completion.choices[0].message.content or ""
        usage = completion.usage
        response = LlmResponse(
            text=message,
            in_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            out_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
        self._write_cache(key, response)
        self.calls += 1
        self.in_tokens += response.in_tokens
        self.out_tokens += response.out_tokens
        return response

    def _cache_path(self, key: str):
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.settings.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> LlmResponse | None:
        path = self.settings.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LlmResponse(
                text=data["text"],
                in_tokens=data.get("in_tokens", 0),
                out_tokens=data.get("out_tokens", 0),
            )
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _write_cache(self, key: str, response: LlmResponse) -> None:
        try:
            self._cache_path(key).write_text(
                json.dumps(
                    {
                        "text": response.text,
                        "in_tokens": response.in_tokens,
                        "out_tokens": response.out_tokens,
                    }
                ),
                encoding="utf-8",
            )
        except OSError:
            pass
