"""CLI: `saboragi-bench` runs the four-arm evaluation and writes a report.

The model is whichever one is already running on this machine. An external
endpoint is used only when SABORAGI_BASE_URL names it. When no model can be
called, the run stays on the harness and does not score a guessed suite.
"""

from __future__ import annotations

import argparse
import os
import sys

from bench.problems import load_jsonl
from bench.report import build_report, render_markdown, write_run
from bench.runner import ARMS, run_suite
from saboragi.compile.harness import INSTRUCTION
from saboragi.compile.llm import LlmClient
from saboragi.config import Settings
from saboragi.local_models import discover_local_models, is_local_base_url, resolve_settings


def _compiler_mode() -> str:
    mode = os.environ.get("SABORAGI_COMPILER", "auto").strip().lower()
    return mode if mode in {"auto", "external", "harness"} else "auto"


def _harness(problems: list, reason: str) -> None:
    print("compiler: harness")
    print("status: needs_harness")
    print(reason)
    print(INSTRUCTION)
    print(f"{len(problems)} problems are waiting on the harness.")


def main(argv: list[str] | None = None, discover=discover_local_models) -> None:
    parser = argparse.ArgumentParser(description="Run the SaborAGI four-arm benchmark")
    parser.add_argument("--suite", default="bench/data/suite.jsonl")
    parser.add_argument("--arms", default=",".join(ARMS), help=f"subset of {sorted(ARMS)}")
    parser.add_argument("--limit", type=int, default=0, help="max problems (0 = all)")
    parser.add_argument("--runs-dir", default="runs")
    args = parser.parse_args(argv)

    named = Settings.from_env()
    settings = resolve_settings(named, discover=discover)
    problems = load_jsonl(args.suite)
    if args.limit:
        problems = problems[: args.limit]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms: {unknown} (choose from {sorted(ARMS)})")

    mode = _compiler_mode()
    if mode == "external" and not settings.model:
        raise SystemExit(
            "SABORAGI_COMPILER=external and no model is reachable. "
            "Start a local model server, or set SABORAGI_BASE_URL to an endpoint you chose."
        )
    if mode == "harness" or not settings.model:
        why = (
            "SABORAGI_COMPILER=harness, so the API model is skipped."
            if mode == "harness"
            else "No model is being served on this machine."
        )
        _harness(problems, why)
        return

    if is_local_base_url(settings.base_url):
        where = settings.base_url
    else:
        where = settings.base_url.split("/")[2]
    if named.model and named.model != settings.model:
        print(
            f"bench model: {settings.model} at {where} (requested {named.model})",
            file=sys.stderr,
        )
    else:
        print(f"bench model: {settings.model} at {where}", file=sys.stderr)

    llm = LlmClient(settings)
    rows = run_suite(problems, arms, settings, llm)
    report = build_report(rows)
    out = write_run(rows, report, args.runs_dir)
    print(render_markdown(report))
    print(f"wrote {len(rows)} rows to {out}")
    print(
        f"LLM usage: {llm.calls} calls, {llm.in_tokens} in / {llm.out_tokens} out "
        f"tokens, ~${llm.cost():.4f}"
    )


if __name__ == "__main__":
    main()
