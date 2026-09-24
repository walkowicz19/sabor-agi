"""Step-4 tests: LLM plumbing, ensemble, sensitivity, verdict, pipeline.

No real LLM is used: a FakeLlm serves canned model code so the full
compile -> solve -> sensitivity -> verdict path runs deterministically.
"""

import textwrap
from types import SimpleNamespace

import pytest

from saboragi.analysis.sensitivity import find_flips
from saboragi.analysis.verdict import build_verdict
from saboragi.compile.compiler import compile_ensemble
from saboragi.compile.llm import LlmClient, LlmResponse, ModelUnavailable, extract_code
from saboragi.compile.prompts import build_messages, build_repair_messages
from saboragi.config import Settings
from saboragi.pipeline import analyze_code, deliberate
from saboragi.sandbox.runner import run_inspect
from saboragi.solve.types import OptionResult, SolveResult

FLIP_CODE = textwrap.dedent(
    """\
    ```python
    from saboragi.wm import Model, Uncertain


    class World(Model):
        horizon = 1
        params = {"p": Uncertain(0.4, low=0.2, high=0.6)}
        state_bounds = {"t": (0, 1), "wealth": (0, 100)}

        def initial_state(self):
            return {"t": 0, "wealth": 0}

        def actions(self, state):
            return ["A", "B"]

        def transition(self, state, action, rng):
            if action == "A":
                gain = 10
            elif rng.random() < self.param("p"):
                gain = 30
            else:
                gain = 0
            return {"t": 1, "wealth": state["wealth"] + gain}

        def reward(self, state, action, next_state):
            return float(next_state["wealth"] - state["wealth"])

        def is_terminal(self, state, t):
            return state["t"] >= 1

        def outcomes(self, state, action):
            if action == "A":
                return [(1.0, {"t": 1, "wealth": state["wealth"] + 10})]
            p = self.param("p")
            return [
                (p, {"t": 1, "wealth": state["wealth"] + 30}),
                (1 - p, {"t": 1, "wealth": state["wealth"]}),
            ]
    ```
    """
)

GUARDED_CODE = "```python\nimport os\n\nX = 1\n```\n"


class FakeLlm(LlmClient):
    def __init__(self, fresh: str, repair: str):
        super().__init__(Settings(model="fake"))
        self._script = {"fresh": fresh, "repair": repair}

    def chat(self, messages, temperature, max_tokens=4096):
        self.calls += 1
        last = messages[-1]["content"]
        key = "repair" if "validity checks" in last else "fresh"
        return LlmResponse(text=self._script[key])


def _settings(**overrides):
    base = {"k": 2, "model": "fake", "validate_timeout": 30, "analyze_timeout": 60}
    base.update(overrides)
    return Settings(**base)


def test_extract_code_variants():
    assert extract_code("```python\nclass World(Model):\n    pass\n```").startswith("class World")
    assert extract_code("no code here") is None
    assert extract_code("```\nprint(1)\n```") == "print(1)"


def test_cache_roundtrip_and_cost(tmp_path):
    settings = Settings(model="m", cache_dir=tmp_path)
    client = LlmClient(settings)
    client._write_cache("k1", LlmResponse(text="hi", in_tokens=10, out_tokens=5))
    cached = client._read_cache("k1")
    assert cached is not None and cached.text == "hi"
    client.in_tokens, client.out_tokens = 1_000_000, 2_000_000
    settings = Settings(model="m", price_in_per_m=1.0, price_out_per_m=2.0)
    assert LlmClient(settings, in_tokens=1_000_000, out_tokens=2_000_000).cost() == 5.0


def test_prompts_teach_the_api():
    messages = build_messages("Some situation.", ["a", "b"], ["boom"], "Frame.")
    blob = "\n".join(m["content"] for m in messages)
    for token in (
        "class World(Model)",
        "Uncertain",
        "state_bounds",
        "outcomes",
        "'a'",
        "'b'",
        "'boom'",
        "rng",
    ):
        assert token in blob
    repair = build_repair_messages("code", ["[bad] thing"])
    assert "thing" in repair[1]["content"]


def test_compiler_repairs_guard_failure():
    llm = FakeLlm(fresh=GUARDED_CODE, repair=FLIP_CODE)
    survivors, warnings = compile_ensemble(llm, _settings(k=1), "situation", ["A", "B"], None)
    assert len(survivors) == 1
    assert warnings == []


def test_compiler_drops_hopeless_code():
    llm = FakeLlm(fresh=GUARDED_CODE, repair=GUARDED_CODE)
    survivors, warnings = compile_ensemble(
        llm, _settings(k=1, max_repairs=0), "situation", ["A", "B"], None
    )
    assert survivors == []
    assert len(warnings) == 1 and "dropped" in warnings[0]


def test_inspect_reports_params():
    code = extract_code(FLIP_CODE)
    assert code is not None
    result = run_inspect(code)
    assert result.ok, result.errors
    assert result.data["params"]["p"]["uncertain"] is True
    assert result.data["actions"] == ["A", "B"]
    assert result.data["horizon"] == 1


def test_sensitivity_finds_flip():
    code = extract_code(FLIP_CODE)
    assert code is not None
    flips, warnings = find_flips(code, ["A", "B"], "B", _settings())
    assert warnings == []
    assert [(f.param, f.flips_at, f.new_best) for f in flips] == [("p", "low", "A")]


def _solve_result(best: str, evs: dict) -> SolveResult:
    return SolveResult(
        options=[OptionResult(a, ev, ev - 1, ev + 1, {}, ev - 2, 100) for a, ev in evs.items()],
        best=best,
        solver="exact",
        exact=True,
    )


def test_verdict_confidence_levels():
    agree = [_solve_result("A", {"A": 10.0, "B": 5.0}) for _ in range(3)]
    verdict = build_verdict(agree, ["A", "B"], [], [], 3)
    assert (verdict["recommended"], verdict["confidence"]) == ("A", "high")
    assert verdict["epistemic_spread"]["agree_on_best"] is True
    assert verdict["models_used"] == 3

    split = [
        _solve_result("A", {"A": 10.0, "B": 5.0}),
        _solve_result("B", {"A": 9.0, "B": 9.5}),
    ]
    verdict = build_verdict(split, ["A", "B"], [], [], 2)
    assert verdict["confidence"] == "low"

    single = build_verdict(agree[:1], ["A", "B"], [], [], 3)
    assert single["confidence"] == "medium"


def test_pipeline_deliberate_end_to_end():
    llm = FakeLlm(fresh=FLIP_CODE, repair=FLIP_CODE)
    verdict = deliberate("Take A or B.", ["A", "B"], None, _settings(k=2), llm)
    assert verdict["recommended"] == "B"
    assert verdict["models_used"] == 2
    assert verdict["confidence"] == "low"  # p@low flips the decision
    assert {"param": "p", "flips_at": "low", "new_best": "A"} in verdict["flip_parameters"]


def test_pipeline_analyze_code():
    code = extract_code(FLIP_CODE)
    assert code is not None
    verdict = analyze_code(code, ["A", "B"], _settings())
    assert verdict["recommended"] == "B"
    assert verdict["models_used"] == 1


def test_unavailable_model_hides_provider_body():
    client = LlmClient(Settings(model="m", api_key="x", base_url="http://127.0.0.1:9/v1"))

    class Boom(Exception):
        status_code = 429

        def __str__(self):
            return "user_id=secret-should-not-leak"

    def fail(**kwargs):
        raise Boom()

    client._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
    with pytest.raises(ModelUnavailable) as caught:
        client.chat([{"role": "user", "content": "hi"}], 0.0)
    assert "429" in str(caught.value)
    assert "secret" not in str(caught.value)


def test_ensemble_propagates_unavailable_model():
    class BoomLlm(LlmClient):
        def chat(self, messages, temperature, max_tokens=4096):
            raise ModelUnavailable("HTTP 429")

    with pytest.raises(ModelUnavailable):
        compile_ensemble(BoomLlm(Settings(model="m")), Settings(model="m", k=2), "s", ["a"], None)
