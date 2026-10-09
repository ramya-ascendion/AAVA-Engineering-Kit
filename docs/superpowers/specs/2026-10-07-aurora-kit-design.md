# Aurora Kit: design

Status: approved by Ramya on 2026-10-07 (with one amendment: carry the whole `vendor/` folder).

## Goal

One repo holding the SDLC and style conventions, skills, hooks and CI gates that
AES 2.0, AES 3.0 and Activations all reuse. The model is the Aurora project,
which Ramya liked. Only the engineering method is taken. Aurora's business
domain (its product, its customer, its ticket project and its decision records) is not.

Success: any of the three projects runs `bin/install-kit` and gets the rules,
skills, gates and an overlay, and a commit with a broken rule is refused.

## Layout

| Path | Holds |
| --- | --- |
| `AGENTS.md`, `CLAUDE.md` | The kit's own rules; `CLAUDE.md` only imports `AGENTS.md`. |
| `docs/agents/` | One rule per leaf file. Each answers one question. |
| `skills/own/` | Skills we wrote, named `aes-*`. |
| `vendor/mattpocock-skills/` | Borrowed skills, pristine, with LICENSE. Never edited. |
| `.git-hooks/`, `ci/` | The same gates in two places: pre-commit and GitHub Actions. |
| `tools/` | Scripts the gates call. |
| `templates/` | Document templates, one per document type. |
| `overlays/<project>/` | Per-project `AGENTS.md` fragment, `CONTEXT.md`, glossary seed, ADR-0001. |
| `bin/install-kit` | Installs core into a target repo, then applies one overlay. |

## Skill layout in a target repo

Real skills live once in `.agents/skills/`. Vendored ones live under `vendor/`.
`.claude/skills/` holds only links into `.agents/skills/`. On Windows the
installer tries a symlink, then a junction, then a copy, and says which it used.
A skill's `name:` equals its directory name.

## Hard rules and how each is enforced

| # | Rule | Enforcement |
| --- | --- | --- |
| 1 | No skipping gates; CI re-runs every gate | deterministic (hook + Action) |
| 2 | Every skill exists once; `name:` matches directory | deterministic (`skill-mirror`) |
| 3 | Every doc has a type, is reachable, every pointer lands | deterministic (`doc_structure`) |
| 4 | One owner per fact; ADRs immutable, superseded stay | hybrid |
| 5 | No secrets in commits | deterministic (gitleaks) |
| 6 | A new gate is shown red on a broken file before it merges | hybrid |
| 7 | Writing standard: answer first, short, plain words, American spelling | hybrid (`american-spelling`) |
| 8 | Search the whole codebase before claiming something is absent | inferred |
| 9 | Design lifecycle: wayfinder, spec, tickets, implement, diagram per phase | inferred |
| 10 | No work on shared main; branches and worktrees, `claude/<ticket>-slug` | hybrid |
| 11 | No invented facts; unverified claims are labeled | inferred |

## What is kept, rewritten, dropped

- Kept pristine: all of `vendor/mattpocock-skills/`.
- Kept and rewritten generic: the `aes-*` workflow skills, `docs/agents/`, templates.
- Dropped: the reference project's tooling-server skills, its editor-specific
  skills, its client skill, its ADRs and glossary, Aurora-only hooks and tools (client checks, design sync, record
  format, scenario ids, guarantee and CRAP scripts).
- Issue tracker is pluggable. Jira and GitHub Issues are documented variants.

## Not bundled

The superpowers, skill-creator, mempalace and context7 skills are not copied.
They have their own licenses and install as plugins. The README lists them as
recommended companions.

## Overlays

`aes-2.0`, `aes-3.0`, `activations`. Each is seeded only from facts already
recorded about the project. Anything not verified is marked `TODO: confirm`.
The three are parallel lines with their own bounded contexts, not one product.

## Verification

- Each deterministic gate has a test that breaks a file and sees the gate fail.
- `bin/install-kit` is run into a scratch directory for each overlay, then the
  target's own gates are run and must pass.
- Domain scan: `bin/check-no-leaks` finds none of the reference project's domain
  words or ticket keys anywhere in the kit.

## Not done here

No push. The repo is local on branch `feat/kit-v1`; Ramya pushes.
