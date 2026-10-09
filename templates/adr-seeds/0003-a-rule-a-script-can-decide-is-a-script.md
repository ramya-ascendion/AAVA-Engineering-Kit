---
status: accepted (baseline)
---

# A rule a script can decide is a script, and it runs in two places

Before a rule is written it is classified: deterministic, hybrid or inferred. A deterministic rule becomes a gate. A gate runs as a pre-commit hook and again as a CI action.

## Why

Prose costs tokens every time an agent loads it. A gate costs none and never forgets. `--no-verify` skips every hook, so a hook alone is a reminder, not a gate.

## Consequences

- A new gate is shown failing on a deliberately broken file before it merges.
- A gate is also shown failing when it is handed nothing, such as an empty file list or an unresolved base commit.
- See `docs/agents/writing-a-rule.md`.
