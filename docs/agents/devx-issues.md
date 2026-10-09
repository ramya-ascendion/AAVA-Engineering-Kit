# Developer experience work: its own label or project, off the delivery board

**Developer experience and engineering standards work is filed under its own
label or project, never on the delivery board.** Delivery work, the behavior a
user gets, is described by [`issue-tracker.md`](issue-tracker.md) and moves
through [`ticket-states.md`](ticket-states.md). That file is unchanged by this
one. This file covers the other lane and says which work goes there.

Keeping the lanes apart matters for a mechanical reason as well as a tidy one.
The delivery frontier ([`delivery-frontier.md`](delivery-frontier.md)) picks the
next `ready-for-agent` ticket on the delivery board. Tooling work mixed in would
be picked as product work, and product work in the tooling lane would never be
picked at all.

## Where it goes

Choose the lane once per project and write it in `AGENTS.md`.

| `KIT_TRACKER` | The tooling lane |
| --- | --- |
| `github` | Issues in the same repo carrying the label `devx`, optionally added to a GitHub Project of their own. Delivery scans exclude the label. |
| `jira` | A separate Jira project, or at minimum the label `devx` with delivery queries excluding it. A GitHub Issue in the repo also works when the engineers live in GitHub. |
| `local` | The folder `.scratch/devx/`, apart from the delivery tickets. |

Type: **Task**. Set it explicitly rather than relying on the default.

## What belongs here

Work on the tools the team builds with, rather than on the product the team
ships. The test is whether a customer would ever notice it. If only an engineer
or an agent would, it is tooling work.

- The agent skills under `.agents/skills/`, and the conventions in `AGENTS.md`
  and `docs/agents/`.
- The git hooks, the gates they run, and CI checks.
- Repo tooling under `tools/`, and the scripts the gates call.
- Naming, layout, and anything about how the repo is organized.

Anything that changes what the product does for a user is a delivery ticket,
even when the change is small and even when it is mostly configuration.

## Filing one in GitHub

```bash
gh issue create --label devx --title "<imperative phrase>" --body-file <path>
```

Add `--project "<project name>"` to put it on a board.

Write the title as an imperative phrase saying what the fix does, matching the
issues already filed, such as "Catch duplicate ADR numbers before they reach the
default branch". Write the body to a file first rather than passing it inline,
so the prose can be read before it is published.

**`--project` needs a `gh` token carrying the `project` scope, which is not one
of the defaults.** Without it the command can create the issue, then fail on the
project step, so the issue lands orphaned off the board. Grant the scope once
per machine before filing anything:

```bash
gh auth refresh -s project
```

`read:project` is not enough. Adding an item to a board is a write.

The body follows the repo's writing standard in `AGENTS.md`: the problem first,
the evidence for it, then a section saying what closes it. A tooling ticket is a
standing reference like any other committed document, so it gets full sentences.

**Ask the engineer before creating one.** Filing an issue publishes it to a
shared repo, so the body is shown to a person first and the command runs after
they agree.

## Referencing one from git

The subject line of a commit belongs to the delivery ticket key when there is
one, because that is where a connector looks ([`git-conventions.md`](git-conventions.md)).
A tooling issue reference goes in the body instead.

- Write `Refs: #123` on its own line in the commit body.
- Never put a bare `#123` in the subject line. A squash merge appends the pull
  request number in that position already.
- Close the issue from the pull request body with `Closes #123`, not from a
  commit message. Only the pull request form lists the pull request as linked
  on the issue.

## A commit with no delivery ticket key

A tooling change often has no delivery ticket at all. [`git-conventions.md`](git-conventions.md),
"When there is no ticket", already allows a branch without a key for work that
genuinely has none. The tooling issue is that work's identifier: put `Refs: #123`
in the body, and let the subject carry the change itself.

## What this file does not decide

- **The delivery lifecycle, the frontier, and the triage labels.**
  [`issue-tracker.md`](issue-tracker.md) and [`triage-labels.md`](triage-labels.md).
- **Branch, commit, and pull request naming.**
  [`git-conventions.md`](git-conventions.md).
- **What the hooks run and when.** [`worktree-hooks.md`](worktree-hooks.md).
