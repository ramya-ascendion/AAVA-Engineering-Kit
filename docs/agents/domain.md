# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists — it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. In multi-context repos, also check `<package>/<context>/docs/adr/` for context-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/aes-grill-with-docs` and `/aes-improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

A **single-context** repo has one `GLOSSARY.md` and one `docs/adr/` at the root. This is an example layout:

```
/
├── GLOSSARY.md
├── docs/adr/
│   ├── 0001-use-a-relational-store-for-orders.md
│   └── 0002-payments-go-through-the-gateway-service.md
└── src/
```

If the project later splits into genuinely separate packages, switch to the multi-context layout: a root `GLOSSARY-MAP.md` pointing at per-context `<package>/<context>/GLOSSARY.md` files, with system-wide decisions staying in the root `docs/adr/` and context-specific ones in `<package>/<context>/docs/adr/`.

## ADR format

This repo layers extra rules on the vendored skill's base ADR format: an
`amended-by` frontmatter field, four writing-style rules, and rules for
restyling existing ADRs. See [`adr-format.md`](adr-format.md). Read it before
writing or editing any ADR.

## Use the glossary's vocabulary

When your output names a domain concept (in a ticket title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
