"""Aggregate scored rows into a report with the kill-criterion verdict.

Kill criterion (from the plan): the engine arm must show at least 10% lower
regret than the code-interpreter arm on the 3-step AND 10-step tiers.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from bench.runner import ScoredRow

BOOTSTRAP_ROUNDS = 1000
KILL_FRACTION = 0.10
KILL_TIERS = (3, 10)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def summarize(rows: list[ScoredRow]) -> dict:
    return {
        "n": len(rows),
        "accuracy": _mean([1.0 if r.correct else 0.0 for r in rows]),
        "regret": _mean([r.regret for r in rows]),
        "brier": _mean([r.brier for r in rows]),
        "valid_rate": _mean([1.0 if r.valid else 0.0 for r in rows]),
        "tool_calls": sum(r.tool_calls for r in rows),
        "llm_calls": sum(r.calls for r in rows),
        "cost": sum(r.cost for r in rows),
        "seconds": sum(r.seconds for r in rows),
    }


def bootstrap_diff(
    a: list[float], b: list[float], seed: int = 0, rounds: int = BOOTSTRAP_ROUNDS
) -> tuple[float, float, float]:
    """Mean(a - b) with a 95% bootstrap CI. Returns (diff, lo, hi)."""
    rng = random.Random(seed)
    base = _mean(a) - _mean(b)
    if not a or not b:
        return base, base, base
    diffs = []
    for _ in range(rounds):
        ra = [rng.choice(a) for _ in a]
        rb = [rng.choice(b) for _ in b]
        diffs.append(_mean(ra) - _mean(rb))
    diffs.sort()
    return base, diffs[int(0.025 * rounds)], diffs[int(0.975 * rounds) - 1]


def kill_check(rows: list[ScoredRow]) -> dict:
    """Per kill tier: engine regret vs code-interpreter regret + PASS/FAIL."""
    tiers = {}
    overall = True
    for tier in KILL_TIERS:
        eng = [r.regret for r in rows if r.arm == "engine" and r.horizon == tier]
        code = [r.regret for r in rows if r.arm == "code_interpreter" and r.horizon == tier]
        if not eng or not code:
            tiers[tier] = {"status": "missing-data", "pass": False}
            overall = False
            continue
        mean_eng, mean_code = _mean(eng), _mean(code)
        if mean_code == 0:
            passed = mean_eng == 0
        else:
            passed = mean_eng <= (1 - KILL_FRACTION) * mean_code
        diff, lo, hi = bootstrap_diff(eng, code)
        tiers[tier] = {
            "engine_regret": mean_eng,
            "code_regret": mean_code,
            "diff": diff,
            "ci95": [lo, hi],
            "pass": passed,
        }
        overall = overall and passed
    return {"tiers": tiers, "pass": overall}


def build_report(rows: list[ScoredRow]) -> dict:
    arms = sorted({r.arm for r in rows})
    tiers = sorted({r.horizon for r in rows})
    families = sorted({r.family for r in rows})
    by_arm = {arm: summarize([r for r in rows if r.arm == arm]) for arm in arms}
    by_arm_tier = {
        f"{arm}/h{horizon}": summarize([r for r in rows if r.arm == arm and r.horizon == horizon])
        for arm in arms
        for horizon in tiers
    }
    by_arm_family = {
        f"{arm}/{family}": summarize([r for r in rows if r.arm == arm and r.family == family])
        for arm in arms
        for family in families
    }
    kill = kill_check(rows)
    return {
        "by_arm": by_arm,
        "by_arm_tier": by_arm_tier,
        "by_arm_family": by_arm_family,
        "kill": kill,
        "verdict": "PASS" if kill["pass"] else "FAIL",
    }


def render_markdown(report: dict) -> str:
    lines = ["# SaborAGI benchmark report", ""]
    lines.append(f"## Verdict: {report['verdict']}")
    lines.append("")
    lines.append("Kill criterion: engine regret at least 10% below code-interpreter")
    lines.append("regret on the horizon-3 and horizon-10 tiers.")
    for tier in sorted(report["kill"]["tiers"]):
        info = report["kill"][tier]
        lines.append(f"- h{tier}: {info}")
    lines.append("")
    lines.append("## By arm")
    for arm, summary in report["by_arm"].items():
        lines.append(f"- {arm}: {json.dumps(summary, default=str)}")
    lines.append("")
    lines.append("## By arm x tier")
    for key, summary in report["by_arm_tier"].items():
        lines.append(f"- {key}: {json.dumps(summary, default=str)}")
    lines.append("")
    lines.append("## By arm x family")
    for key, summary in report["by_arm_family"].items():
        lines.append(f"- {key}: {json.dumps(summary, default=str)}")
    return "\n".join(lines) + "\n"


def write_run(rows: list[ScoredRow], report: dict, runs_dir: str = "runs") -> Path:
    import datetime

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(runs_dir) / stamp
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.jsonl", "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row.to_dict()) + "\n")
    with open(out / "report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    with open(out / "report.md", "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
    return out
