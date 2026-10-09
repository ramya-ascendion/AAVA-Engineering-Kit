# Aurora Kit

The method, skills and gates this project builds with. Settings that differ per
project live in `.kit/config.env`. The kit holds no product knowledge: the
project's own `CONTEXT.md` and ADRs say what the product is.

## Writing standard

Every prose document is written for an engineer joining the team. They know
software. They do not know this domain yet. What kinds of document exist, and
what each is for, is `tools/document_types.yaml`.

- Say the decision or answer first. Backstory after.
- Short sentences. One idea each.
- Plain everyday words: "slow", not "suboptimal".
- Name real things: "the retry loop", not "the resilience layer".
- Define a technical term once, in a few words, at first use.
- Bullets when listing more than two things. Never nest them.
- No self-congratulation. A record does not grade itself.
- Spelling follows `KIT_SPELLING_LOCALE`. Quoted outside material, names other
  people own, and vendored text keep their original spelling.

### Be concise where text leaves the repo

Text that leaves the repo is read once and thrown away: a ticket, a pull request
comment, a chat reply, a handoff. Fragments are fine there. Text committed to
the repo is standing reference and stays in short full sentences, because a
newcomer reads it cold with no chat history.

### One owner per fact

Every fact lives in exactly one place:

- An ADR decides it. Settled, binding.
- `GLOSSARY.md` or `CONTEXT.md` defines it. A term, or a fact about the domain.
- A design note holds a possibility still being explored. When its question is
  settled it is deleted, because the ADR now owns the fact.
- The ticket gets a one-line gist and a link to whichever of the above holds
  the detail.

A value defined in code is owned by the code. Name the constant and link the
module; do not copy what it holds. Before committing, check every file you
touched for the same fact restated elsewhere.

## Hard rules

Each rule is classified before it is written. A rule a script can decide is a
script. See `docs/agents/writing-a-rule.md`.

| # | Rule | How it is enforced |
| --- | --- | --- |
| 1 | Hooks are never skipped. CI re-runs every gate, because `--no-verify` skips every hook. | deterministic: hook and Action |
| 2 | Every skill lives once. `name:` matches its directory. Vendored skills are never edited. | deterministic: `skill-mirror` |
| 3 | Every document has a type, is reachable from this file, and every pointer lands. | deterministic: `doc-structure` |
| 4 | No secret enters a commit. | deterministic: `gitleaks` |
| 5 | A gate that did not run says NOT RUN. A missing tool is FAILED, never passed. | deterministic: hooks |
| 6 | A new gate is shown failing on a broken file, and on empty input, before it merges. | hybrid: review |
| 7 | One owner per fact. An ADR is never edited to change its decision; a new ADR amends it. | hybrid: review |
| 8 | Writing standard above, and the spelling locale. | hybrid: `american-spelling` |
| 9 | Search the whole codebase for the fact, not the tool name, before saying something is absent. | inferred |
| 10 | Design before tickets, tickets before code, a diagram at each phase. | inferred |
| 11 | No work on the shared default branch. Branches and worktrees only. | deterministic: `protected-branch` |
| 12 | No invented facts. An unverified claim is labeled unverified. | inferred |

## Agent skills

### Design lifecycle

The phases before a ticket exists: wayfinding, spec, tickets. A diagram at each
phase is strongly encouraged. See `docs/agents/design-lifecycle.md`,
`docs/agents/wayfinding-operations.md` and `docs/agents/slices.md`.

### Issue tracker and ticket rules

Where tickets live is chosen by `KIT_TRACKER`: `github`, `jira` or `local`.
`docs/agents/issue-tracker.md` is the way in, with a table of which file answers
which question. The ticket rules:

- `docs/agents/ticket-states.md`: how a ticket moves, Blocked, definition of done.
- `docs/agents/ticket-lifecycle.md`: the same flow as pictures.
- `docs/agents/ticket-stalled-clock.md`: when a claimed ticket is stalled or stale.
- `docs/agents/ticket-links.md`: Blocks, Related, Duplicate, and the link pass.
- `docs/agents/epic-lifecycle.md`: an Epic's status is a statement about its children.
- `docs/agents/delivery-frontier.md`: which ticket is free to start.
- `docs/agents/triage-labels.md` and `docs/agents/issue-types.md`: the five
  triage roles, and why the label owns the fact.
- `docs/agents/devx-issues.md`: tooling work stays off the delivery board.

### Git conventions and worktrees

Branches, commits and pull request titles carry the ticket key, written
`claude/PROJ-123-short-slug` for agent branches. See
`docs/agents/git-conventions.md`.

**A commit or push from a worktree runs the same gates as one from the main
checkout.** See `docs/agents/worktree-hooks.md`.

### Writing rules, documents and decisions

- `docs/agents/writing-a-rule.md`: classify a rule before writing it.
- `docs/agents/document-types.md`: every document belongs to a type.
- `docs/agents/adr-format.md`: decision record rules.
- `docs/agents/domain.md`: what to read before exploring, and how to flag an ADR conflict.
- `docs/agents/diagramming.md`: six notations, written as Mermaid, committed as `.mmd`.
- `docs/agents/before-saying-the-system-cannot-do-that.md`: widen the search first.

### Quality bars

- `docs/agents/coverage-and-crap.md`: line coverage and CRAP bars, from `.kit/config.env`.
- `docs/agents/guarantees.md`: optional. Prove a stated guarantee by removing the line that keeps it.

### Skills

Our skills are named with the `KIT_SKILL_PREFIX` prefix, so a reader can tell
ours from a borrowed one by name alone. Borrowed skills live pristine under
`vendor/`. See `docs/agents/skill-overrides.md` for the wrap-never-edit rule and
the update recipe, and `docs/agents/skills-across-harnesses.md` for what each
tool can reach.

## Harness setup

This file is the one place project conventions live, so engineers can bring
their own AI tool.

- Claude Code reads it through `CLAUDE.md`, which imports it with `@AGENTS.md`.
- Codex and Cursor read `AGENTS.md` directly.
- Every skill has one source: ours in `.agents/skills/`, borrowed ones pristine
  under `vendor/`. `KIT_SKILL_LAYOUT` says how the other places get it. In the
  `copy` layout (the default) `.agents/skills/` and `.claude/skills/` hold real
  files, `bin/sync-skills` regenerates them, and the gate proves they are
  byte-identical to the source. In the `link` layout they are links. Never edit
  a copy by hand, because two copies that differ is the failure this prevents.
- The `skill-mirror` gate checks this on any commit that touches either skills
  directory or the vendored tree.
- Only the Claude Code path has been traced end to end. What Codex and Cursor
  can reach is untested.
