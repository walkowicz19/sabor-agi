# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

The user specified the replacement: Java 25 and Quarkus for the API, TypeScript and React for the counter, Lucide for icons. The legacy program is Java 8, Servlet 3.1, and JSP on Tomcat. This record belongs to the Oficina Leme fixture, not to the SaborAGI engine.

## Users

A counter clerk at the fictional municipal workshop Oficina Leme, on a shift, issuing spare parts against a job. A manager steps in to approve an issue and is the only person who may see unit cost.

## Product Purpose

The desk lets a clerk find a part and open a requisition, and lets a manager approve it only when the bin still has the quantity. Success is a requisition that cannot drive on-hand below zero, with cost hidden from the clerk.

## Positioning

The screen is the counter, not a brochure for the migration. The rule that stock cannot go negative, and the rule that cost belongs to the manager, are enforced by the server. A neighboring admin template could not truthfully claim those checks live only in the page.

## Operating Context

Internal workshop counter. One clerk, occasionally a manager. Short tasks: sign on, find a part, request a quantity, approve or refuse. The store is in memory and the people, parts, and costs are synthetic. Restarting the process drops requisitions.

## Capabilities and Constraints

- Part code is 6 digits. Quantity is an integer from 1 to 99.
- Clerks open requisitions for themselves. Only a manager can approve.
- Unit cost is manager-only.
- A requisition cannot drive on-hand below 0.
- The dead bin-transfer screen is not part of the counter.
- Dev sign-on values live in fixture configuration and are not a production secret store.
- UI copy is English. Assumed from the sibling use case, not a separate confirmation.
- No real workshop, no real prices, no customers, and no measured uptime. Demonstration numbers are synthetic and labeled as such.

## Brand Commitments

The product name is Oficina Leme. Icons are Lucide, chosen by the user. Voice is the language of a counter: part, bin, on hand, requisition, approve. No marketing claims.

## Evidence on Hand

No photographs, no real stock extract, and no testimony. Seed parts and people are authored for the fixture.

## Product Principles

- The server keeps the rule when the old page and the old servlet disagreed.
- A clerk's session cannot see another clerk's requisition or any unit cost.
- The counter shows the bin and the decision, and leaves the migration story to the use-case note.
- Synthetic rows stay marked as a fixture.

## Accessibility & Inclusion

WCAG 2.2 AA is the bar for this desk: keyboard use, visible focus, labels on fields, and status that is not color alone. The user asked for the Impeccable audit, which includes that bar.
