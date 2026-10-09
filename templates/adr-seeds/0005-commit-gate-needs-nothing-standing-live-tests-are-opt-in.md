---
status: accepted (baseline)
---

# The commit gate needs nothing standing, and live tests are opt-in

A commit runs only what needs a checkout and a shell. Tests that need a running service are marked `live`, are collected by directory, and run only with `--live` or at pre-push when the service is up. A push is never blocked because the service is switched off.

## Why

A commit gate that needs infrastructure is a commit gate people bypass.

## Consequences

- A skipped live test says what to start.
- One module, `tests/live_gate.py`, answers whether the live suite should run, so conftest and the hooks cannot disagree.
