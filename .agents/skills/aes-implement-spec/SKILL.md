---
name: aes-implement-spec
description: "Implement one Epic in parallel. Pass the Epic key, and optionally a fix version ceiling. The run shows who it would claim, waits for a go, then gives each ticket its own worktree, its own plan approval, and its own pull request."
disable-model-invocation: true
---

# Implement one Epic in parallel

Read the vendored `implement-spec` skill
(`vendor/mattpocock-skills/implement-spec/SKILL.md`). It holds the task graph
and the worktree per ticket. Follow this file for the run. The vendored steps
that open one integration branch, merge every ticket into it, and resolve the
tickets do not apply.

Upstream lands the whole spec on one integration branch and one pull request.
This run does not. One branch and one pull request per ticket.

`/aes-work-the-path` stays the serial loop. The bare `implement-spec` name is
not registered. It opens that one pull request and resolves tickets on its own,
which `docs/agents/ticket-states.md` does not allow.

The run never merges a pull request. It never creates a ticket. It never
closes a ticket to `Done` unasked. How a ticket moves stays in
`docs/agents/ticket-states.md`.

Every tracker operation below (fetch, claim, comment, move, label) is done the
way `docs/agents/issue-tracker.md` says for the tracker `KIT_TRACKER` names in
`.kit/config.env`. The default branch is `KIT_DEFAULT_BRANCH`; this file says
"the default branch".

## Arguments

- An Epic key, required (`PROJ-364`). An Epic is the spec. Without one, ask
  for it and stop.
- A fix version, optional, such as `v0.2`. It is a ceiling.

## Once per session

**Check the model once.** The check is step 1 of `/aes-implement`. Do not
ask again per ticket. Completion: the engineer has agreed the model, or the
session has stopped.

## Reconcile stacked pull requests

Do this before the scan. Those tickets are `In Review`, so the scan will not
see them.

Find open pull requests for this Epic whose base is another ticket's branch,
and whose blocker commits are already on the default branch. Replay only the
dependent commits onto a branch cut from the default branch. Retarget the pull
request to the default branch. Rerun the checks the replay touched. A replay
that does not apply cleanly is reported and left with the engineer.

Completion: every such pull request is retargeted, or named as the engineer's.

## In-flight scan

Run the in-flight scan in `/aes-work-the-path`, "Each iteration: scan,
pick, announce", restricted to children of this Epic. Its offers and its
one catch-up stay as that file writes them.

A review bounce stays in the claim-now set. It resumes its existing branch
and pull request. This run does not cut it a second branch.

Completion: every in-flight child is offered, caught up, left alone, or
marked as a review bounce.

## Build the set

Fetch the Epic's children with the same fields as the candidate query in
`/aes-work-the-path`, "Compute the frontier", restricted to this Epic. Keep
tickets an open blocker would have dropped. Build the blocks graph from that
response first.

Then split.

**Claim now.** A ticket the frontier would start. `ready-for-agent`, not
`In Review`, not `Blocked`, no `wayfinder:*` label, assignee empty or the
engineer, and every blocker `Done`. A review bounce is in this group and
keeps its branch.

**Claim later.** Inside the version ceiling, and every transitive
blocker is `Done` or selected in this run. At least one of those blockers is
not yet ready for its pull request question.

**Left out.** Name the ticket and the reason. A transitive blocker that is
not `Done` and not selected in this run. A newer version. A blocker outside the
Epic. Not ready. A wayfinder. Someone else's ticket.

**Version.** Compare the ticket's own fix version. The rules are in
`docs/agents/delivery-frontier.md`: numbers, one part at a time; none counts
as `v0.1`; several count as the earliest. An earlier blocker joins the set
only when it is inside the ceiling. A newer blocker stays out. The frontier's
inherited-version sort key is for ordering, and it does not add a ticket to
this set.

Show the three groups before any claim. The engineer may drop tickets. Each
drop redraws the list, including a dependent that lost its blocker.

Completion: the engineer has said go on a redraw, or the run has stopped with
nothing claimed.

On go, claim every claim-now ticket. Assignee is the engineer. `To Do` moves
to `In Progress`. A ticket already `In Progress` and already theirs is left
as it is. The go also covers the claim-later tickets. Nothing is claimed
before the go.

## Plans

The parent session is the only voice. Finish the open conversation before
starting another. Take claim-now tickets in the order
`frontier-ranking.md` sets.

Draw the plan. Send the plan to `/aes-second-opinion-design`. On a thumbs-up,
put it to the engineer. On approval, start that ticket's implementer, then plan
the next ticket.

A skipped plan unclaims the ticket, per `docs/agents/ticket-states.md`,
"Letting go of a ticket". A plan that turns out to span more than one ticket's
worth of work unclaims it and recommends a split. Do not create the tickets.

Any of those redraws the run. A dependent moves to left out, with the
reason, when one of its transitive blockers is no longer `Done` and no longer
in the run. That dependent is not claimed later.

Completion: the implementer has started, or the ticket is unclaimed and the
list is redrawn.

## Implementers

Each new ticket gets its own worktree and its own branch.
`docs/agents/git-conventions.md` names the branch. A commit from that
worktree runs the same gates as one from the main checkout
(`docs/agents/worktree-hooks.md`).

Cut the branch from the default branch. A dependent is cut from the
highest-ranked in-run blocker branch instead. Merge each other in-run blocker
branch in. Rank is `frontier-ranking.md`. A review bounce checks out the branch
it already has.

The implementer follows `/aes-implement` for the build. Skip that skill's
model check and its claim. Both are done.

Do not guess a question the plan left open. Commit as the work lands. An open
question does not stop the other tickets.

Before the implementer reports ready, it finishes the bars in
`quality-bars.md` and ticks the acceptance criteria.

The implementer does not ask the engineer. Completion: the parent has a
ready signal, or an open question.

## Open questions

An open question queues as a plan. Among plans, frontier order still applies.
The parent asks the engineer. Other tickets keep going.

If the answer changes the plan, `/aes-second-opinion-design` and the engineer
approve the revised plan before that implementer resumes. If the answer only
fills a hole the plan already named, the implementer resumes.

Completion: that ticket has resumed, or it has been unclaimed.

## Dependents

When every in-run blocker of a claim-later ticket is ready for its pull
request question, claim the ticket and queue its plan. There is no second go.

Two blockers in this run: cut from the one the frontier ranks higher, and
merge the other in.

Later commits on a blocker are merged into the dependent branch. The bars
on the old tree no longer apply, so code review and `quality-bars.md` run
again. If the pull request is already open, rewrite its review route from the
new diff before review continues.

Completion: the dependent's plan is queued, or it has moved to left out.

## The queue

Finish the conversation already open. Then a plan. An open question is a
plan. Then a pull request question. Then a review-walk question from
`/aes-second-opinion-review`: push its fixes, or comment on the ticket. Within
one kind, frontier order.

## The pull request

Ask the question in `/aes-work-the-path`, gate 1. The ticket stays
`In Progress` until the pull request exists.

On go, open the pull request, or push the existing one when this is a review
bounce. The base is the default branch, or the blocker branch when the ticket is
stacked. The title carries the ticket key (`docs/agents/git-conventions.md`).
Comment on the ticket with the link. Move the ticket to `In Review` and the
label to `ready-for-human`. Write the review route, per `review-route.md`. Then
`/aes-second-opinion-review` walks that route in the ticket's worktree. The
other tickets keep going.

Until the pull request is retargeted to the default branch, that walk fetches
and diffs against the pull request's actual base branch. `review-route.md` and
`/aes-work-the-review` otherwise use `origin/<default branch>`. After the
retarget, the fixed point is the default branch again.

On "not yet", follow `docs/agents/ticket-states.md`, "The flow", step 5.

Completion: the ticket is `In Review`, and the route walk is queued or done.

## The end

Stop when nothing left in the set can be planned or built. Name the open
pull requests, the tickets still blocked from outside the set, and any
stacked pull request still waiting on a squash. Do not wait for the squash.
The next run's reconciliation pass replays it.

## Where the rules live

This file is the parallel loop. The board is
`docs/agents/ticket-states.md`. The frontier order is `frontier-ranking.md`
beside `/aes-work-the-path`. The bars are `quality-bars.md` beside that
same skill.
