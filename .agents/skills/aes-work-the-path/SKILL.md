---
name: aes-work-the-path
description: "Work the delivery critical path ticket by ticket. Picks the next unblocked ready-for-agent ticket that is the engineer's or unowned, checks it has a story diagram, drives it with /aes-implement, holds it to the coverage and CRAP bars, stops to ask before opening the pull request, hands the engineer an ordered route through the review they now owe, then asks again before starting the next ticket. Pass `report` to print the pick and every planned write without writing anything, or a ticket key to start there instead of the frontier's top pick."
disable-model-invocation: true
---

# Work the delivery critical path

One interactive session, one ticket at a time, in this repo. The board is the
coordination mechanism, so no worktrees and no parallel branches. The
previous ticket sits `In Review` while the next one is worked.

Every tracker operation below (search, fetch, claim, comment, move, label) is
done the way `docs/agents/issue-tracker.md` says for the tracker `KIT_TRACKER`
names in `.kit/config.env`. Where this file shows a query, it shows the Jira
form; `docs/agents/delivery-frontier.md` gives the `github` and `local`
equivalents. The default branch is `KIT_DEFAULT_BRANCH`; this file says "the
default branch".

This skill always stops for three questions:

- **"Does this plan look right?"** Asked after the ticket is claimed and
  before any code is written, in plan mode. The plan's diagrams are shown
  first, and agreed, before the plan itself goes up.
- **"Create the pull request?"** Asked while the ticket is still
  `In Progress`, before any PR exists. Once the PR opens, the ticket moves
  to `In Review` (`ticket-states.md`, "The flow", step 5).
- **"Continue to the next ticket?"** Asked after the PR opens, and after
  the engineer has been handed the route through the review they now owe.

Two more questions are possible but not routine, both from the coverage and
CRAP bars: an offer to exempt a function that cannot get under the bar, and a
stop after three laps of fixing that have not settled it. Neither is asked on a
clean run. Nothing else stops.

Three things it never does: merge a pull request, touch a ticket assigned to
anyone but the engineer running it, or close a ticket out to `Done` unasked.

Arguments:

- none: loop from the frontier's top pick.
- `report`: dry run. Print the frontier, the pick, and every write that would
  happen, then stop **before** claiming anything, so it never reaches the plan
  gate and never enters plan mode. Write nothing. Every ticket named in a report
  is written `PROJ-146: [title]`: the key, a colon, then the summary, never a
  bare key and never a key on its own line.
- a ticket key (`PROJ-146`): start at that ticket instead of the frontier's
  top pick, after checking it passes the same ownership and unblocked rules.
  If it fails them, say why and stop rather than working it anyway.

## Once per session

**Check what you are running.** The same check `/aes-implement` makes: the
model and reasoning effort the project has chosen for implementation, and ask if
on anything else. Asking here satisfies that check for every iteration. Do not
re-ask per ticket.

**Start clean.** On the default branch, working tree clean, `git pull
--ff-only`. A dirty tree stops the session with a question, never a silent
stash.

**Cache the build order.** Fetch the slices once (in Jira, `project = PROJ AND
issuetype = Epic AND labels = "slice"` with `fields: ["summary", "issuelinks"]`)
and order them by their Blocks links. This is the build order as it lives on the
board, used only for tie-breaking.

## Each iteration: scan, pick, announce

**Scan first, then pick, then announce both.** The scan offers rather than
acts, the pick comes off the delivery frontier, and the announcement names the
top three before the one being taken.

Follow `docs/agents/delivery-frontier.md`, "The delivery frontier". The steps
below are how to find those tickets, and what else the scan owes the engineer
on the way past.

**Scan first.** Offers, never actions, except one catch-up named below.

Search the in-flight tickets once: in Jira, `project = PROJ AND issuetype in
(Story, Task, Bug) AND status in ("In Progress", "In Review", "Blocked") AND
(assignee = currentUser() OR assignee IS EMPTY)` with `fields: ["summary",
"status", "assignee", "labels"]`. Then sort each one by what git and GitHub say
about it: `gh pr list --state merged --limit 20 --json number,title`,
`gh pr list --state open --json number,title,headRefName`, and
`git log --oneline origin/<default branch> --grep=PROJ-NNN`.

**`In Review` and `In Progress` both hide situations the scan has to tell
apart, and each needs a different response:**

- **Its work is merged.** Commits carrying the key are on the default branch,
  or a merged PR names it. The close-out never happened. Offer to finish it:
  `Done`, label removed, a what-shipped comment linking the merged PR, per
  `ticket-states.md`. Never do it unasked.
- **It has an open PR and the ticket has caught up** (`In Review`
  + `ready-for-human`). Genuinely awaiting a human. Report it as in flight
  and leave it completely alone. No offer. There is nothing to fix.
- **It has an open PR and the ticket hasn't caught up.** Still
  `In Progress`, or still `ready-for-agent`. This state has two different
  causes, and only one of them is this scan's to fix. A review on the git host
  is not a reliable signal here. This project's review happens by running
  `/code-review` and deciding in chat (`ticket-states.md`, "The flow", step
  6), which need never leave a review on the PR itself. Check the ticket's
  own status history, and ask whether it has ever reached `In Review`
  before. If it has, this is a review bounce still waiting on the agent. It
  went `In Review → In Progress` at least once already. Leave it. The
  frontier already picks it up as ordinary `ready-for-agent` work, and it
  moves to `In Review` again once the fix is pushed, not before. If it has
  not, this is its first time in this state, so the PR opened and nothing
  since caught the board up. This is the one action the scan takes. Move it
  to `In Review` and swap the label to `ready-for-human`.
- **It has no PR at all.** The withheld-PR case from gate 1. Offer to reopen
  that gate and open the PR now.

**A `Blocked` ticket is reported, never acted on.** Someone outside the team has
to move first, so there is no offer to make. Say it is blocked, say how long it
has sat, and go on to the frontier. Clearing it is the lead's, and the blocked
panel already tells them.

**Never move a ticket into `Blocked`.** The lead is the only role that declares
one, and the engineer makes the move once the lead agrees. If a ticket looks
blocked, a plan that dead-ends on another team or a dependency nobody here can
satisfy, say so to the engineer, name the actor and the action, and stop. See
"The lead declares a ticket blocked" in `ticket-states.md`.

**Adoptable loose ends.** Any of the above that is unassigned is also a loose
end. Offer adoption: claim it, review the branch, finish it, take over its PR,
instead of the frontier pick. This is `ticket-states.md`'s own "Picking up a
ticket that is not in `To Do`" rule. Cite it, don't restate it.

Fold every offer into the pick announcement so the engineer reads one message,
not five interruptions.

**Compute the frontier.** The steps start here and finish in
`frontier-ranking.md`.

1. Candidates: the query in `delivery-frontier.md`, with the fields `summary`,
   `status`, `assignee`, `labels`, `issuelinks`, `parent`, `fixVersions` and a
   limit of 50. **Drop anything carrying a `wayfinder:*` label.** The type list
   is a cheap first cut and not enough on its own. A settling type can lag
   behind the label that owns the fact, and a ticket whose type has not caught
   up is still a Task.
   **`In Review` is excluded whatever its label says.** The next action there
   is a human's, and the catch-up scans above are what handle it.
   Without this, a ticket left `In Review` + `ready-for-agent` by label drift
   ranks as implementable when its code already shipped. **`Blocked` has to be
   named too.** In some trackers its status category is the same as `To Do`,
   so a plain "not Done" filter passes it straight through, and nobody here can
   move it.

   The links field makes this response large enough to spill to a file in some
   tools. That is the good case: read it back with `jq` rather than pulling it
   inline.
2. Drop the blocked: any candidate holding an inward *is blocked by* link at
   a ticket that is not `Done`. `In Review` is not `Done`. A blocker awaiting
   review still blocks.

### Rank what is left, then announce

`frontier-ranking.md` beside this file holds the leverage count, the fix
version, the merged-commits flag, the pick order and the look-ahead. A run handed
an explicit ticket key stops here. It has its pick already, and nothing in that
file would change it. A `report` run reads it and stops at the end of it.

## Narrate every state change

The engineer is watching a stream of work, not a black box. Updates are short
and decision-first (`AGENTS.md`, writing standard). Required:

- the look-ahead after each frontier computation: "The next three tickets on
  the path are PROJ-146, PROJ-147, PROJ-151, top of the critical path, all
  ready to implement. Starting with PROJ-146, which unblocks four others."
- the claim: "PROJ-146 claimed, To Do → In Progress."
- entering the plan gate: "Planning PROJ-146 before writing anything."
- the plan's diagrams, before the plan itself: the rendered images, what each
  one claims, and anything drawing them made you notice
- the plan's outcome: approved and starting, revising, or skipped and
  unclaimed with the next pick named
- anything found mid-implementation that changes the approach
- the suite green and `/code-review` clean
- both measurements, pass or fail: the coverage percent and the worst CRAP
  score, each in plain words
- the start of each extra lap of review, coverage and CRAP, and what forced it
- the move to `In Review` / `ready-for-human`
- after a go: "PROJ-146 pushed as PR #24, now In Review."
- the review route itself, once the PR is open. It is the handover, not a
  status line, and it is the longest thing this skill writes
- after a yes at gate 2: "Starting PROJ-147, next on the path."

Silence between milestones is fine. A state change without an update is not.

## Claim it

Assignee = the engineer running this session, `To Do → In Progress`, before
any work, planning included. Skip idempotently when the ticket is already
theirs and `In Progress`; a review bounce re-enters here.

Claiming comes before the plan gate, not after. The rule is that claiming
happens before any work so two sessions never take the same ticket, and
planning is work that takes a while. That window is exactly what claiming
closes. The skip path in the next section is what makes an early claim safe to
reverse.

## Ticket readiness: the story diagram

Before planning, check whether the picked ticket links a Story-level diagram
(`docs/agents/design-lifecycle.md`, the `/to-tickets` phase's diagram row).
Some tickets predate that file and never got one. This check is also the
backfill for them, applied lazily, the moment work actually starts, rather than
as a separate migration pass over the backlog.

- **Missing, and a diagram would clarify something.** Build one now, via
  `/artifact-diagramming` where the harness has it: published as an Artifact,
  plus the usual committed `.mmd` (and `.png`) per `docs/agents/diagramming.md`,
  linked from the ticket. Then continue to the plan gate.
- **Missing, but nothing here has a shape worth drawing.** Say so in the
  pick announcement and move on. This is encouragement, not a gate
  (`design-lifecycle.md`): a ticket never stops here the way it stops on an
  unchecked acceptance criterion.
- **Already linked.** Continue straight to the plan gate.

## Draw the plan before you write it

This is the plan gate's first beat, not a gate of its own. It happens inside
plan mode, and the section below is the rest of it.

**The plan gets diagrams, and they are shown first.** Draw how the build will
work, put the pictures in front of the engineer, and only then call
`ExitPlanMode`. A plan read cold as prose hides a wrong shape; a picture of the
wrong shape is obvious in ten seconds, and it is far cheaper to find it here
than in the review.

This is not the Story diagram from the section above. That one belongs to the
ticket and says what the behavior is. These belong to the plan and say how the
build goes together, so a ticket that already has a Story diagram still gets
them.

**Always draw at least one UML sequence diagram.** These tickets are almost
always about a thing that happens in an order (a message arriving, a wait
ending, a worker dying and coming back), and order is what a sequence diagram
carries and prose does not. Add a UML state diagram when the thing being built
can be in more than one state, which is most waits and most loops.

The notations, the palette and the rendering command are
`docs/agents/diagramming.md`, and nothing here overrides it. In particular:
Mermaid, the `.mmd` committed beside the `.png`, and the in-scope and gap colors
the project chose.

Draw as many as the build has shapes, and no more. One is fine when the ticket
has one shape. Never pad.

Then put them to the engineer on their own, before the plan:

- Send the rendered images, and say in a line or two what each one claims.
- Name anything the pictures made you notice: a field that does not exist yet,
  a seam that turned out to be wiring rather than building.
- Ask whether to go to the plan, or fix a picture first.

**A correction here changes the plan, not just the drawing.** If the engineer
says the shape is wrong, redraw and ask again. The plan is built on whatever
picture they agreed to.

## Gate 0: the plan

**Call `EnterPlanMode`.** Read the ticket properly first: its description,
acceptance criteria, links and comments. Then design how to build it. When the
plan is ready, send it to `/aes-second-opinion-design` and carry on only after
its thumbs-up.

**This gate has two beats, and the diagrams are the first.** Draw the build and
put the pictures up, per the section above; once the engineer has them, call
`ExitPlanMode`, which is what puts the plan itself to them. Both beats happen
inside plan mode, and they are one gate rather than two. The pictures and the
plan are the same proposal, shown in the order that finds a wrong shape
soonest.

**The acceptance criteria are the *what*; the plan is the *how*.** These
tickets arrive specified (an agent brief is a contract, not a sketch), so a
plan that restates the criteria has said nothing. Name the seams, the files,
the tests that go first, and any choice the ticket left open.

Three ways this resolves:

- **Approved.** Implement. Do not ask again.
- **Revise.** The ticket stays claimed and `In Progress`, because it is still
  yours and still in flight. Rework the plan and put it up again. Nothing on
  the board moves.
- **Skip this ticket.** Unclaim it, per `ticket-states.md`, "Letting go of a
  ticket": clear the assignee, status back to `To Do`, label back to
  `ready-for-agent`, in one move. Then take the next frontier candidate and
  keep going. A declined plan ends the ticket, not the session. Leaving it
  claimed and `In Progress` after deciding against it is the loose end that
  rule exists to prevent.

## Drive the ticket with /aes-implement, two changes

Run `/aes-implement` on the pick, with these deliberate overrides:

1. **Skip its model check and its claim.** Both are done: the model once at
   session start, the claim above.
2. **At "Before the pull request":** tick the acceptance criteria as it says,
   then run the checks in the next section. They come before the ask, not
   after it. Then report and ask. The ticket stays `In Progress` until the PR exists
   (`ticket-states.md`, "The flow", steps 4 and 5). At "Opening it" on a go: open
   the PR, comment on the ticket linking it, move the ticket to `In Review`
   and the label to `ready-for-human`, and stop there.

## Three more checks, before the gate

`/aes-implement` has finished and the pull request has not been asked for
yet.

`quality-bars.md` beside this file holds which checks run, the order they run
in, what each one reads, and the two ways this ends early.

## Gate 1: the pull request

Ask, with the report: "PROJ-146: [title] is done on `claude/PROJ-146-slug`.
Full suite green, `/code-review` clean, acceptance criteria ticked. The tests
run 94 out of every 100 lines, and the worst CRAP score is 25. Create the pull
request?"

- **Go.** Push the branch and open the PR: key in the title
  (`git-conventions.md`), base the default branch. Comment on the ticket linking
  it. Move the ticket to `In Review` and the label to `ready-for-human`, because
  the next action is the engineer's review. Run `/code-review` directly against
  the default branch yourself first, same as always, before handing it over. Then
  write the review route, per "Hand over the review" below.
- **Not yet.** Push the branch anyway; work must not live only on this
  machine, and the ticket should link it. Comment on the ticket:
  work complete on the branch, pull request withheld pending a human
  decision. Move the ticket to `In Review` / `ready-for-human`. Nothing is
  left for the agent, so the next action really is a person's, per
  `ticket-states.md`, "The flow", step 5. The loop ends with a session
  summary.
- **No, with instructions.** The pre-PR bounce. Move the ticket back to
  `In Progress` and the label back to `ready-for-agent`, rework, and come
  back through the suite, `/code-review`, the criteria, and this gate.

## Hand over the review, before gate 2

The PR is open and the next action is the engineer's. **Write them the review
they are about to do**, in the same message or the one straight after.

`review-route.md` beside this file holds what a route is: the passes, their
order, and the five things every route carries.

## Gate 2: continue

After the PR opens and the review route is handed over: "PR #24 is open and
PROJ-146 is In Review. Continue to the next ticket on the path?"

- **Yes.** `git checkout <default branch> && git pull --ff-only`, then a fresh
  iteration: both scans, frontier recomputed from the live board. A ticket
  bounced back from review re-enters as a first-tier pick on its own, with no
  special case needed.
- **No.** Session summary: tickets advanced, PRs opened, offers still
  pending. End.

## Verify a tracker write by reading the fields, not by re-running the search

A tracker's search index can lag behind a write by seconds. A count run straight
after a label swap may still report the old value, while a direct read of the
fields on those same tickets is correct immediately.

So confirm a write by fetching the tickets by key and reading the fields you
changed. Never conclude from a stale count that a write failed and try it again.

## Endings and edges

- **Empty frontier.** Say why: how many candidates existed, how many dropped
  as blocked and behind which keys, and whether the dam is someone else's
  open ticket. Then end.
- **A HITL-shaped pick.** A ticket labeled `ready-for-agent` whose body
  turns out to need hardware, credentials, or a decision the agent cannot
  drive: say so, offer the label it should carry (`needs-info` or
  `ready-for-human`), and take the next frontier candidate this iteration.
  Never relabel unasked.
- **Someone else's work.** Excluded twice over: the ownership clause drops
  their tickets, and the blocked filter drops everything behind their open
  work. Stated here so nobody adds a third rule.
- **The pre-push hook** may run slow or live suites when the project wired them
  in; a switched-off dependency never blocks a push. Expect either.
- **Merging.** Never. The decision is the human's, made fresh each time.

## Where the rules live

The law is in the conventions, not here: `docs/agents/delivery-frontier.md`
(which ticket is free to start), `docs/agents/ticket-states.md` (how a delivery
ticket moves), `docs/agents/issue-types.md` (which type a ticket gets),
`docs/agents/triage-labels.md` (whose turn is next),
`docs/agents/git-conventions.md` (branch, commit and PR naming),
`docs/agents/design-lifecycle.md` (the story diagram),
`docs/agents/diagramming.md` (the six notations, the palette, the rendering),
`docs/agents/coverage-and-crap.md` (the two bars and how they are measured),
`docs/agents/guarantees.md` (the optional guarantee check and its results).
This file holds only the loop.

Three of its steps are their own file beside this one, each read only when that
step is reached:

- `frontier-ranking.md`: how the frontier is ranked, and the look-ahead.
- `quality-bars.md`: what must be green before the pull request gate.
- `review-route.md`: the review handed over once the pull request is open.

This skill lives once, in `.agents/skills/`; `.claude/skills/` holds a
symlink to it. Edit the one file. The `skill-mirror` pre-commit gate refuses
a second copy.
