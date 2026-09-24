# SaborAGI

<p align="center">
  <img src="assets/saboragi-logo.svg" alt="SaborAGI" width="420">
</p>

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

## Use it from an MCP client

The server speaks MCP over stdio. Paste this once into the client’s global MCP settings (Cursor, Claude Desktop, VS Code, or any client that uses `mcpServers`). It starts the same way in every workspace. The open folder does not have to be this repository. If `uv` is not on the PATH that client uses, put the full path to `uv` in `command`.

```json
{
  "mcpServers": {
    "saboragi": {
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "git+https://github.com/walkowicz19/sabor-agi",
        "saboragi"
      ]
    }
  }
}
```

That config only starts the local server. SaborAGI looks for a model already running on this machine: Ollama at `127.0.0.1:11434`, or LM Studio at `127.0.0.1:1234`. A model id and an API key are optional. A remote server is used when you set `SABORAGI_BASE_URL` to it.

`SABORAGI_K` is how many separate pictures that model writes. The default is 3.

When nothing local is reachable, `deliberate` returns `needs_harness`. The caller writes one `World` per job and sends them to `resume_deliberation`. `SABORAGI_COMPILER=harness` always uses that path. `SABORAGI_COMPILER=external` stays on the configured endpoint and skips the handoff.

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

## One local security check

Kairos Sotos 1.0 14B, running locally as `kairos-sotos:q6` (with a security-auditor instruction and a 2048-token context), was given one containment write-up and no answer key. Isolate the payment service: lost orders cost 40, and records still leave 5% of the time. Rotate the admin token and stay up: engineer time costs 8, and records leave 25% of the time. Wait until morning: no immediate cost, and records leave 55% of the time. Records leaving add 100. The best expected cost is rotate, at 33, against 45 and 55.

The local picture used those costs and chances. A sampled solve also picks rotate (about 31, 45, and 53). The automatic checker rejected the picture: isolate and wait can leave the state equal to the start when records do not leave, because there is no clock, and the repair returned the same code. The model also widened 25% to a range of 10–40%. At 40%, isolate wins.

Grok 4.7, given the same stated numbers in this session, produced an exact picture: −33, −45, −55, and the same choice. That is one decision and one picture each. It is separate from the horizon-3 and horizon-10 benchmark.

The opening is that the incident write-up stays on the machine. Kairos Sotos 1.0 14B supplies the picture. The solver walks the futures. The same check can sit in front of other hard-to-reverse security choices: when to isolate, when to stay up, and which guessed chance would flip the plan.

## The benchmark

The bar for this project is a live comparison. On problems with a 3-step horizon and problems with a 10-step horizon, the engine arm has to show at least 10% lower regret than the code-interpreter arm.

Generate the suite, then run it. The command uses a model already running on this machine. When none is running, the same command stays on the harness and keeps the problems on this machine.

```bash
uv run python -m bench.generate
uv run saboragi-bench --arms engine,code_interpreter
```

The full four-arm run is `uv run saboragi-bench`. Reports land under `runs/`. The generated problems are `bench/data/suite.jsonl`.

The live comparison is scored when that command finishes against a local model. A harness run prints `needs_harness` and leaves the kill criterion for a later scored run.

## License

MIT. See `LICENSE`.
