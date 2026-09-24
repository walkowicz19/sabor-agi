"""Ask SaborAGI which Oficina Leme plan to take. Loads .env. Prints no secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from saboragi.config import Settings
from saboragi.pipeline import deliberate

OPTIONS = [
    "strangler_counter_first",
    "big_bang_rewrite",
    "facade_keep_tomcat",
]

SITUATION = """
A team of 2 developers will replace a fictional 2014 internal app: Oficina Leme,
a municipal workshop parts counter. It is Java 8, Servlet 3.1 and JSP on Tomcat
8.5, javax.servlet, no manual. The source is small and has been read. Defects
that must not ship: passwords stored and compared as plaintext; the session id
is not rotated on sign-on; the approve action checks the manager role only in
the JSP, so the servlet accepts any signed-on clerk; requisition reads are not
scoped, so any session can open any id and see unit cost; part search
concatenates the typed text into a SQL string; the JSP refuses to issue more
parts than are on hand, but the servlet allows it and stock goes negative. A
dead bin-transfer screen is never linked and must not be ported. Rules that
must survive: part code is 6 digits, requisition quantity is an integer from 1
to 99, a requisition cannot drive on-hand below 0, clerks create requisitions
for themselves, only a manager can approve, unit cost is manager-only. The
replacement stack is fixed: Java 25, Quarkus, and a TypeScript React counter.
The store stays in memory for this fixture.

Three plans, pick the first action. Score expected engineer-days consumed,
including repair and a credential incident. Fewer days is better. Miss and
incident are independent.

strangler_counter_first: 22 certain engineer-days. Days 1-16 build the Quarkus
sign-on (hashed passwords, new token, login rate limit), literal part lookup,
and requisitions that refuse negative stock, with the role check and cost field
enforced on the server, plus tests. Days 17-22 put the React counter in front
and retire Tomcat. Chance a real counter rule is missed: 10%. A miss costs 18
engineer-days. Tomcat stops on day 22, so plaintext passwords and the open
requisition reads end then. Chance of a credential incident during those 22
days: 6%. That incident costs 35 engineer-days.

big_bang_rewrite: 28 certain engineer-days for one rewrite of sign-on, counter,
the report page, and cutover on day 28. Chance a real rule is missed: 32%.
Repair costs 18 engineer-days. Tomcat runs the whole time, so the chance of a
credential incident before cutover is 9%, costing 35 engineer-days.

facade_keep_tomcat: 8 certain engineer-days for a Quarkus proxy and a React
skin that still posts to the old servlets. Plaintext passwords, the JSP-only
role check, the open requisition reads, the SQL concatenation, and negative
stock all stay. Chance of missing a current behavior: 0%, repair 0. Chance of
a credential incident over the following year: 28%, costing 70 engineer-days.
The real rewrite is still required and costs another 26 engineer-days.

Days for one run are base + later + repair if missed + incident cost if incident.
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
