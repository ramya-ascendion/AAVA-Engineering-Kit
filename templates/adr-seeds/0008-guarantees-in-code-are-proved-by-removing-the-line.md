---
status: proposed (optional)
---

# A guarantee stated in code is proved by removing the line that keeps it

A docstring that states a guarantee is a claim. `tools/guarantees.py` lists each guarantee with the line that keeps it and the tests that prove it. It removes that line on a copy of a commit and checks those tests go red.

## Why

A claim nothing can falsify is decoration.

## Consequences

- The proof runs on a `git archive` copy of a commit, never in the working tree.
- Results are proved, exempt, unmeasured, unproved or broken. A guarantee the machine cannot measure lets a push through, and says so.
- Optional. Adopt it when the project has claims worth proving. See `docs/agents/guarantees.md`.
