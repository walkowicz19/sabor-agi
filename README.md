# SaborAGI

SaborAGI is a pause before a choice that is unsure, has several steps, or is hard to take back. A language model writes the situation down once, as rules. This program checks that the picture can be played, then walks the possible futures and returns a verdict you can argue with.

Sabor means taste. Nothing here is trained on old projects, and nothing is fitted to one decision.

## What comes back

`deliberate` returns:

- the recommended option
- the expected value of each option
- the chance of the events you asked about
- a bad-day figure (5th percentile of the return)
- which guessed numbers would flip the winner
- whether the separate pictures agreed, and a confidence of high, medium, or low

If the pictures disagree, or a guess at the edge of its range would change the winner, confidence is low. That disagreement is part of the answer. The verdict does not build the new system for you.

## Install

Python 3.12 or newer, and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
uv run --group dev pytest -q
```

## Use it from Cursor

The server speaks MCP over stdio. It is meant to run on your machine, next to the editor. Copy `mcp.example.json` into your Cursor MCP config and replace `REPLACE_WITH_ABSOLUTE_PROJECT_PATH` with the folder that contains this file. If `uv` is not on the PATH Cursor uses, put the full path to `uv` in `command`.

There is no API key in that config. The model id and key stay in a `.env` file in the project folder, which is gitignored:

```
SABORAGI_MODEL=your-model-id
SABORAGI_API_KEY=your-key
SABORAGI_BASE_URL=https://openrouter.ai/api/v1
```

`SABORAGI_K` is how many separate pictures that same model writes. The default is 3.

If no model is configured, or the provider is down, `deliberate` returns `needs_harness`. The caller writes one `World` per job and sends them to `resume_deliberation`. `SABORAGI_COMPILER=external` skips that handoff and fails instead. `SABORAGI_COMPILER=harness` skips the API model.

Tools:

| Tool | What it does |
|---|---|
| `deliberate` | Write the situation, get a verdict |
| `resume_deliberation` | Solve worlds the caller already wrote |
| `simulate_model` | Solve one world you wrote yourself |
| `explain_last` | Show the last models, or a few sample paths |

## How a picture is scored

A world model is a small Python class: where things stand, what you can do, what happens next, and whether that step was worth it. Chance comes only from the `rng` the solver passes in. If every next step is listed in `outcomes()`, the walk is exact. Otherwise the solver samples.

A number you are unsure about goes in `params` as `Uncertain(best, low, high)`. The solver tries the low and high ends and says whether the winner changes.

Several pictures are written apart, so one confident paragraph cannot pass a guess off as a fact.

Driving, liquids, machines, a gather-then-finish loop, and a short forecast are ordinary functions in `saboragi.sim`. One call is one time step. Keep the horizon short and the action list small, because the exact solver lists every reachable state.

The code checker rejects obvious dangerous constructs, then runs the model in a separate process with a time limit and a memory cap. That checker is a guardrail, not a wall. Run the server on your own machine. Do not put it on a network where strangers send code.

## The samples

`usecases/` holds two fictional modernizations, a 2003 bank counter and a 2014 parts counter. The day counts are judgments written into the rules, not a measured history. `validation/` holds later checks: a clinic book, a warehouse move, a rent-or-buy split, and physical scenes where the better move changes when the situation changes.

## The benchmark

The bar for this project is a live comparison. On problems with a 3-step horizon and problems with a 10-step horizon, the engine arm has to show at least 10% lower regret than the code-interpreter arm.

Generate the suite, then run it with a configured model:

```bash
uv run python -m bench.generate
uv run saboragi-bench --arms engine,code_interpreter
```

The full four-arm run is `uv run saboragi-bench`. Reports land under `runs/`. The generated problems are `bench/data/suite.jsonl`.

That live comparison has not been scored yet. It needs `SABORAGI_MODEL` and a key. The suite itself is in the repo so the run can start as soon as a model is set.

## License

MIT. See `LICENSE`.
