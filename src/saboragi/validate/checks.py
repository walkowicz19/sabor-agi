"""Executable validity checks for a world-model instance.

Every check returns structured issues (``code`` + ``message``) so the compiler
can feed them back to the LLM for repair. Checks run inside the sandbox worker
for untrusted code; the same functions run in-process for trusted code.
"""

from __future__ import annotations

import copy
import json
import math
import random
from dataclasses import dataclass, field

from saboragi.wm.api import Model, State, Uncertain, canonical

OUTCOMES_PROB_TOL = 1e-6


@dataclass
class CheckIssue:
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}

    @classmethod
    def from_dict(cls, data: dict) -> CheckIssue:
        return cls(code=data["code"], message=data["message"])


@dataclass
class CheckReport:
    errors: list[CheckIssue] = field(default_factory=list)
    warnings: list[CheckIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str) -> None:
        self.errors.append(CheckIssue(code, message))

    def warn(self, code: str, message: str) -> None:
        self.warnings.append(CheckIssue(code, message))

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    @classmethod
    def from_dict(cls, data: dict) -> CheckReport:
        return cls(
            errors=[CheckIssue.from_dict(e) for e in data.get("errors", [])],
            warnings=[CheckIssue.from_dict(w) for w in data.get("warnings", [])],
        )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def run_checks(
    model: Model,
    *,
    seed: int = 0,
    n_rollouts: int = 200,
    max_outcome_states: int = 10,
    outcome_samples: int = 2000,
) -> CheckReport:
    """Run all validity checks against a model instance."""
    report = CheckReport()

    _check_declarations(model, report)
    if report.errors:
        return report

    try:
        s0 = model.initial_state()
    except Exception as exc:  # noqa: BLE001 - surfaced as a check issue
        report.error("initial_state", f"initial_state() raised {exc!r}")
        return report

    if not _check_state_shape(model, s0, report, where="initial_state"):
        return report

    try:
        actions0 = model.actions(copy.deepcopy(s0))
    except Exception as exc:  # noqa: BLE001
        report.error("actions", f"actions(initial_state) raised {exc!r}")
        return report
    if (
        not isinstance(actions0, list)
        or not actions0
        or not all(isinstance(a, str) for a in actions0)
    ):
        report.error("actions", "actions() must return a non-empty list of str")
        return report

    _check_determinism(model, s0, actions0[0], seed, report)
    states = _check_rollouts(model, s0, seed, n_rollouts, report)
    if states:
        _check_action_effects(model, states, report)
        _check_outcomes(model, states, max_outcome_states, outcome_samples, seed, report)
        _check_events(model, states, report)
    return report


def _check_declarations(model: Model, report: CheckReport) -> None:
    if not isinstance(model.horizon, int) or isinstance(model.horizon, bool):
        report.error("horizon", "horizon must be an int")
    elif model.horizon <= 0:
        report.error("horizon", "horizon must be positive")
    if not isinstance(model.params, dict):
        report.error("params", "params must be a dict")
    else:
        for name, value in model.params.items():
            if isinstance(value, Uncertain):
                continue
            if not _is_number(value):
                report.error("params", f"param {name!r} must be a number or Uncertain")
    if not isinstance(model.state_bounds, dict):
        report.error("state_bounds", "state_bounds must be a dict")
    else:
        for name, bounds in model.state_bounds.items():
            if (
                not isinstance(bounds, (list, tuple))
                or len(bounds) != 2
                or not all(_is_number(v) for v in bounds)
                or not bounds[0] <= bounds[1]
            ):
                report.error(
                    "state_bounds",
                    f"state_bounds[{name!r}] must be a (low, high) number pair",
                )
    if not isinstance(model.events, dict):
        report.error("events", "events must be a dict")
    else:
        for name, fn in model.events.items():
            if not callable(fn):
                report.error("events", f"event {name!r} is not callable")


def _check_state_shape(model: Model, state: State, report: CheckReport, *, where: str) -> bool:
    try:
        json.dumps(state)
    except (TypeError, ValueError):
        report.error("state_not_serializable", f"{where}: state is not JSON-serializable")
        return False
    if not isinstance(state, dict):
        report.error("state_not_dict", f"{where}: state must be a dict")
        return False
    ok = True
    for name, bounds in model.state_bounds.items():
        if name not in state:
            report.error("missing_bound_var", f"{where}: bounded var {name!r} missing")
            ok = False
            continue
        value = state[name]
        if not _is_number(value):
            report.error("bound_var_not_numeric", f"{where}: bounded var {name!r} is not numeric")
            ok = False
        elif not bounds[0] <= value <= bounds[1]:
            report.error(
                "out_of_bounds",
                f"{where}: {name}={value} outside [{bounds[0]}, {bounds[1]}]",
            )
            ok = False
    return ok


def _step(model: Model, state: State, action: str, rng: random.Random) -> tuple[State, float]:
    nxt = model.transition(copy.deepcopy(state), action, rng)
    rew = model.reward(state, action, nxt)
    return nxt, rew


def _check_determinism(
    model: Model, s0: State, action: str, seed: int, report: CheckReport
) -> None:
    try:
        s1, r1 = _step(model, s0, action, random.Random(seed))
        s2, r2 = _step(model, s0, action, random.Random(seed))
    except Exception as exc:  # noqa: BLE001
        report.error("transition_raised", f"transition/reward raised {exc!r}")
        return
    if s1 != s2 or r1 != r2:
        report.error(
            "nondeterministic",
            "transition/reward with a fixed seed gave different results; "
            "use only `rng` for randomness and do not mutate inputs",
        )


def _check_rollouts(
    model: Model, s0: State, seed: int, n_rollouts: int, report: CheckReport
) -> list[tuple[State, int]]:
    """Sample rollouts; validate bounds, rewards, termination. Returns (state, t)."""
    rng = random.Random(seed)
    seen: dict[str, tuple[State, int]] = {}

    def record(state: State, t: int) -> None:
        key = canonical(state)
        if key not in seen:
            seen[key] = (copy.deepcopy(state), t)

    for rollout in range(n_rollouts):
        state = copy.deepcopy(s0)
        record(state, 0)
        terminated = model.is_terminal(state, 0)
        t = 0
        try:
            while not terminated:
                if t >= model.horizon:
                    break
                actions = model.actions(copy.deepcopy(state))
                if not actions:
                    report.error(
                        "no_actions",
                        f"rollout {rollout}: no legal actions at step {t}",
                    )
                    break
                action = rng.choice(actions)
                nxt, rew = _step(model, state, action, rng)
                if not _is_number(rew) or not math.isfinite(rew):
                    report.error(
                        "bad_reward",
                        f"rollout {rollout}: reward {rew!r} is not a finite number",
                    )
                    break
                t += 1
                if not _check_state_shape(model, nxt, report, where=f"step {t}"):
                    break
                state = nxt
                record(state, t)
                terminated = model.is_terminal(state, t)
        except Exception as exc:  # noqa: BLE001
            report.error("rollout_raised", f"rollout {rollout} raised {exc!r}")
            break
        if not terminated:
            report.error(
                "never_terminal",
                f"rollout {rollout}: no terminal state within horizon {model.horizon}",
            )
            break
        if report.errors:
            break
    return list(seen.values())


def _check_action_effects(
    model: Model, states: list[tuple[State, int]], report: CheckReport
) -> None:
    legal: dict[str, bool] = {}
    effective: dict[str, bool] = {}
    rng = random.Random(999)
    for state, t in states[:300]:
        try:
            if model.is_terminal(state, t):
                continue
            actions = model.actions(copy.deepcopy(state))
        except Exception:  # noqa: BLE001 - rollout checks already cover raises
            continue
        for action in actions:
            legal[action] = True
            if effective.get(action):
                continue
            try:
                nxt = model.transition(copy.deepcopy(state), action, rng)
            except Exception:  # noqa: BLE001
                continue
            if nxt != state:
                effective[action] = True
    for action in sorted(legal):
        if not effective.get(action):
            report.error(
                "action_no_effect",
                f"action {action!r} never changed the state in sampled states",
            )


def _check_outcomes(
    model: Model,
    states: list[tuple[State, int]],
    max_states: int,
    n_samples: int,
    seed: int,
    report: CheckReport,
) -> None:
    tested = 0
    rng = random.Random(seed + 1)
    for state, t in states:
        if tested >= max_states:
            break
        try:
            if model.is_terminal(state, t):
                continue
            actions = model.actions(copy.deepcopy(state))
        except Exception:  # noqa: BLE001
            continue
        for action in actions:
            if tested >= max_states:
                break
            try:
                dist = model.outcomes(copy.deepcopy(state), action)
            except Exception as exc:  # noqa: BLE001
                report.error("outcomes_raised", f"outcomes() raised {exc!r}")
                return
            if dist is None:
                continue
            tested += 1
            _check_single_outcomes(model, state, action, dist, n_samples, rng, report)
            if report.errors:
                return


def _check_single_outcomes(
    model: Model,
    state: State,
    action: str,
    dist: list[tuple[float, State]],
    n_samples: int,
    rng: random.Random,
    report: CheckReport,
) -> None:
    where = f"outcomes({action!r})"
    if not isinstance(dist, list) or not dist:
        report.error("bad_outcomes", f"{where}: must be a non-empty list")
        return
    total = 0.0
    for prob, _ in dist:
        if not _is_number(prob) or prob < 0:
            report.error("bad_outcomes", f"{where}: probabilities must be >= 0")
            return
        total += prob
    if abs(total - 1.0) > OUTCOMES_PROB_TOL:
        report.error("bad_outcomes", f"{where}: probabilities sum to {total}, not 1")
        return
    counts: dict[str, int] = {}
    try:
        for _ in range(n_samples):
            nxt = model.transition(copy.deepcopy(state), action, rng)
            key = canonical(nxt)
            counts[key] = counts.get(key, 0) + 1
    except Exception as exc:  # noqa: BLE001
        report.error("transition_raised", f"sampling {where} raised {exc!r}")
        return
    expected_keys = {canonical(s) for _, s in dist}
    for key in counts:
        if key not in expected_keys:
            report.error(
                "outcomes_mismatch",
                f"{where}: transition sampled a state missing from outcomes()",
            )
            return
    for prob, nxt in dist:
        freq = counts.get(canonical(nxt), 0) / n_samples
        tol = max(0.02, 3 * math.sqrt(prob * (1 - prob) / n_samples)) if prob < 1 else 0
        if abs(freq - prob) > tol:
            report.error(
                "outcomes_mismatch",
                f"{where}: sampled frequency {freq:.3f} != declared {prob:.3f}",
            )
            return


def _check_events(model: Model, states: list[tuple[State, int]], report: CheckReport) -> None:
    for name, fn in model.events.items():
        for state, _ in states[:100]:
            try:
                value = fn(copy.deepcopy(state))
            except Exception as exc:  # noqa: BLE001
                report.error("event_raised", f"event {name!r} raised {exc!r}")
                break
            if not _is_number(value) or not 0 <= value <= 1:
                report.error(
                    "bad_event",
                    f"event {name!r} must return a number in [0, 1], got {value!r}",
                )
                break
