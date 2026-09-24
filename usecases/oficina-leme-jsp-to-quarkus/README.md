# Use case: 2014 Java 8 Tomcat JSP to Java 25 + Quarkus

Fictional municipal workshop. It is not a real parts room and it is not an attack guide. `legacy/` is the 2014 counter. `modern/` is the replacement slice. `decision/` is the SaborAGI solve that chose which replacement to build.

SaborAGI did not emit the Java. It scored three plans as executable stochastic models, and the implementation followed the plan that won.

## Legacy program

The app is Java 8, Servlet 3.1, and JSP, packaged for Tomcat 8.5. `web.xml` uses the JCP Java EE 7 schema. There is no manual. The rules below were read out of the source.

Kept:

- Part code is 6 digits. Quantity is an integer from 1 to 99.
- Clerks open requisitions. A manager approves.
- Unit cost is manager-only.
- A requisition must not drive on-hand below 0.

Dropped or fixed:

| 2014 behavior | Where | What the port does |
|---|---|---|
| Passwords are stored and compared as the typed characters. | `PlainPasswords` | PBKDF2-HMAC-SHA256, 120,000 iterations, random salt. The password is not stored. |
| Sign-on keeps the session id the browser already sent. | `SessionGate`, `LoginServlet` | A new 32-byte token is issued, and the previous token for that person is dropped. |
| The page shows Approve only for `MANAGER`. The servlet accepts any signed-on role. | `Approver` | Approve and reject return 403 unless the role is `MANAGER`. |
| Any signed-on session can read any requisition, including unit cost. | `RequisitionServlet.doGet` | A clerk receives 404 for someone else's id. The clerk view has no `unitCost`. |
| Name search pastes the typed text into a SQL string. | `PartSearch.sqlFor` | Lookup is an in-memory literal match. The response contains no SQL. |
| The JSP refuses a quantity above on-hand. The servlet subtracts anyway and stock goes negative. | `RequisitionBook` | Approve checks on-hand and leaves stock unchanged when the bin is short. |
| `/transfer` is mapped and never linked from the counter. | `BinTransferServlet`, `CounterMenu` | Not ported. `GET` and `POST /transfer` are 404. |

## The decision

A team of two has a fixed target stack, Java 25, Quarkus, and a TypeScript React counter, and three ways to start. The score is expected engineer-days consumed, including repair and a credential incident. Fewer days is better.

The probabilities and costs were written into the situation. They are judgments about this fixture, not measured frequencies from a workshop.

| Plan | Certain days | Miss | Repair if missed | Incident | Incident cost |
|---|---:|---:|---:|---:|---:|
| `strangler_counter_first` | 22 | 10% | 18 | 6% | 35 |
| `big_bang_rewrite` | 28 | 32% | 18 | 9% | 35 |
| `facade_keep_tomcat` | 8, then a later rewrite of 26 | 0% | 0 | 28% | 70 |

Miss and incident are independent. Days for one run are

`base + later + (repair if missed) + (incident cost if incident)`.

Expected days:

- Strangler: `22 + 0.10×18 + 0.06×35 = 25.90`
- Big bang: `28 + 0.32×18 + 0.09×35 = 36.91`
- Facade: `8 + 26 + 0.28×70 = 53.60`

The facade is cheapest on the certain part and misses nothing, because it keeps the JSP behavior. It also keeps the plaintext passwords and the open requisition reads, so the incident term dominates.

## How it was solved

No model id was configured, so `deliberate` returned `needs_harness`. Three `World` classes were written from the three framings and solved together with `resume_deliberation`. The sources are `decision/harness/model_0.py` (actuary: shared schedule slack, soft facade incident cost), `model_1.py` (the stated figures as given), and `model_2.py` (incident chances marked `Uncertain`). `decision/plans_model.py` is the same arithmetic without a sensitivity range, for `simulate_model`.

All three survived the sandbox. Sensitivity did not flip the ranking. The actuary's slack sits on every plan, so it cannot change the order. The facade incident cost at 45 still leaves the facade worse than the big bang, and the incident-chance ranges in the third model do not catch the strangler.

Result in `decision/verdict.json`:

| Plan | Expected reward | Expected days | Incident | Missed behavior | Models ranking it first |
|---|---:|---:|---:|---:|---:|
| `strangler_counter_first` | −25.90 | 25.90 | 6% | 10% | 3 |
| `big_bang_rewrite` | −36.91 | 36.91 | 9% | 32% | 0 |
| `facade_keep_tomcat` | −53.60 | 53.60 | 28% | 0% | 0 |

Confidence is **high**: three models were requested, three survived, they agree, nothing flipped, and there were no warnings. `epistemic_spread` on the winner is `[−25.9, −25.9]`.

High confidence means the formalizations agree on these figures. It does not mean the percentages were measured.

The 5th-percentile returns are about 57 days for the strangler (the incident, without the miss), 63 for the big bang, and 104 for the facade.

## What was implemented

The winning plan is the counter slice first: sign-on, part lookup, and requisitions. `modern/` is that API. `web/` is the React desk: TypeScript, Vite, and Lucide, drawn as a gauge board. The needle is the requested quantity. Signal red starts at on-hand. A manager approves from the lever on the lead dial.

- `POST /sessions` checks the fixture user and returns a new bearer token, role, and display name. Five failures inside 15 minutes lock that id; the next attempt is 429 with `Retry-After`. `DELETE /sessions` drops the token.
- `GET /parts` requires the bearer token. Clerks do not receive `unitCost`. `q` is a literal match on code or name, at most 40 characters. The list is marked synthetic.
- `POST /requisitions` is clerks only. Part code must be 6 digits and quantity must be 1 through 99. Stock does not move yet.
- `POST /requisitions/{id}/approve` is managers only. It decrements on-hand, or returns 409 and leaves the bin unchanged.
- `POST /requisitions/{id}/reject` is managers only and does not move stock.
- `GET /requisitions/{id}` is 404 when the row is missing or belongs to another clerk.

The store is in memory. Restarting the process drops requisitions and sessions and restores the seed bins. The passwords in `application.properties` are a dev fixture.

Passwords use PBKDF2 because it is in the JDK and this fixture does not take an extra crypto library. A deployment that can take a maintained library should prefer Argon2id. The session lasts 30 minutes, which is long for a high-risk path and is a fixture choice so a demo shift can finish.

## Run

Requires JDK 25 and Maven 3.9 or newer. This repo keeps both under `.tools/`. From `modern/`:

```powershell
$env:JAVA_HOME = "D:\Projects\sabor-agi\.tools\jdk25\jdk-25.0.4.1+1"
$env:Path = "$env:JAVA_HOME\bin;D:\Projects\sabor-agi\.tools\maven\apache-maven-3.9.16\bin;" + $env:Path
mvn quarkus:dev
```

The API listens on `http://localhost:8081`.

The desk, from `web/`:

```powershell
npm install
npm run dev
```

Vite serves `http://localhost:5173` and proxies `/sessions`, `/parts`, and `/requisitions` to the API. Sign-on values are typed at the counter. They are not compiled into the page.

Dev users, override these outside a real deployment:

| Id | Password | Role | Name |
|---|---|---|---|
| 2001 | 135790 | clerk | Nia Costa |
| 2002 | 112233 | clerk | Rita Campos |
| 3001 | 246810 | manager | Helio Prado |

```powershell
mvn test
```

`POST /sessions` returns a token. Send it as `Authorization: Bearer …` on `/parts` and `/requisitions`.

The legacy module compiles as Java 8 and its tests lock the old behavior. From `legacy/`, `mvn test`.

To re-solve the hand-written world, call `simulate_model` on `decision/plans_model.py`. To re-solve the ensemble on disk, pass the three files in `decision/harness/` to `resume_deliberation`. `decision/decide.py` compiles a fresh ensemble and needs a working model id.
