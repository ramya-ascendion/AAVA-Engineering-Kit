---
status: proposed (optional)
---

# The API shape is owned by one source, and clients generate their types from it

One place owns each API contract. Clients and docs generate from it. Nothing restates it by hand.

## Why

A hand-copied contract drifts, and the drift surfaces in production.

## Consequences

- A gate runs the generator with `--check` and fails when the committed output is stale. `tools/generated.py` is the pattern.
- Optional. Adopt it when the project has a public or cross-team API.
