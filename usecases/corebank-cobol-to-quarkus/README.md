# Use case: 2003 COBOL teller menu to Java 25 + Quarkus

Fictional branch-banking fixture. It is not a real bank and it is not an attack guide. `legacy/BNKMENU.cbl` is the legacy program. `modern/` is the replacement. `decision/` is the SaborAGI solve that chose which replacement to build.

SaborAGI did not emit the Java. It scored three plans as executable stochastic models, and the implementation followed the plan that won.

## Legacy program

`BNKMENU.cbl` is dated 2003-04-17. It has a teller menu and customer registration, and it shipped with no manual. The rules below were read out of the source.

Kept:

- Customer number is 10 digits. Branch code is 4 digits. PIN is 6 digits. Name is required and at most 40 characters.
- A new customer opens with balance 0 and status `A`.
- Registration and PIN change require an operator sign-on.
- The menu offers register, inquiry, PIN change, and exit.

Dropped or fixed:

| COBOL behavior | Where | What the port does |
|---|---|---|
| Two name checks disagree. `3100-CHECK-NAME` rejects blanks. `3110-VALIDATE-NAME` then forces the name valid, so blanks are stored. | `NamePolicy` | Only the rejecting rule remains. |
| Operator `9999` / `ADMIN` signs on with no lookup. | `OperatorDirectory` | That pair is not accepted. |
| Inquiry ignores the sign-on flag and displays `PIN-PLAIN`. | `CustomerResource`, `CustomerView` | Inquiry requires `X-Operator-Token`. The response type has no PIN. |
| PINs are stored and compared as plaintext. | `PinHasher` | PBKDF2-HMAC-SHA256, 120,000 iterations, random salt. The PIN is not stored. |
| `5000-CHANGE-PIN` only displays `REWRITE NOT IMPLEMENTED`, but the menu offers it. | `CustomerService.changePin` | The old hash is verified, then replaced. Balance is unchanged. |
| `7000-WIRE-TRANSFER` is never reached from the menu and subtracts the fee twice. | menu and teller page | Not ported. Neither surface lists it. |

## The decision

A team of two has a fixed target stack, Java 25 and Quarkus, and three ways to start. The score is expected engineer-days consumed, including repair and a credential incident. Fewer days is better.

The probabilities and costs were written into the situation. They are judgments about this fixture, not measured frequencies from a bank.

| Plan | Certain days | Miss | Repair if missed | Incident | Incident cost |
|---|---:|---:|---:|---:|---:|
| `strangler_registration_first` | 25 | 12% | 25 | 5% | 40 |
| `big_bang_rewrite` | 30 | 35% | 25 | 8% | 40 |
| `facade_keep_cobol` | 10, then a later rewrite of 30 | 0% | 0 | 30% | 80 |

Miss and incident are independent. Days for one run are

`base + later + (repair if missed) + (incident cost if incident)`.

Expected days, multiplying the branches:

- Strangler: `25 + 0.12×25 + 0.05×40 = 30.00`
- Big bang: `30 + 0.35×25 + 0.08×40 = 41.95`
- Facade: `10 + 30 + 0.30×80 = 64.00`

The facade looks cheapest on the certain part and misses nothing, because it keeps the COBOL behavior. It also keeps the plaintext PIN store, so the incident term dominates.

## How the simulated paths worked

A world model is a small Python class, `World(Model)`, with a finite horizon, a state, a list of actions, a transition that may use only the `rng` it is given, a reward, and an end condition. Optional `outcomes()` lists every next state with a probability that sums to 1. Optional `events` are indicators in `[0, 1]`. Optional `Uncertain(value, low, high)` parameters are the ones sensitivity is allowed to move.

The server never asks the language model to roll the dice. The model writes the code once. A sandbox checks it. A solver runs it. This use case went through three paths. All three ranked the plans the same way.

### Path 1 — `deliberate` with the configured API model

`decision/decide.py` calls `pipeline.deliberate` with K = 3. That asks the configured model to write three independent `World` classes, repairs each at most once, then solves the survivors.

That call did not produce a model. The endpoint was unavailable (rate limit on a free pool, and later no model id was configured). `ModelUnavailable` stops the ensemble immediately so a 429 is not reported as "the models failed validation." The benchmark arm still uses only this path, so an eval run is not silently answered by a different model.

### Path 2 — `simulate_model` on a hand-written world

`decision/plans_model.py` is one `World` with the table above. Reward is the negative of days, because the solver maximizes reward. `outcomes()` enumerates miss × incident, skipping branches whose probability is 0.

Horizon is 1 and `outcomes()` exists, so the solver is exact backward induction. For a one-step model that is just the sum of `probability × reward` over the branches. The expected values are the 30.00 / 41.95 / 64.00 figures, with no sampling error. The confidence interval on an exact value is a point.

`worst_case_p5` is separate. After the exact value is known, the solver draws 20,000 returns under that action, sorts them, and reports the low 5th percentile. Those returns are still negative days:

| Plan | Exact expected days | 5th-percentile return | Reading of that tail |
|---|---:|---:|---|
| Strangler | 30.00 | −65 | About 65 days: the incident branch, without the miss. |
| Big bang | 41.95 | −70 | About 70 days: incident on the larger base. |
| Facade | 64.00 | −120 | About 120 days: the 30% incident branch is already most of the left tail. |

Event probabilities come from the same branches: `credential_incident` and `missed_behavior`.

One surviving model is reported as confidence **medium**, even when the arithmetic is exact. A single formalization can launder a bad guess into a sharp number. This path was the first successful solve. `decision/verdict.json` has since been replaced by the ensemble result, which matches these values.

### Path 3 — harness ensemble

With no API model available, three session sub-agents each wrote a `World`, using a different framing (careful, mechanical, alternative reading). The sources are `decision/harness/model_0.py`, `model_1.py`, and `model_2.py`. They were validated and solved together by `deliberate_codes`. The compiler field on the verdict is `harness`.

Each model was checked in a sandbox before it could affect the verdict: the AST guard, 200 random rollouts, `outcomes()` summing to 1 and matching the sampled transitions, state bounds, and the requirement that `actions()` include the three plan names. A model that fails is dropped. All three survived, with no warnings.

The solver then ran sensitivity. Any `Uncertain` parameter is set to its low and its high, one at a time, and the problem is solved again. A flip is recorded when the best action changes.

- The actuary model added `schedule_slack = Uncertain(0, 0, 5)` to every plan. The same number on every plan cannot change the ranking.
- The research model marked the facade incident cost `Uncertain(80, 55, 110)`. At 55 the facade is still about 56.5 expected days, which is still worse than 41.95. At 110 it is worse still. No flip.

Result in `decision/verdict.json`:

| Plan | Expected reward | Expected days | Incident | Missed behavior | Models ranking it first |
|---|---:|---:|---:|---:|---:|
| `strangler_registration_first` | −30.00 | 30.00 | 5% | 12% | 3 |
| `big_bang_rewrite` | −41.95 | 41.95 | 8% | 35% | 0 |
| `facade_keep_cobol` | −64.00 | 64.00 | 30% | 0% | 0 |

Confidence is **high**: three models were requested, three survived, they agree on the best action, nothing flipped, and there were no warnings. `epistemic_spread` on the winner is `[−30, −30]`. The models did not disagree.

Two kinds of uncertainty stay separate:

- Aleatoric, inside one world: the incident and miss probabilities, and the 5th-percentile tail.
- Epistemic, across worlds: whether independent formalizations pick the same action, and whether a parameter's plausible range changes the pick.

High confidence here means the formalizations agree. It means the stated numbers pick the strangler. It does not mean those probabilities were measured.

## What was implemented

The winning plan is the registration slice first, then the menu in front of it. `modern/` is that slice.

- `POST /sessions` checks the configured operator and returns a token. `DELETE /sessions` drops it. `9999` / `ADMIN` gets 401.
- `POST /customers` registers. Duplicate customer numbers are 409. Blank or over-long names, and customer, branch, or PIN values that are not the legacy widths, are 400.
- `GET /customers/{customerNumber}` returns number, name, branch, balance, and status.
- `POST /customers/{customerNumber}/pin` replaces the hash after the current PIN matches.
- `GET /menu` lists codes 1, 2, 3, and 9.
- `http://localhost:8080/` is the teller page for those four actions.

The store is in memory. Restarting the process drops customers. The operator id and PIN in `application.properties` are a dev fixture and have to be overridden outside that fixture.

## Can SaborAGI raise accuracy and make the implementation safer?

On this use case, yes for the plan choice, and only indirectly for the code.

**Accuracy of the choice.** The expected values are computed from the transitions, not estimated in prose. With `outcomes()` present, that computation is exact, so the 30 / 41.95 / 64 split is arithmetic rather than a model's mental estimate. The ensemble is the check on the formalization: three independent writings of the same situation produced the same ranking, and the parameters they marked as soft did not flip it. A single compiled model would have been labeled medium on purpose. Disagreement, or a flip inside the stated range, would have been labeled low.

That accuracy is conditional on the situation text. If the 5%, 12%, or 30% figures are wrong, the recommendation can be the wrong plan and the confidence can still be high, because every model was given the same figures. Sensitivity only moves parameters the models marked `Uncertain`. It does not search for a different story.

This use case is not the benchmark. The four-arm eval (direct answer, chain of thought, a code interpreter, and this engine) has its own suite of problems with known optima. The kill criterion there is regret, not a claim about banking code. It has not been run on `BNKMENU`.

**Safer implementation.** The solver never saw the Java. What it changed is which program got written. The winning plan removes the plaintext PIN store on the registration path and leaves the dead wire paragraph behind. The facade, which would have kept both, lost on the scored incident cost. The situation text also named the defects that must not ship: the backdoor, the unsigned inquiry, the disagreeing name checks, the plaintext PIN, and the double debit. The port and the tests follow that list.

The sandbox guards the world-model code (imports, timeouts, consistency of `outcomes()`). It does not audit the Quarkus service. Safety of the service is what the tests and the browser pass checked:

- 10 tests, including blank names, duplicate numbers, digit widths, the backdoor operator, session required on register and inquiry, PIN change without returning the new PIN, sign-off, and the absence of a wire action.
- A browser pass of sign-on failure, the menu, registration, inquiry, a missing customer, and exit. The customer screen showed balance 0, status A, and no PIN.

Residual risk that the verdict does not close: the 12% miss term is still a real chance that an unnamed rule was dropped; the customer store is not durable; the dev operator PIN is in the fixture config; this is one menu, not a core-banking system. Those are properties of the slice, and a later deliberation would be a new situation with new numbers.

## Run

Requires JDK 25 and Maven 3.9 or newer. From `modern/`:

```powershell
mvn quarkus:dev
```

Open `http://localhost:8080`.

Dev operator, override these outside a real deployment:

- id `1001`
- pin `246810`

```powershell
mvn test
```

`POST /sessions` returns a token. Send it as `X-Operator-Token` on `/customers`.

To re-solve the hand-written world without an API model, call `simulate_model` (or `pipeline.analyze_code`) on `decision/plans_model.py`. To re-solve the ensemble already on disk, pass the three files in `decision/harness/` to `resume_deliberation`. `decision/decide.py` compiles a fresh ensemble and needs a working model id in the environment.
