---
name: aes-second-opinion-review
description: "Hand this session's review route to a second model, have it walk the route with /aes-work-the-review, and fix and resend until every pass passes."
disable-model-invocation: true
---

# A second model walks the review route

This skill takes the review route this session wrote for its pull request and
has a second model walk it. The reviewer follows `/aes-work-the-review`. Claude
fixes what fails and sends it back. The loop ends when every pass passes, or
after five rounds.

It does not merge, change ticket status, or post to the tracker without asking.

## The reviewer is a parameter

The reviewer CLI and the reviewer model are the user's choice, as set out in
`/aes-second-opinion-design`, "The reviewer is a parameter". Take them from
`AGENTS.md` or ask once per session. Neither is hardcoded here.

## No pull request (the local tracker)

When `KIT_TRACKER` is `local`, or the work sits on a branch with no PR, there is
no PR, no `gh` and no branch key to find. Replace the first two steps this way
and keep the rest:

- **Route.** If this session wrote no `# Your review route` block, build one
  from the commit range the ticket or branch names (`git log <base>..HEAD`):
  one pass per behaviour the tickets promise, each with the command that proves
  it. Say plainly in the report that the route was built from the range, not
  taken from an earlier session.
- **Ticket.** Read the ticket files under `.scratch/` that the range closes,
  not the tracker. The key is the `id:` in each file.
- **Reviewer access.** Run the reviewer read-only (see the flags below) and give
  it the commit range, not a PR number.

## Steps

1. Find the route, the pull request, and the ticket. Completion: all three are
   in hand, or the run has stopped and said what is missing.
2. Fetch the ticket. Completion: status and summary are in hand.
3. Send the route to the reviewer. Completion: the reviewer's report is saved to
   a file in the scratchpad.
4. Read the report. Completion: every pass has a result.
5. Fix and resend, or finish. Completion: every pass passed, or five rounds ran.
6. Report, then ask about the push and the tracker comment. Completion: the
   engineer has the last report and has said yes or no to each write.

## Find the route

The route is the last `# Your review route` block in **this** session. Look in
the conversation first. If it is not there, read this session's transcript
(Claude Code keeps one `.jsonl` per session under `~/.claude/projects/`, named
by `$CLAUDE_CODE_SESSION_ID`):

```bash
ls ~/.claude/projects/*/"$CLAUDE_CODE_SESSION_ID".jsonl
```

Take the last message holding that heading, and copy the route exactly. Do not
rebuild a route from the diff. If this session has no route, stop and ask the
engineer to paste one.

The pull request is the open one for the current branch
(`gh pr view --json number,url,headRefName`). The ticket key is the
`PROJ-NNN` in the branch name (`docs/agents/git-conventions.md`).

## Fetch the ticket

Fetch it by key (`docs/agents/issue-tracker.md`, the operation table for the
tracker `KIT_TRACKER` names). Claude does this, not the reviewer, because the
reviewer CLI may not have access to the tracker.

## Send the route to the reviewer

Pin the commit the reviewer walks to this checkout's `HEAD`, not the pull
request's head. A fix from an earlier round is then walked before anyone pushes
it.

Run from the repo root, in the background, because a walk can take longer than
a shell timeout. Save the output in the scratchpad. One example, for the Claude
CLI:

```bash
claude -p --permission-mode acceptEdits --allowedTools Bash --model opus "<prompt>" \
  > "<scratchpad>/review-round-N.md" 2>&1
```

`--permission-mode acceptEdits --allowedTools Bash` lets it run the route's commands and the break edit. That is for a route that must run commands. A review that only reads the code and the diff should use `--permission-mode plan` instead, which cannot edit or run anything.
If it prints an authentication error,
stop and ask the engineer to log in to the reviewer CLI.

The prompt says, in this order:

- Follow `.agents/skills/aes-work-the-review/SKILL.md` for `PROJ-NNN`.
  Other harnesses have no traced path to our skills
  (`docs/agents/skills-across-harnesses.md`), so name the file.
- The ticket's status and summary are given here. Do not fetch the ticket.
- The route is pasted below. Use it as written.
- Pin `<HEAD oid>`. This replaces the skill's pin rule for an open PR.
- Do not comment on the tracker. Return the report only.
- End with one line: `TOTAL passed=N failed=N partial=N skipped=N not-run=N`.
- The route, verbatim.

## Fix and resend

A pass counts only if it **passed**. Failed, partial, skipped, and not run all
send the loop around again.

For each pass that did not pass, read the reviewer's evidence and fix the cause
on this branch. Commit each fix with the ticket key, and let the hooks run. Then
send the same route again, pinned to the new `HEAD`.

**Never make a pass pass by editing the route.** A route that is itself wrong,
such as a stale test count, may be corrected, but name each change to the route
as a judgment call in the final report.

**Stop after five rounds**, even with passes still failing. Report what still
fails. This skill's loop replaces the review stopping rule for route passes,
because the engineer asked for every pass to pass. Anything the reviewer raises
that is outside a pass becomes a proposed ticket, not a fix.

After every round, check that `git worktree list` no longer shows the
reviewer's `review-PROJ-NNN` worktree. If one is left, name its path and stop.

## Report and ask

Show the last reviewer report in chat, then one line per round: which passes
failed and which commit fixed them.

Then ask, one at a time:

- Push the fix commits to the pull request?
- Post the last report as a comment on `PROJ-NNN`?

Both are writes other people see, so this skill asks every time.

## Where the rules live

What a route is: `.agents/skills/aes-work-the-path/review-route.md`. How a
route is walked: `.agents/skills/aes-work-the-review/SKILL.md`. This file
holds only the hand-off to the reviewer and the fix loop.
