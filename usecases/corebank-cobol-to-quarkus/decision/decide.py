"""Ask SaborAGI which modernization plan to take. Loads .env. Prints no secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from saboragi.config import Settings
from saboragi.pipeline import deliberate

OPTIONS = [
    "strangler_registration_first",
    "big_bang_rewrite",
    "facade_keep_cobol",
]

SITUATION = """
A team of 2 developers has 30 working days to replace a fictional 2003 COBOL
branch program, BNKMENU. It is a teller menu plus customer registration for a
core-banking training fixture. There is no documentation. The source has
duplicated name checks that disagree (one rejects blanks, the later copy
accepts them), a wire-transfer paragraph that the menu never calls and that
debits the fee twice, plaintext PINs stored and displayed, a hardcoded
operator sign-on, and an inquiry path that does not check sign-on.

The replacement stack is fixed: Java 25 and Quarkus. Business rules that must
survive: 10-digit customer number, name required up to 40 characters, 4-digit
branch, 6-digit PIN, new customers open with balance 0. The wire-transfer
paragraph is dead and must not be ported. Plaintext PINs must not ship.

Three plans, pick the first action:

strangler_registration_first: Days 1-18 build the Quarkus registration,
inquiry, and PIN change with hashed PINs and tests for the rules above.
Days 19-25 put the menu in front of that API and cut over. Chance a real
registration rule is missed: 12%. A miss costs 25 engineer-days of repair
and a delayed cutover. COBOL stops running on day 25, so the plaintext-PIN
exposure ends then. Chance of a credential-exposure incident during the 25
days COBOL is still live: 5%. That incident costs 40 engineer-days.

big_bang_rewrite: All 30 days go into one rewrite of menu plus registration,
with a single cutover on day 30. Chance a real rule is missed: 35%. Same
25-engineer-day repair cost. COBOL runs the whole time, so the chance of a
credential-exposure incident before cutover is 8%, costing 40 engineer-days.
No dual-running after day 30.

facade_keep_cobol: Spend 10 days on a Java facade that still calls the COBOL
program. The plaintext PIN store, the blank-name bug, the dead wire paragraph,
and the unsigned inquiry stay. Chance of a credential-exposure incident within
the next year: 30%, costing 80 engineer-days. The real rewrite is still
required afterwards and costs another 30 engineer-days. Almost no chance of
missing a current behavior, because the behavior does not change.

Score each plan by expected engineer-days consumed, including incident and
repair costs. Fewer days is better.
"""


def main() -> None:
    settings = Settings.from_env().with_overrides(
        k=3,
        max_repairs=1,
        llm_timeout=90,
        validate_timeout=45,
        analyze_timeout=120,
    )
    verdict = deliberate(
        SITUATION,
        OPTIONS,
        ["credential_incident", "missed_behavior"],
        settings,
    )
    out = Path(__file__).resolve().parent / "verdict.json"
    out.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print("recommended", verdict["recommended"])
    print("confidence", verdict["confidence"])
    print("models_used", verdict["models_used"])
    for opt in verdict["options"]:
        print("option", opt["action"], "ev", round(float(opt["ev"]), 2))
    print("flips", len(verdict.get("flip_parameters") or []))
    print("warnings", len(verdict.get("warnings") or []))
    print("wrote", out.name)


if __name__ == "__main__":
    main()
