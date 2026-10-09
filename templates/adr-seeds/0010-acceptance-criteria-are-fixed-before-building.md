---
status: accepted (baseline)
---

# Acceptance criteria are fixed before building, and a hard-zero failure class is named

Before a ticket is built, "good enough" is written down as acceptance criteria. At least one failure class is named hard-zero: a result in that class fails the work however good the average is.

## Why

A bar chosen after the result is a bar the result was fitted to.

## Consequences

- The ticket gate refuses to hand off a ticket whose criteria are missing.
- A bar that must move is moved by a new decision record, not by editing the old one.
