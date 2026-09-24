"""Runtime settings, read from SABORAGI_* environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


def _first_set(*names: str) -> str | None:
    for name in names:
        raw = os.environ.get(name)
        if raw not in (None, ""):
            return raw
    return None


def load_dotenv() -> None:
    """Load a project .env into the process. Existing variables win."""
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        return
    root = Path(__file__).resolve().parents[2]
    _load(root / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "not-needed"
    model: str | None = None
    k: int = 3
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".saboragi" / "cache")
    price_in_per_m: float = 0.0
    price_out_per_m: float = 0.0
    max_repairs: int = 2
    llm_timeout: float = 180.0
    validate_timeout: float = 60.0
    analyze_timeout: float = 240.0
    memory_mb: int = 1024
    max_sensitivity_params: int = 8

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        defaults = cls()
        cache = os.environ.get("SABORAGI_CACHE_DIR")
        api_key = _first_set("SABORAGI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")
        if os.environ.get("SABORAGI_BASE_URL"):
            base_url = os.environ["SABORAGI_BASE_URL"]
        elif api_key and api_key != defaults.api_key:
            base_url = "https://openrouter.ai/api/v1"
        else:
            base_url = defaults.base_url
        return cls(
            base_url=base_url,
            api_key=api_key or defaults.api_key,
            model=_first_set("SABORAGI_MODEL", "OPENROUTER_MODEL", "MODEL", "MODEL_ID"),
            k=_env_int("SABORAGI_K", defaults.k),
            cache_dir=Path(cache) if cache else defaults.cache_dir,
            price_in_per_m=_env_float("SABORAGI_PRICE_IN", defaults.price_in_per_m),
            price_out_per_m=_env_float("SABORAGI_PRICE_OUT", defaults.price_out_per_m),
            max_repairs=_env_int("SABORAGI_MAX_REPAIRS", defaults.max_repairs),
            llm_timeout=_env_float("SABORAGI_LLM_TIMEOUT", defaults.llm_timeout),
            validate_timeout=_env_float("SABORAGI_VALIDATE_TIMEOUT", defaults.validate_timeout),
            analyze_timeout=_env_float("SABORAGI_ANALYZE_TIMEOUT", defaults.analyze_timeout),
            memory_mb=_env_int("SABORAGI_MEMORY_MB", defaults.memory_mb),
            max_sensitivity_params=_env_int(
                "SABORAGI_MAX_SENSITIVITY_PARAMS", defaults.max_sensitivity_params
            ),
        )

    def with_overrides(self, **changes: object) -> Settings:
        return replace(self, **changes)

    def require_model(self) -> str:
        if not self.model:
            raise RuntimeError(
                "No LLM configured: set SABORAGI_MODEL (and SABORAGI_BASE_URL / SABORAGI_API_KEY "
                "for non-local endpoints)."
            )
        return self.model
