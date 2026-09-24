"""Host side of the sandbox: guard, spawn, enforce timeout + memory cap."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from saboragi.sandbox import guard

# Directory that contains the saboragi package: src/ in a checkout, site-packages when installed.
SRC_DIR = Path(__file__).resolve().parents[2]


@dataclass
class RunResult:
    ok: bool
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    stage: str = ""  # "guard" | "worker" | "timeout" | "memory" | "protocol"
    seconds: float = 0.0


def _env_with_src() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _poll_memory(proc: subprocess.Popen, memory_mb: int) -> bool:
    """True if the process tree currently exceeds the memory cap."""
    try:
        import psutil

        root = psutil.Process(proc.pid)
        total = root.memory_info().rss
        for child in root.children(recursive=True):
            try:
                total += child.memory_info().rss
            except psutil.NoSuchProcess:
                pass
        return total > memory_mb * 1024 * 1024
    except Exception:  # noqa: BLE001 - psutil missing/dead pid means no cap
        return False


def run_op(
    code: str,
    op: str,
    payload: dict | None = None,
    *,
    timeout: float = 60.0,
    memory_mb: int = 1024,
) -> RunResult:
    """Guard ``code``, run ``op`` in a worker subprocess, return its answer."""
    started = time.time()
    problems = guard.check(code)
    if problems:
        return RunResult(ok=False, errors=problems, stage="guard")

    with tempfile.TemporaryDirectory(prefix="saboragi_") as tmp:
        code_path = Path(tmp) / "model_code.py"
        request_path = Path(tmp) / "request.json"
        code_path.write_text(code, encoding="utf-8")
        request_path.write_text(json.dumps({"op": op, "payload": payload or {}}), encoding="utf-8")
        # The host (an MCP client) owns this process's stdin. A worker that
        # inherits that pipe blocks until the client disconnects, so the tool
        # call never returns. Detach stdin.
        proc = subprocess.Popen(
            [sys.executable, "-m", "saboragi.sandbox.worker", str(code_path), str(request_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_env_with_src(),
        )
        try:
            while True:
                try:
                    out, err = proc.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    if _poll_memory(proc, memory_mb):
                        proc.kill()
                        proc.wait()
                        return RunResult(
                            ok=False,
                            errors=[f"worker exceeded memory cap ({memory_mb} MB)"],
                            stage="memory",
                            seconds=time.time() - started,
                        )
                    if time.time() - started > timeout:
                        proc.kill()
                        proc.wait()
                        return RunResult(
                            ok=False,
                            errors=[f"worker timed out after {timeout:.0f}s"],
                            stage="timeout",
                            seconds=time.time() - started,
                        )
        except Exception as exc:  # noqa: BLE001
            proc.kill()
            return RunResult(ok=False, errors=[f"sandbox error: {exc!r}"], stage="worker")

    seconds = time.time() - started
    if proc.returncode != 0:
        return RunResult(
            ok=False,
            errors=[f"worker exited with code {proc.returncode}: {(err or '')[-2000:]}"],
            stage="worker",
            seconds=seconds,
        )
    try:
        answer = json.loads((out or "").strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return RunResult(
            ok=False,
            errors=["worker produced no JSON output"],
            stage="protocol",
            seconds=seconds,
        )
    if not answer.get("ok"):
        return RunResult(
            ok=False,
            errors=[answer.get("error", "unknown worker error")],
            stage="worker",
            seconds=seconds,
        )
    return RunResult(ok=True, data=answer["data"], stage="worker", seconds=seconds)


def run_validate(
    code: str,
    *,
    timeout: float = 60.0,
    memory_mb: int = 1024,
    seed: int = 0,
    n_rollouts: int = 200,
) -> RunResult:
    """Validate untrusted model code in the sandbox."""
    return run_op(
        code,
        "validate",
        {"seed": seed, "n_rollouts": n_rollouts},
        timeout=timeout,
        memory_mb=memory_mb,
    )


def run_analyze(
    code: str,
    first_actions: list[str] | None = None,
    *,
    timeout: float = 240.0,
    memory_mb: int = 1024,
    seed: int = 0,
    exact_state_limit: int = 200_000,
    mcts_iterations: int = 20_000,
    mc_rollouts: int = 5_000,
    param_overrides: dict[str, float] | None = None,
) -> RunResult:
    """Solve untrusted model code in the sandbox; returns a SolveResult dict."""
    return run_op(
        code,
        "analyze",
        {
            "first_actions": first_actions,
            "seed": seed,
            "exact_state_limit": exact_state_limit,
            "mcts_iterations": mcts_iterations,
            "mc_rollouts": mc_rollouts,
            "param_overrides": param_overrides or {},
        },
        timeout=timeout,
        memory_mb=memory_mb,
    )


def run_inspect(
    code: str,
    *,
    timeout: float = 30.0,
    memory_mb: int = 512,
) -> RunResult:
    """Return a model's params, initial actions, and horizon (no solving)."""
    return run_op(code, "inspect", {}, timeout=timeout, memory_mb=memory_mb)


def run_sample(
    code: str,
    *,
    n_trajectories: int = 3,
    seed: int = 0,
    timeout: float = 60.0,
    memory_mb: int = 512,
) -> RunResult:
    """Sample random-policy trajectories from model code (for inspection)."""
    return run_op(
        code,
        "sample",
        {"n_trajectories": n_trajectories, "seed": seed},
        timeout=timeout,
        memory_mb=memory_mb,
    )
