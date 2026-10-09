# Aurora Kit

One baseline for how AES 2.0, AES 3.0 and the Activation Control Plane are
designed, built and gated. It carries the SDLC method and writing style, the
skills, the hooks, the CI gates and the document templates. It carries no
product knowledge.

## Guides

- [How to use the kit](docs/guides/how-to-use.md): install, daily flow, what the gates mean.
- [Runbook](docs/guides/runbook.md): install, upgrade, test, release, roll back, and a symptom-to-fix table.

## Install into a project

```bash
bin/install-kit <target-dir> <overlay> [--dry-run] [--force]
# overlays: aes-2.0, aes-3.0, activations
```

The installer never overwrites a file that already exists. It lists what it
skipped so a person can compare. Run it with `--dry-run` first.

Then, in the target:

1. Edit `.kit/config.env`. Items marked `TODO: confirm` are guesses, not decisions.
2. Run `bash setup-dev-env.sh` to point git at `.git-hooks/`.
3. Commit the installed files in one commit of their own.

## What is in it

| Path | Holds |
| --- | --- |
| `AGENTS.md`, `CLAUDE.md` | Writing standard, hard rules, pointers. |
| `docs/agents/` | One rule per file. Each answers one question. |
| `docs/agents/document-templates/` | Shapes for the document types. |
| `templates/adr-seeds/` | Baseline decision records every project starts with. |
| `.agents/skills/` | Our generic `aes-*` skills, and the borrowed ones (real copies of `vendor/`). |
| `.claude/skills/` | Links into `.agents/skills/`, for Claude Code. |
| `vendor/mattpocock-skills/` | Borrowed skills, pristine. |
| `.git-hooks/`, `ci/`, `tools/`, `tests/` | The gates, run as hooks and again in CI. |
| `overlays/` | Per-project config and `AGENTS.md` fragment. |
| `.kit/config.env.example` | Every per-project setting. |

## Hard rules

Twelve rules, each classified deterministic, hybrid or inferred. The table is in
`AGENTS.md`. Deterministic ones are scripts, so they cost no tokens and cannot be forgotten.

## Not bundled

These install as plugins and have their own licenses, so the kit does not copy
them. They are recommended companions: superpowers, skill-creator, mempalace,
context7, code-simplifier.

## Stacks

Secrets, doc-structure, skill-mirror and spelling gates run for every stack.
The Python gates (lint, type check, layering, coverage, CRAP) run only when
`KIT_STACK=python`. Node projects set `KIT_TEST_CMD`.

## Where it came from

See `PROVENANCE.md`. The design is `docs/superpowers/specs/`.
