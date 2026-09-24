"""Build a full benchmark suite: families x tiers with fixed seeds."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from bench.generators import allocation, dice, gamble, inventory, staffing
from bench.problems import Problem, dump_jsonl

FAMILIES = {
    "gamble": gamble.generate,
    "inventory": inventory.generate,
    "staffing_queue": staffing.generate,
    "resource_allocation": allocation.generate,
    "dice_game": dice.generate,
}

TIERS = (1, 3, 10)
MAX_ATTEMPTS = 50


def build_suite(
    seed: int = 0,
    per_family_per_tier: int = 10,
    tiers: tuple[int, ...] = TIERS,
) -> list[Problem]:
    problems: list[Problem] = []
    for tier in tiers:
        for family, generate in FAMILIES.items():
            made = 0
            attempts = 0
            while made < per_family_per_tier and attempts < MAX_ATTEMPTS:
                attempts += 1
                problem_seed = hash((seed, family, tier, attempts)) & 0xFFFFFFFF
                problem = generate(random.Random(problem_seed), tier, made, problem_seed)
                if problem is None:
                    continue
                problem.description += (
                    "\n\nYour options (answer with exactly one of these "
                    f"strings): {', '.join(problem.actions)}."
                    f"\nAlso estimate {problem.event_description}."
                )
                problems.append(problem)
                made += 1
            if made < per_family_per_tier:
                raise RuntimeError(
                    f"could only generate {made}/{per_family_per_tier} {family} h{tier} problems"
                )
    return problems


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the SaborAGI benchmark suite")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--per", type=int, default=10, help="problems per family tier")
    parser.add_argument("--out", default="bench/data/suite.jsonl")
    args = parser.parse_args(argv)
    problems = build_suite(seed=args.seed, per_family_per_tier=args.per)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_jsonl(problems, str(out))
    print(f"wrote {len(problems)} problems to {out}")


if __name__ == "__main__":
    main()
