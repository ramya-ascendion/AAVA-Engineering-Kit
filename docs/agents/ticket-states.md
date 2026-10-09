# Ticket lifecycle: Story, Task, Bug

How a delivery ticket moves from `To Do` to `Done`, who moves it, and the two
ways out that are not shipping. The pictures for this are
[`ticket-lifecycle.md`](ticket-lifecycle.md).

**An Epic does not move like this.** Its status is a statement about its
children rather than about anybody's work, and two of the rules below break on
it. See [`epic-lifecycle.md`](epic-lifecycle.md).

**A ticket carrying a `wayfinder:*` label is not one of these.** It settles a
question instead of shipping code, has no pull request, and finishes itself. See
[`wayfinding-operations.md`](wayfinding-operations.md).

The workflow is flat: **To Do → In Progress → In Review → Done**, with
**Blocked** off to one side. Any status can move to any other status directly.
There is no gate to fight and no screen to fill in along the way. These five
names are the same in every tracker variant; [`issue-tracker.md`](issue-tracker.md)
says how each variant spells them.

`Blocked` is not a step in that sequence. It is where a ticket parks when
someone outside this team has to act before anyone here can move it. See
"Blocked: waiting on someone outside the team" below.

**Every status change and every claim goes through an agent.** Engineers here
drive the board with `/aes-implement` and the other skills rather than by hand,
so these rules are the enforcement. No tracker automation sits behind them, and
nothing catches a step an agent skips. Write them into the skill, not just into
this file. `/aes-work-the-path` chains `/aes-implement` along the delivery
frontier (see [`delivery-frontier.md`](delivery-frontier.md)), one ticket at a
time, stopping at each pull request.

# The flow

1. **The engineer calls `/aes-implement`** on a ticket.
2. **The agent checks what it is running** before anything else: the model and
   reasoning effort the project has chosen for implementation, recorded in
   `AGENTS.md` (by default the fast-model tier of
   [`design-lifecycle.md`](design-lifecycle.md), "Model tiers", at medium
   reasoning effort). Anything else (a smaller model, a
   different effort level) and it says so and asks the engineer to confirm
   before implementing. This is a question asked once at the start, not a
   silent downgrade discovered in the diff.
3. **The agent reads the ticket, claims it, and moves it to `In Progress`.**
   Claiming means assigning the ticket to the engineer who called
   `/aes-implement`, the same rule "Claiming a ticket" uses for wayfinder
   tickets. It happens before any work, so two sessions never take the same
   ticket.

   **Then it plans, and the plan is approved before any code is written.** The
   acceptance criteria say what to build; the plan says how, and the engineer
   signs it off first. A revised plan changes nothing on the board, because the
   ticket is claimed and in flight either way. A plan the engineer declines
   outright means letting the ticket go: unclaim it, per "Letting go of a
   ticket" below, rather than leaving it claimed and `In Progress` with nobody
   working it.
4. **The agent implements, finishes, and asks about a pull request.** Two
   things must be true before anything moves:
   - The full test suite is green and `/code-review` ran clean.
   - **The ticket's acceptance criteria have been reviewed and checked off**
     in the ticket description, each one confirmed against the work that was
     actually done, not assumed. An unchecked criterion is either not done or
     not verified, and both stop the ticket here.

   When both hold, the agent reports and asks about the pull request. It
   never opens one unprompted. The ticket stays `In Progress` until the PR
   exists.
5. **On "go", the agent opens the pull request**, its title carrying the
   ticket key ([`git-conventions.md`](git-conventions.md)), and comments on the
   ticket linking it. The open PR moves the ticket to `In Review` and swaps the
   triage label from `ready-for-agent` to `ready-for-human`
   ([`triage-labels.md`](triage-labels.md)).

   On "not yet", no PR opens. Nothing is left for the agent, so the ticket
   still moves to `In Review` / `ready-for-human`, with a comment saying the
   PR is withheld pending a human decision. The board still tells the truth,
   because the agent's work is done.
   **With no pull request at all** (a local tracker, or work kept on one
   branch), `In Review` means the same thing: the agent's work is done and a
   person has to look. Move the ticket when its last commit lands, name the
   commit range in a comment, and let the reviewer walk that range.
6. **A person reviews the code**, once the ticket is `In Review`. The agent
   wrote the code, so the engineer who ran it may be that reviewer and may
   approve the PR themselves. Run `/code-review` on the pull request by hand.
   It already ran once inside `/aes-implement`, but calling it directly,
   as a fresh reader, reliably surfaces code smells the earlier run missed,
   so the extra minute is worth it. Two rules make it count.
   **Its fixed point is the branch the PR merges into, usually the default
   branch** (`KIT_DEFAULT_BRANCH`), not the last commit anyone reviewed. And
   **review the diff on its own terms**: do not go looking for an earlier run's
   report, and do not treat silence as a pass. A run that reads the earlier ones
   is not a fresh read. Then, two ways out:
   - **Changes requested.** The ticket goes back to `In Progress` and the label
     back to `ready-for-agent`, because the next action is agent work again.
     Step 4's checks repeat, acceptance criteria included, and the existing PR
     gets new commits, not a fresh one.
   - **Approved.** The human either merges the PR themselves or asks the
     agent to merge it. Either is fine; the decision to merge is always the
     human's, made fresh each time. An agent does not merge on its own
     initiative, no matter how clean the diff or how long it has sat.
7. **An approved, merged PR takes the ticket to `Done`**, with the triage
   label removed. The change is out, so there is no next turn to name
   ([`triage-labels.md`](triage-labels.md)). Leave a comment saying what shipped,
   linking the merged PR.

If an agent notices a PR merged without it being asked to close the ticket out
(while checking status, picking up other work, whatever the reason), say so
and offer to finish step 7. Don't do it unasked, and don't stay quiet about it
either.

# Letting go of a ticket

Shipping is not the only way out. A claimed ticket has two other endings, and
both are deliberate acts. Neither is "stop touching it and move on".

To **unclaim** a ticket is to give it back to the pool of free work, the exact
inverse of claiming it. It has nothing to do with a release: a release is a
version that ships to production (see "Slices" in [`slices.md`](slices.md)).

- **Unclaim it.** The work is still worth doing, just not by you now. Clear the
  assignee, move it back to `To Do`, and set the label back to
  `ready-for-agent`. That returns it to the pool of free work, which is exactly
  what an unassigned `To Do` ticket means. If a pull request is already open,
  say so in a comment and close the PR. An open PR against a ticket nobody
  owns is the trap this whole section exists to avoid.
- **Decide not to do it.** The work should not happen. Move the ticket to
  `Done` and apply `wontfix`, with a comment saying why. This is the one `Done`
  that keeps a label: `wontfix` records the reason it closed, which is
  something the board still needs to know ([`triage-labels.md`](triage-labels.md)).

**Handing a ticket to someone else is always allowed.** Reassign it and carry
on. The ticket keeps its status and its label, because the work has not
changed hands in the sense the lifecycle cares about, only the person. If real
work was already done, leave a handoff comment saying where things stand, so
the next person is not reading a diff cold.

# Blocked: waiting on someone outside the team

`Blocked` says one thing: **nobody here can move this ticket, and the person
who can is not on this team.** Another team has to grant access, a partner has
to ship a fix, a vendor has to answer a question. The status exists so
that waiting on the outside looks like what it is, instead of looking like work
we are not doing.

**A ticket waiting on our own work is not `Blocked`.** That is what the Blocks
link is for. That ticket keeps whatever status it has, holds an inward *is
blocked by* link at the ticket it waits on, and drops off the frontier through
the link rule in [`delivery-frontier.md`](delivery-frontier.md). Needing a
peer's help is not `Blocked` either. That is a ticket that has stopped moving,
and [`ticket-stalled-clock.md`](ticket-stalled-clock.md) is the rule for it.

The two kinds of blocked answer different questions, and one ticket can be both
at once:

| | What it means | Where it shows |
| --- | --- | --- |
| The `Blocked` status | Someone outside the team must act | The ticket's status, and the blocked panel |
| An *is blocked by* link | Another ticket here must finish first | The tracker's own screens, and the critical path |

# The lead declares a ticket blocked

**One role says a ticket is blocked: the lead, meaning the person the team
names as owning unblocking (the ticket's owner when the team names nobody).**
That person owns getting it unblocked from that point on, so the call to enter
the status is theirs. An engineer who thinks a ticket is blocked takes it to the
lead first.

The conversation is short and has a shape:

```
Engineer: I intend to move PROJ-NNN to blocked because we need ACTOR to do
          ACTION before our team can work on this.
Lead:     Proceed.
```

- **Name the actor and the action.** Not "we are waiting on the vendor" but
  who, and what they have to do. A block you cannot say that sentence about is
  usually not a block. It is work nobody has scoped yet, or a question we could
  answer ourselves.
- **The lead's other answer is questions.** Some of what feels blocked turns out
  to be reachable from inside the team, and the questions are what find that
  out. Until the lead says proceed, the ticket does not move.
- **The engineer makes the move themselves once the lead agrees.** This is a
  buy-in gate, not a queue. Nobody waits for the lead to have time to click the
  button.
- **An agent never moves a ticket to `Blocked`.** If it looks blocked, the agent
  says so to the engineer and stops there. Every other status on this board is
  an agent's to write; this one is not, because the declaration is a decision
  about people outside the team, not about the state of the code.

**The lead's ownership does not show up in the assignee field.** It shows up in
the blocked panel, which is the list of what the lead owns for as long as those
tickets sit there. Nothing else has to be written down to hand over a blocked
ticket.

# What moves with the status

Four things go with it:

- **The assignee stays the engineer who will build it.** Blocking is not
  unclaiming, and it is not a handoff to the lead either. The field goes on
  saying the same thing it always says: who is holding the ticket. A ticket
  blocked before anyone claimed it has no assignee yet, which is correct. See
  "A ticket can be born blocked" below.
- **The turn label becomes `ready-for-human`.** The next action is a person's,
  and it is not an agent's.
- **A comment says who we are waiting on, what was asked, and when it was
  asked.** Without it the board records that we are stuck and nothing else, and
  the first question anyone asks (who owes us this) takes a person half an
  hour to reconstruct.
- **Coming back, the ticket returns to the status the work is really in.**
  `In Progress` if code is half written, `To Do` if nothing has started, with
  the turn label set to match. `Blocked` keeps no memory of where the ticket
  came from.

**Leaving does not need a declaration.** Entering `Blocked` is the lead's call
because it commits them to the chase. Leaving only records that the outside
party delivered, so whoever learns that (the lead or the engineer) moves the
ticket back. An agent can say a blocked ticket looks unblocked. It still does
not make the move.

Three rules the status does not change:

- **The clock keeps running.** A blocked ticket ages and goes stale like any
  other. [`ticket-stalled-clock.md`](ticket-stalled-clock.md) is that rule.
- **`Blocked` is not a third way out.** A ticket cannot end there. It comes
  back, or it takes one of the two exits above.
- **An Epic never goes `Blocked`.** An Epic's status is a statement about its
  children, so the blocked child carries the block and the Epic goes on
  reporting what its children are doing. See [`epic-lifecycle.md`](epic-lifecycle.md).

**No agent picks up a `Blocked` ticket**, and one query trap makes that worth
spelling out. In some trackers `Blocked` sits in the same status category as
`To Do` (Jira does this), so a filter like "category is not Done" does not
exclude it. Any query that means "work an agent could start" has to name the
status itself.

# A ticket can be born blocked

**`To Do` to `Blocked` is a normal move, not a repair.** When the outside
dependency is known while the ticket is being written (a partner has to
confirm an API, another team has to open a port), put the ticket in `Blocked`
then and there. Nothing has to be attempted first.

The point is time. A block found on the day the ticket is written can be raised
that day, and the answer may take weeks to come back. Leaving the ticket in
`To Do` until an agent tries to start it burns the whole gap, and the board
spends that time claiming the work is ready to pick up.

- **It still goes through the lead.** Born blocked or blocked mid-flight, the
  declaration is the same conversation and the same sentence.
- **It does not need an assignee to sit in `Blocked`.** Nobody has claimed the
  work, and putting a name on it would say someone is building a ticket nobody
  can start. The chase is the lead's either way, and the panel is what tells
  them.
- **The clock still runs on it**, which is why the assignee filter does not
  apply to `Blocked`. See "Which tickets the clock runs on" in
  [`ticket-stalled-clock.md`](ticket-stalled-clock.md). A ticket blocked
  straight out of `To Do` has no assignee to filter on, and it is exactly the
  one that would otherwise sit unseen.
- **It goes back to `To Do` when the block clears**, still unassigned and
  `ready-for-agent`, which puts it in the pool of free work exactly as it was.

# Picking up a ticket that is not in `To Do`

An unassigned ticket outside `To Do` is a loose end, and claiming it is the
repair rather than a violation. Set the assignee and carry on.

**An Epic is the exception, and it is not a loose end.** Assigning a slice Epic
to one engineer would claim one person owns the whole slice, which is not what
the board means, so an Epic with no assignee outside `To Do` is correct. See
[`epic-lifecycle.md`](epic-lifecycle.md).

**A `Blocked` ticket with no assignee is not a loose end at all.** A ticket goes
to `Blocked` straight from `To Do` when the outside dependency is known up
front, so there is no half-finished work to adopt and no branch to find.
Clearing the block is the lead's, not the assignee's. Claiming one only says you
will build it when it comes back, and there is no hurry to do that while
nobody can start.

**But look before you implement.** A ticket sitting in `In Progress` or
`In Review` with no owner may already have work behind it: commits on a branch
carrying its key, or an open pull request ([`git-conventions.md`](git-conventions.md)
explains how to find them). If there is, adopt that work (review it, finish it,
take over its PR) rather than starting again and producing a second
implementation of the same ticket.

# Definition of done

A Story, Task, or Bug is done when all of these are true:

- Every acceptance criterion in the ticket description is checked off.
- The full test suite is green and `/code-review` ran clean.
- The pull request was approved and merged to the default branch, with the
  ticket key preserved in the merge commit ([`git-conventions.md`](git-conventions.md)).
- The ticket is transitioned to `Done`, with its triage label removed.
- A comment on the ticket says what shipped, linking the merged PR.

A ticket closed as `wontfix` is not "done" in this sense, because nothing
shipped. It is closed, and the label says why.
