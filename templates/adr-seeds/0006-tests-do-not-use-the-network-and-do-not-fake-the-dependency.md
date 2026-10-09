---
status: accepted (baseline)
---

# Tests do not use the network, and no hand-written fake stands in for the real dependency

A test run needs no network. Anything a test downloads is staged once into a local directory. Delivery-path code is exercised against the real dependency, or against a recorded real response, never a hand-written fake that someone can bend to pass.

## Why

A fake agrees with the code that wrote it. A recorded real response can disagree, and that disagreement is the point.

## Consequences

- Recordings are scrubbed of secrets and personal data when captured.
- `offline/` proves the suite runs with the network off, and proves the proof: the run without the staged files must fail for the right reason.
