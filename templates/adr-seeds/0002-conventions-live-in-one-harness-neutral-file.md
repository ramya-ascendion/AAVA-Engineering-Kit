---
status: accepted (baseline)
---

# Project conventions live in AGENTS.md, and CLAUDE.md only imports it

`AGENTS.md` holds pointers and the gist of each rule. `CLAUDE.md` contains one line, `@AGENTS.md`. Each rule's detail lives in its own file under `docs/agents/`.

## Why

Engineers bring different AI tools, and one file serves all of them. `AGENTS.md` is loaded every session, so it pays for its length every time. A leaf file is loaded only when needed.

## Consequences

- A rule is added as a leaf file and a pointer, never as prose in `AGENTS.md`.
- The `doc-structure` gate refuses a leaf file that `AGENTS.md` does not reach.
