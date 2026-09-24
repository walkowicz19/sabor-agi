"""CLI: `saboragi-bench` runs the four-arm evaluation and writes a report."""

from __future__ import annotations

import argparse

from bench.problems import load_jsonl
from bench.report import build_report, render_markdown, write_run
from bench.runner import ARMS, run_suite
from saboragi.compile.llm import LlmClient
from saboragi.config import Settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the SaborAGI four-arm benchmark")
    parser.add_argument("--suite", default="bench/data/suite.jsonl")
    parser.add_argument("--arms", default=",".join(ARMS), help=f"subset of {sorted(ARMS)}")
    parser.add_argument("--limit", type=int, default=0, help="max problems (0 = all)")
    parser.add_argument("--runs-dir", default="runs")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    settings.require_model()
    problems = load_jsonl(args.suite)
    if args.limit:
        problems = problems[: args.limit]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms: {unknown} (choose from {sorted(ARMS)})")

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
