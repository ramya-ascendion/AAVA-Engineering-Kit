---
name: aes-work-the-review
description: "Walk a ticket's review route, report each pass, and comment the result on the ticket. Pass a ticket key (`PROJ-286`), or a ticket key plus a pasted route."
disable-model-invocation: true
---

# Walk a review route

A **review route** is the numbered pass list `/aes-work-the-path` writes
after the PR opens. This skill walks that route. Nothing else.

It does not run `/code-review`, score acceptance criteria, change ticket
status, submit a review on the git host, merge, or switch the engineer's
checkout.

Arguments:

- a ticket key (`PROJ-286`): look the route up, then walk it.
- a ticket key plus a pasted route: use the pasted text. Do not look further.

A missing or malformed key stops the run and asks for one.

Every tracker operation (fetch, comment) is done the way
`docs/agents/issue-tracker.md` says for the tracker `KIT_TRACKER` names in
`.kit/config.env`. The default branch is `KIT_DEFAULT_BRANCH`; this file says
"the default branch".

## Steps

1. Fetch the ticket. Completion: status, summary, and key are in hand.
2. Resolve the route. Completion: the exact pass list is in hand, or the run
   has stopped and asked for a paste.
3. Pin a ref and add a worktree. Completion: commands run against that
   checkout, and the engineer's branch is untouched.
4. Walk every pass, in order. Completion: each pass has a result, or the
   route itself said to stop and later passes are recorded as not run.
5. Report in chat, then comment the same report on the ticket. Completion:
   the engineer can read it in both places.
6. Remove the worktree. Completion: `git worktree list` no longer names it,
   and the engineer's checkout matches the start of the run.

Do the cleanup after a failed pass too. A leftover worktree is not a report.

## Fetch the ticket

Fetch by key (`docs/agents/issue-tracker.md`, "When a skill says fetch the
relevant ticket"). Read status, summary, and comments. The comments are not a
route source; they are context for the report header.

## Resolve the route

**Pasted text wins.** If the invocation included a route, that is the route.

Otherwise look it up. Do not invent one. Do not rebuild one from the diff.

**Local tracker or no git host** (`KIT_TRACKER` is `local`, or there is no PR
and no `gh`). Skip the `gh` lookups below. The route is pasted text, or a route
file the invocation names, or one the engineer built from a commit range. Pin the
checkout to the range's last commit. Ticket state comes from the ticket file
under `.scratch/`, never from a host.

**Ticket is `Done`.** Find that ticket's last merged pull request:

```bash
gh pr list --search "PROJ-NNN" --state merged --limit 20 \
  --json number,title,mergedAt,mergeCommit
```

Keep rows whose title carries the key. Sort by `mergedAt`, take the latest.
Then search Claude Code sessions for a review route that names that PR.

**No merged PR yet.** Search Claude Code sessions for the ticket key. Take
the last review route in the newest matching session.

Claude Code transcripts for this repo live under `~/.claude/projects/`.
Encode `git rev-parse --show-toplevel` by turning each path separator into `-`
(so `/home/me/dev/project` becomes `-home-me-dev-project`). Search that
directory's `*.jsonl` files, not `subagents/`. The heading to find is
`# Your review route`. When one session holds more than one route, the last
one wins.

**If the lookup finds nothing, stop.** Name what was searched: ticket status,
last PR (or that none merged), and the session path. Ask the engineer to
paste the route. Do not continue.

A `Done` ticket with no merged PR stops the same way: there is no ref to pin.

## Pin a ref and add a worktree

Capture this checkout first: `git rev-parse --show-toplevel`,
`git branch --show-current`, `git status --porcelain`. That is the engineer's
tree. Do not `checkout` it.

Pin:

- **`Done`**: the last merged PR's merge commit (`mergeCommit.oid`).
- **Open PR**: that PR's head (`gh pr view N --json headRefOid`).
- **No PR**: the one local branch whose name carries the ticket key. None,
  or more than one, stops and says so.

Fetch the oid if it is not local, and always fetch the default branch, so
`origin/<default branch>` is current before any route command diffs against it.
Then:

```bash
git fetch origin <default branch>
git worktree add --detach "$(git rev-parse --git-dir)/review-PROJ-NNN" <oid>
```

If that path still exists from a crashed run, `git worktree remove --force`
it first.

A `Done` merge commit is an ancestor of today's default branch, so a diff
against the default branch at that commit is empty. Rewrite every
`<default branch>...HEAD` (and `origin/<default branch>...HEAD`) in the route to
the merge's first parent:

```bash
git diff <oid>^1 <oid>
```

On an open PR the worktree's `HEAD` is the change, so
`origin/<default branch>...HEAD` is the PR, because the pin step fetched the
default branch. Rewrite a bare `<default branch>...HEAD` to it: the local branch
may be stale, and then the diff holds everything merged since it was last pulled.

Run every route command from the worktree, using this checkout's virtualenv
(`KIT_VENV_DIR`).

## Walk the passes

Follow the route's own stop line. If a pass says the picture is wrong, stop
here: later passes are only asking whether the code matches it. Stop, and
record the rest as not run.

Otherwise finish every pass. For each one:

1. Run the command it gives, from the worktree.
2. Answer the question it asks, from what that command showed.
3. Record **passed**, **failed**, **partial**, or **skipped**, with evidence.

### Break it

A **break** is the named edit the route says should turn tests red.

At the start of that pass, `git status --porcelain` in the worktree. If it is
dirty, skip the pass and say so. Do not edit.

If it is clean: make the named change, run the tests the route says should go
red, restore those files, confirm the worktree is clean, then record whether
the predicted tests went red.

Restore even when the tests fail. A break that outlives the pass is a defect
in this run, not a finding about the ticket.

## Report

In chat first, then the same body as a ticket comment. Do not change status.
Confirm the comment by reading the ticket, not by re-running a search
(`aes-work-the-path`, "Verify a tracker write by reading the fields").

```markdown
# Review route — PROJ-NNN: [title]

Pinned: `<oid>` (PR #N at <url>, merged or open)
Route from: pasted | Claude Code session `<file>` (last `# Your review route`)

## Pass 1 · [title from the route]
**Result:** passed | failed | partial | skipped
**Evidence:** (command, output, what was read)
**Issues / suggestions:** (or none)

## Pass 2 · …
```

End with a one-line total: how many passed, failed, partial, skipped, and
not run. The engineer decides whether to bounce or approve.

## Cleanup

```bash
git worktree remove --force "$(git rev-parse --git-dir)/review-PROJ-NNN"
```

If a break would not restore, stop and leave the worktree. Name its path.
Force-removing a dirty break hides the edit on the engineer's disk.

Then check the engineer's checkout: same branch, same `git status
--porcelain` as at the start.

## Where the rules live

What a review route is, and the shape of its passes, live in
`.agents/skills/aes-work-the-path/review-route.md`. How to fetch a ticket
lives in `docs/agents/issue-tracker.md`. How a PR names a
ticket lives in `docs/agents/git-conventions.md`. This file holds only the
walk.

This skill lives once, in `.agents/skills/`; `.claude/skills/` holds a
symlink to it. Edit the one file. The `skill-mirror` pre-commit gate
refuses a second copy.
