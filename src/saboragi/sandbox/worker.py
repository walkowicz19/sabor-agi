"""Sandbox worker: loads one model file, runs one op, prints one JSON document.

Usage: ``python -m saboragi.sandbox.worker <code_path> <request_json>``

Only ``validate`` exists in step 1; ``analyze`` (solve) arrives with step 2.
Stdout from model code is captured so the protocol line stays parseable.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import time
import traceback


def _load_model(code_path: str):  # noqa: ANN202 - dynamic model type
    spec = importlib.util.spec_from_file_location("saboragi_user_model", code_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {code_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    from saboragi.wm.api import Model

    candidates = [
        obj
        for obj in vars(module).values()
        if isinstance(obj, type)
        and issubclass(obj, Model)
        and obj is not Model
        and obj.__module__ == module.__name__
    ]
    if not candidates:
        raise ImportError("no subclass of saboragi.wm.Model found in model code")
    preferred = [c for c in candidates if c.__name__ == "World"]
    cls = preferred[0] if preferred else candidates[0]
    try:
        return cls()
    except TypeError as exc:
        raise ImportError(f"model class {cls.__name__}() raised {exc!r}") from exc


def _op_validate(model, payload: dict) -> dict:
    from saboragi.validate.checks import run_checks

    report = run_checks(
        model,
        seed=payload.get("seed", 0),
        n_rollouts=payload.get("n_rollouts", 200),
    )
    return {"op": "validate", "report": report.to_dict()}


def _op_analyze(model, payload: dict) -> dict:
    from saboragi.solve.select import solve

    for name, value in payload.get("param_overrides", {}).items():
        model.set_param_override(name, value)
    result = solve(
        model,
        payload.get("first_actions"),
        seed=payload.get("seed", 0),
        exact_state_limit=payload.get("exact_state_limit", 200_000),
        mcts_iterations=payload.get("mcts_iterations", 20_000),
        mc_rollouts=payload.get("mc_rollouts", 5_000),
    )
    return {"op": "analyze", "result": result.to_dict()}


def _op_inspect(model, payload: dict) -> dict:
    import copy

    params = {}
    for name, value in model.params.items():
        if hasattr(value, "value"):
            params[name] = {
                "value": value.value,
                "low": value.low,
                "high": value.high,
                "uncertain": True,
            }
        else:
            params[name] = {"value": value, "uncertain": False}
    s0 = model.initial_state()
    return {
        "op": "inspect",
        "params": params,
        "actions": model.actions(copy.deepcopy(s0)),
        "horizon": model.horizon,
    }


def _op_sample(model, payload: dict) -> dict:
    import copy
    import random

    rng = random.Random(payload.get("seed", 0))
    n = min(5, max(1, payload.get("n_trajectories", 3)))
    trajectories = []
    for _ in range(n):
        state = model.initial_state()
        steps = [{"t": 0, "action": None, "reward": 0.0, "state": copy.deepcopy(state)}]
        total, t = 0.0, 0
        while not model.is_terminal(state, t):
            actions = model.actions(copy.deepcopy(state))
            action = rng.choice(actions)
            nxt = model.transition(copy.deepcopy(state), action, rng)
            reward = model.reward(state, action, nxt)
            total += reward
            state, t = nxt, t + 1
            steps.append(
                {"t": t, "action": action, "reward": reward, "state": copy.deepcopy(state)}
            )
            if t > model.horizon:
                break
        trajectories.append({"total": total, "steps": steps})
    return {"op": "sample", "trajectories": trajectories}


OPS = {
    "validate": _op_validate,
    "analyze": _op_analyze,
    "inspect": _op_inspect,
    "sample": _op_sample,
}


def main(argv: list[str]) -> int:
    code_path, request_path = argv[1], argv[2]
    with open(request_path, encoding="utf-8") as fh:
        request = json.load(fh)
    started = time.time()
    try:
        model = _load_model(code_path)
        handler = OPS.get(request.get("op"))
        if handler is None:
            result = {"ok": False, "error": f"unknown op {request.get('op')!r}"}
        else:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                data = handler(model, request.get("payload", {}))
            result = {"ok": True, "data": data, "stdout": buf.getvalue()}
    except Exception:  # noqa: BLE001 - worker must always answer in JSON
        result = {"ok": False, "error": traceback.format_exc(limit=5)}
    result["seconds"] = time.time() - started
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
