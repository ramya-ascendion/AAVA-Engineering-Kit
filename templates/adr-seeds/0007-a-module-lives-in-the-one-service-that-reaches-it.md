---
status: accepted (baseline)
---

# A module lives inside the one service that reaches it, and a script enforces the boundaries

A module sits in the one service that uses it. Shared code is a short list of leaves that anything may import. A crossing from one service to another is allowed only when it is listed with a reason. `tools/layering.py` reads the import graph and refuses an unlisted crossing.

## Why

"More than one caller" is not a reason to share. Shared code couples services, and the coupling is invisible until it hurts.

## Consequences

- Every allowed crossing carries a one-line reason in the table.
- A crossing that no longer exists is reported as stale.
