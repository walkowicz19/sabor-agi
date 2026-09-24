"""Prompts that teach an LLM to write executable world models."""

from __future__ import annotations

API_SPEC = """\
You write an executable probabilistic world model as a Python subclass of saboragi.wm.Model.
Only these imports are available: math, random, numpy, itertools, functools, collections, \
dataclasses, statistics, `from saboragi.wm import Model, Uncertain`, and \
`from saboragi.sim import rk4, euler, bicycle_step, exchange, transfer, linear_project, \
agent_step, machine_step`.

API (implement every method; read parameters via self.param(name)):

class World(Model):
    horizon = <int: max steps; every episode MUST terminate at t <= horizon>
    params = {"name": <float> or Uncertain(value, low, high)}
    state_bounds = {"var": (low, high)}   # REQUIRED: cover ALL reachable values
    events = {"name": lambda s: ...}      # optional indicators in [0, 1] for asked-about chances

    def initial_state(self): ...          # return the start state (JSON-serializable dict)
    def actions(self, state): ...         # return non-empty list of action-name strings
    def transition(self, state, action, rng): ...   # sample and return the next state dict
    def reward(self, state, action, next_state): ...# one-step reward as a finite float
    def is_terminal(self, state, t): ...  # True when the episode ends
    def outcomes(self, state, action): ...# OPTIONAL, encouraged: [(prob, next), ...] summing to 1

Rules for transition/reward:
- Use ONLY the `rng` argument for randomness (rng.random(), rng.randint(a, b), rng.choice(s)).
  Never use global random, time, or anything nondeterministic.
- Never mutate the input `state`; build and return a new dict.
- States must be JSON-serializable (numbers, strings, booleans, or a short list of those \
for a small grid).
- Rewards must be finite numbers.
- Driving, liquid, machines, agent loops, and forecasts advance inside transition \
by calling the saboragi.sim helpers. One call is one time step. Do not import a \
physics engine or unroll an unbounded loop.
- Every action you list must change the state in at least some situation.
- If you define outcomes(), its probabilities must sum to 1 and match what transition() samples.

Rules for numbers you are unsure about:
- Put them in params as Uncertain(best_guess, low, high) with a plausible range, and use \
self.param("name") wherever the number appears.
- Do NOT silently invent precise constants for genuinely uncertain quantities; mark them Uncertain.

Reply with exactly one ```python block containing the full model code \
(class World(Model)); nothing else needed outside the block.\
"""

FRAMINGS = [
    (
        0.2,
        "You are a careful actuary. Prefer simple, robust models with honest uncertainty ranges.",
    ),
    (
        0.7,
        "You are a simulation engineer. Model the mechanics faithfully "
        "and double-check edge cases.",
    ),
    (
        1.0,
        "You are a creative operations researcher. Consider alternative interpretations of the "
        "situation before committing to one clear formalization.",
    ),
]


def build_messages(
    situation: str,
    options: list[str] | None,
    question_events: list[str] | None,
    framing: str,
) -> list[dict]:
    if options:
        choice_text = (
            "The decision maker's candidate first actions are exactly: "
            + ", ".join(f"{a!r}" for a in options)
            + ". Your actions() method must include all of them for the initial state."
        )
    else:
        choice_text = (
            "No candidate actions are given: define a sensible small set of first "
            "actions yourself via actions()."
        )
    if question_events:
        event_text = (
            "The decision maker also wants calibrated chances for: "
            + ", ".join(f"{e!r}" for e in question_events)
            + ". Expose each as an entry in events (a function of the state "
            "returning 0.0/1.0 or a probability in [0, 1])."
        )
    else:
        event_text = ""
    user = f"""\
{framing}

Situation to model:
{situation}

{choice_text}
{event_text}

{API_SPEC}"""
    return [
        {
            "role": "system",
            "content": (
                "You formalize decision situations as executable probabilistic "
                "world models. You reply with exactly one ```python block."
            ),
        },
        {"role": "user", "content": user},
    ]


def build_repair_messages(code: str, errors: list[str]) -> list[dict]:
    details = "\n".join(f"- {error}" for error in errors)
    return [
        {
            "role": "system",
            "content": (
                "You fix broken world-model code. Reply with exactly one "
                "```python block containing the complete corrected model."
            ),
        },
        {
            "role": "user",
            "content": f"""\
The model below failed automatic validity checks. Fix every issue and return the complete \
corrected model.

Failures:
{details}

Broken code:
```python
{code}
```

{API_SPEC}""",
        },
    ]
