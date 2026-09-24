"""Step-6 tests: parsing, tool loops, scoring, and the kill criterion."""

from bench.arms import code_interpreter, direct, engine
from bench.arms.base import parse_answer
from bench.arms.code_interpreter import run_python
from bench.generate import build_suite
from bench.problems import Problem
from bench.report import bootstrap_diff, build_report, kill_check
from bench.runner import ARMS, ScoredRow, run_suite, score
from saboragi.compile.llm import LlmClient, LlmResponse
from saboragi.config import Settings
from tests.test_step4 import FLIP_CODE

ANSWER = '```answer\n{"action": "order_20", "p_event": 0.25}\n```'


class StubLlm(LlmClient):
    def __init__(self, handler):
        super().__init__(Settings(model="stub"))
        self._handler = handler

    def chat(self, messages, temperature, max_tokens=4096):
        self.calls += 1
        return LlmResponse(text=self._handler(messages))


def _problem() -> Problem:
    return build_suite(seed=3, per_family_per_tier=1, tiers=(1,))[1]


def _answer_for(problem: Problem, p: float = 0.25) -> str:
    return f'```answer\n{{"action": "{problem.optimal}", "p_event": {p}}}\n```'


def test_parse_answer():
    problem = _problem()
    good = parse_answer(problem, _answer_for(problem))
    assert good.valid and good.action == problem.optimal and good.p_event == 0.25
    assert not parse_answer(problem, "no fence").valid
    assert not parse_answer(problem, _answer_for(problem).replace(problem.optimal, "nope")).valid
    assert not parse_answer(problem, _answer_for(problem, p=2.0)).valid


def test_run_python_executes_and_guards():
    out = run_python("print(2 + 2)")
    assert "4" in out
    blocked = run_python("import os\nprint(1)")
    assert "GUARD" in blocked
    assert "Traceback" in run_python("raise ValueError('boom')")


def test_direct_arm_scores_optimal():
    problem = _problem()
    answer = f'```answer\n{{"action": "{problem.optimal}", "p_event": 0.25}}\n```'
    llm = StubLlm(lambda messages: answer)
    result = direct.run(problem, llm)
    assert result.answer.valid
    row = score(problem, "direct", result)
    assert row.correct and row.regret == 0.0
    true_p = problem.event_probs[problem.optimal]
    assert row.brier == (0.25 - true_p) ** 2


def test_code_arm_tool_loop_feeds_output_back():
    problem = _problem()
    seen = []

    def handler(messages):
        seen.append(messages[-1]["content"])
        if len(seen) == 1:
            return "Let me compute.\n```python\nprint(40 + 2)\n```"
        assert "42" in messages[-1]["content"]
        return _answer_for(problem)

    llm = StubLlm(handler)
    result = code_interpreter.run(problem, llm, Settings(model="stub"))
    assert result.answer.valid and result.tool_calls == 1


def test_engine_arm_uses_verdict():
    problem = Problem(
        id="toy-1",
        family="toy",
        horizon=1,
        description="Take A (10 for sure) or B (30 with some chance, else 0).",
        actions=["A", "B"],
        q_values={"A": 10.0, "B": 12.0},
        optimal="B",
        event_name="big_win",
        event_description="the chance of the big win",
        event_probs={"A": 0.0, "B": 0.4},
        model_code="",
        seed=0,
    )
    calls = {"n": 0}

    def handler(messages):
        calls["n"] += 1
        last = messages[-1]["content"]
        if "Situation to model:" in last:
            return FLIP_CODE
        if calls["n"] == 1:
            return (
                "```deliberate\n"
                '{"situation": "A pays 10, B pays 30 with chance p else 0.", '
                '"options": ["A", "B"], "question_events": []}\n'
                "```"
            )
        assert "VERDICT" in last and '"recommended": "B"' in last
        return '```answer\n{"action": "B", "p_event": 0.4}\n```'

    llm = StubLlm(handler)
    result = engine.run(problem, llm, Settings(model="stub", k=1))
    assert result.answer.valid and result.answer.action == "B"
    assert result.tool_calls == 1


def _row(arm: str, horizon: int, regret: float) -> ScoredRow:
    return ScoredRow(
        problem_id="x",
        family="toy",
        horizon=horizon,
        arm=arm,
        action=None,
        optimal="A",
        correct=regret == 0.0,
        valid=True,
        regret=regret,
        brier=0.0,
        tool_calls=0,
        calls=0,
        in_tokens=0,
        out_tokens=0,
        cost=0.0,
        seconds=0.0,
    )


def test_kill_criterion_pass_and_fail():
    rows = [
        _row(arm, horizon, regret)
        for horizon in (1, 3, 10)
        for arm, regret in (("engine", 0.0), ("code_interpreter", 0.5))
    ]
    assert kill_check(rows)["pass"] is True
    failing = [
        _row(arm, horizon, 0.49 if arm == "engine" else 0.5)
        for horizon in (1, 3, 10)
        for arm in ("engine", "code_interpreter")
    ]
    assert kill_check(failing)["pass"] is False


def test_bootstrap_diff_brackets_truth():
    diff, lo, hi = bootstrap_diff([0.0] * 20, [0.5] * 20, seed=0)
    assert diff == -0.5 and lo <= diff <= hi


def test_report_structure_and_runner_end_to_end():
    assert set(ARMS) == {"direct", "cot", "code_interpreter", "engine"}
    problems = build_suite(seed=3, per_family_per_tier=1, tiers=(1,))

    class Fixer(StubLlm):
        def chat(self, messages, temperature, max_tokens=4096):
            problem = self._current
            text = f'```answer\n{{"action": "{problem.optimal}", "p_event": 0.5}}\n```'
            self.calls += 1
            return LlmResponse(text=text)

    llm = Fixer(lambda messages: "")
    rows = []
    for problem in problems:
        llm._current = problem
        for arm in ("direct", "cot"):
            rows.append(score(problem, arm, ARMS[arm](problem, llm)))
    report = build_report(rows)
    assert report["by_arm"]["direct"]["accuracy"] == 1.0
    assert report["by_arm"]["cot"]["accuracy"] == 1.0
    assert report["verdict"] in ("PASS", "FAIL")

    pager = Fixer(lambda messages: ANSWER)
    pager._current = problems[0]
    suite_rows = run_suite(problems[:2], ["direct"], Settings(model="stub"), pager)
    assert len(suite_rows) == 2
    assert all(r.seconds >= 0 for r in suite_rows)
    assert pager.calls == 2
