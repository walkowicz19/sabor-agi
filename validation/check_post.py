"""Check the LinkedIn post against the solver.

The scenes named in the post are solved again. New scenes and new decisions
sit beside them, so a move that was right in one picture can lose in another.
"""

from __future__ import annotations

import json
from pathlib import Path

from saboragi.config import Settings
from saboragi.pipeline import deliberate_codes
from saboragi.sandbox.runner import run_validate
from saboragi.solve.exact import try_exact

ROOT = Path(__file__).resolve().parents[1]
POST_SCENES = [
    ("straight road", ROOT / "tests/reference_models/drive.py", "accelerate", 3.0),
    ("full cup", ROOT / "tests/reference_models/tank.py", "drain", 0.5),
    ("empty-handed helper", ROOT / "tests/reference_models/agent_loop.py", "lookup", 5.0),
    ("cool press", ROOT / "tests/reference_models/machine.py", "run", 3.0),
    ("straight numbers", ROOT / "tests/reference_models/forecast.py", "trust_trend", 0.0),
]
NEW_SCENES = [
    ("mark off to the side", ROOT / "validation/physical/road_mark.py", "steer", None),
    ("empty cup to fill", ROOT / "validation/physical/cups_share.py", "share", 1.0),
    ("press already hot", ROOT / "validation/physical/hot_press.py", "cool", 1.0),
    ("bent numbers", ROOT / "validation/physical/bent_forecast.py", "repeat_last", 0.0),
    ("facts already gathered", ROOT / "validation/physical/facts_ready.py", "finish", 5.0),
]


def _world(path: Path):
    namespace: dict = {}
    exec(path.read_text(encoding="utf-8"), namespace)  # noqa: S102 - local fixture
    return namespace["World"]()


def _solve_scene(path: Path) -> dict:
    code = path.read_text(encoding="utf-8")
    checked = run_validate(code, timeout=60)
    if not checked.ok:
        return {"ok": False, "errors": checked.errors}
    model = _world(path)
    solved = try_exact(model, model.actions(model.initial_state()), p5_samples=0)
    if solved is None:
        return {"ok": False, "errors": ["exact solver declined"]}
    winner = solved.option(solved.best)
    return {
        "ok": True,
        "best": solved.best,
        "ev": winner.ev,
        "options": {opt.action: opt.ev for opt in solved.options},
    }


def _days(verdict: dict) -> list[dict]:
    rows = []
    for option in verdict["options"]:
        rows.append(
            {
                "action": option["action"],
                "days": round(-option["ev"], 2),
                "ev": option["ev"],
                "p_events": option["p_events"],
                "worst_case_p5": option["worst_case_p5"],
                "models_ranking_first": option["models_ranking_first"],
            }
        )
    return rows


def _codes(folder: Path) -> list[str]:
    return [path.read_text(encoding="utf-8") for path in sorted(folder.glob("model_*.py"))]


def run() -> dict:
    scenes = []
    for label, path, best, ev in POST_SCENES + NEW_SCENES:
        solved = _solve_scene(path)
        scenes.append(
            {
                "label": label,
                "file": str(path.relative_to(ROOT)),
                "expected": best,
                "expected_ev": ev,
                **solved,
            }
        )

    clinic = deliberate_codes(
        _codes(ROOT / "validation/clinic"),
        ["start_with_book", "rewrite_everything", "keep_old_desk"],
        Settings(k=3, analyze_timeout=180, memory_mb=512),
    )
    warehouse = deliberate_codes(
        _codes(ROOT / "validation/warehouse"),
        ["phased_move", "weekend_move"],
        Settings(k=2, analyze_timeout=180, memory_mb=512),
    )
    split = deliberate_codes(
        _codes(ROOT / "validation/split"),
        ["rent", "buy"],
        Settings(k=2, analyze_timeout=180, memory_mb=512),
    )
    return {
        "scenes": scenes,
        "clinic": clinic,
        "warehouse": warehouse,
        "split": split,
    }


def main() -> None:
    report = run()
    out = ROOT / "validation" / "results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    for scene in report["scenes"]:
        mark = "ok" if scene.get("ok") and scene.get("best") == scene["expected"] else "FAIL"
        print(f"{mark:4} {scene['label']}: {scene.get('best')} ev={scene.get('ev')}")
    for name in ("clinic", "warehouse", "split"):
        verdict = report[name]
        print(
            f"{name}: {verdict['recommended']} confidence={verdict['confidence']} "
            f"agree={verdict['epistemic_spread']['agree_on_best']} "
            f"flips={verdict['flip_parameters']}"
        )
        for row in _days(verdict):
            print(f"  {row['action']}: days={row['days']} events={row['p_events']}")


if __name__ == "__main__":
    main()
