# Who moves the ticket, and what moves with it

The rules live in [`ticket-states.md`](ticket-states.md). This file is the
pictures.

Three parties touch a delivery ticket, and each can do things the others
cannot. The first picture is who does what. The second is what the ticket
itself looks like at each stop.

Every section here is about a **delivery ticket**: a Story, Task or Bug. An
Epic moves on different rules, and its own picture is in
[`epic-lifecycle.md`](epic-lifecycle.md). Check any new board rule against both
before applying it to the whole board.

| Party | What only they can do |
| --- | --- |
| Engineer | Starts the work, and unblocks it when the agent asks |
| Agent | Writes to the tracker: status, label, assignee |
| Reviewer | Approves a diff |

These are roles, not three people. The reviewer may well be the same engineer
who called `/aes-implement`. What matters is that the reviewing is a separate act
with its own steps, not who is sitting in the chair.

**Blocking is the exception, and it is one named role rather than any of the
three.** The lead is the only one who declares a ticket blocked, and owns
clearing it. The lead has no lane in section 1 because they appear nowhere on
the shipping path. Section 4 is that conversation.

## 1 · The three lanes

Time runs down the page. Which column a step sits in is who owns it, and every
arrow that crosses a column boundary is a handoff.

**Figure:** three lanes (engineer, agent, reviewer) with every step of a ticket
placed in its owner's lane. Source: [`ticket-lifecycle-lanes.mmd`](ticket-lifecycle-lanes.mmd).

Every box that changes something in the tracker belongs to the agent. The
engineer and the reviewer decide things; the agent is the only party that writes
status, label or assignee.

- **No automation runs behind any of this.** Engineers drive the board through
  an agent rather than by hand, so these rules are the whole enforcement. A step
  the agent skips is a step nobody performs, and nothing notices.
- **Five arrows leave the agent's lane, and each one is a question it must
  stop and ask.** An off-spec model, the plan (put up after claiming and
  before any code), the pull request (asked from `In Progress` before any PR
  exists), the review verdict, and the merge. None of the five is the agent's
  to answer, and nothing reaches `Done` on its own initiative.
- **The acceptance criteria are a gate, not a formality.** They get ticked off in
  the ticket, against work actually done, before the ticket leaves
  `In Progress`. An unchecked criterion is either not done or not verified.
  Both stop the ticket rather than shipping inside it.
- **`In Review` means the agent's work is done.** It lands when the PR opens,
  or when there's nothing to share at all: a ticket can sit `In Review` with
  no PR, and if the go on one never comes, a comment says it's withheld.
- **`/code-review` runs twice, on purpose.** The agent runs it inside
  `/aes-implement` before it will open a PR. The reviewer runs it again, by
  hand, on the PR, because calling it directly, as a fresh reader, reliably
  surfaces code smells the earlier run missed. The by-hand run is not
  optional, even when the reviewer is the engineer who ran the agent.
- **The dashed arrow is the ordinary path, not the error branch.** A review
  asking for changes hands the ticket back to the agent (status and label
  both), and the work comes back down through the criteria check on its way out
  again.

## 2 · What the ticket looks like at each stop

Two fields carry two different facts, and they are easy to confuse. The label
says whose turn is next. The assignee says who is holding it.

**Figure:** the four states of a ticket (To Do, In Progress, In Review, Done)
with the label and assignee at each, and Blocked off to one side. Source:
[`ticket-lifecycle-states.mmd`](ticket-lifecycle-states.mmd).

The label is not a record of how the ticket was written. It is a pointer at
whoever acts next, which is why it moves backwards as readily as forwards.

- **The label answers one question: whose turn is it next.** That single rule
  produces the whole sequence, the backwards step included. No separate rule
  was needed for the bounce back from review.
- **Done clears the label rather than setting a final one.** A finished ticket
  has no next action to point at, the same way `wontfix` takes a rejected one
  out of the machine instead of leaving a role behind.
- **Assignee is a different fact.** It says who is holding the ticket, not what
  state it is in. Handing a ticket to someone else is always allowed:
  reassign and carry on, and leave a handoff comment if real work was already
  done. What the assignee never does is go *empty* while the ticket is in
  flight. Clearing it is how you unclaim a ticket, which sends it back to
  `To Do` at the same time.
- **`Blocked` hangs off the path rather than sitting on it.** A ticket goes
  there when someone outside this team has to act: another team, a partner, a
  vendor. It carries `ready-for-human`, because the next move is a person's and
  not an agent's, and it comes back to the status the work is really in:
  `In Progress` when code is half written, `To Do` when nothing has started.
- **A ticket can go straight from `To Do` to `Blocked`.** When the outside
  dependency is known while the ticket is being written, it goes there the same
  day. Nobody has to try to start it first. That is the whole point: the sooner
  the block is on the board, the sooner someone can start asking.
- **A blocked ticket keeps its assignee, and it still means the builder.**
  Clearing the block is the lead's job, and that ownership lives in the blocked
  panel rather than in any field on the ticket. A ticket blocked before anyone
  claimed it has no assignee, which is correct. Nobody is building it yet.
- **Waiting on our own work is not `Blocked`.** That is an *is blocked by* link
  between two tickets here, and it changes no status. The rules for both are
  "Blocked: waiting on someone outside the team" in
  [`ticket-states.md`](ticket-states.md).
- **A ticket carrying a `wayfinder:*` label is not one of these.** It settles a
  question instead of shipping code, has no pull request, and finishes itself.
  Different lifecycle, same board.

## 3 · The two ways out that are not shipping

Most tickets ship. A claimed one can also be handed back or decided against,
and both are deliberate acts rather than just going quiet.

**Figure:** unclaiming a ticket versus closing it as wontfix, and why a handoff
is neither. Source: [`ticket-lifecycle-exits.mmd`](ticket-lifecycle-exits.mmd).

Unclaiming is not the same as abandoning, and closing is not the same as
failing. Each writes a specific pair of fields.

- **Unclaiming clears the assignee and returns the status to `To Do`** in one
  move. They go together, because an unassigned `To Do` ticket is exactly what
  "free to pick up" means. Close any open pull request when you do, and say so:
  an open PR against a ticket nobody owns is the trap the whole rule exists to
  avoid.
- **`wontfix` is the one `Done` that keeps its label.** Every other `Done`
  has the label removed because the change shipped and no turn is left.
  `wontfix` ends the turns too, but with nothing released, and the board still
  needs to know that, so the label stays and says it.
- **A handoff is neither of these.** Giving the ticket to another person is
  always allowed and changes nothing but the assignee. Leave a comment saying
  where things stand if real work was already done.
- **An unassigned ticket outside `To Do` is a loose end, not a free ticket.**
  Claiming it is the right repair, but look for commits or an open PR carrying
  its key first, and adopt that work instead of starting over.
- **Two ways out is the whole list.** Going quiet is not a third one. It is a
  condition that forces one of these two, or a return to moving. Section 5 is
  the picture of that. `Blocked` is not a third one either: a ticket parked
  there comes back, or it ends through one of these two.

## 4 · Declaring a ticket blocked

The lead is the only role that declares a ticket blocked, and from that moment
owns getting it unblocked. The engineer still makes the move on the board; what
they need first is the lead's agreement.

**Figure:** an engineer proposes a block to the lead naming the actor and the
action, and on proceed moves the ticket to Blocked, which puts it in the blocked
panel as the lead's to clear. Source:
[`ticket-blocked-declaration.mmd`](ticket-blocked-declaration.mmd).

The proposal is one sentence, and its shape is the gate: *I intend to move
PROJ-NNN to blocked because we need ACTOR to do ACTION before our team can work
on this.*

- **A block you cannot say that sentence about is usually not a block.** Naming
  the actor and the action is what separates a real outside dependency from work
  nobody has scoped, or a question the team could answer itself.
- **The lead's other answer is questions, and until they say proceed nothing
  moves.** That is the point of asking them rather than telling them.
- **The lead is a gate, not a queue.** The engineer makes the move themselves
  once the lead agrees, so nobody waits on the lead to have time to click a
  button.
- **The assignee does not change.** It still says who will build the ticket.
  The lead's ownership is not written into the ticket at all.
- **The blocked panel is the handoff.** A ticket landing there is what tells the
  lead the block is theirs, which is why nothing else has to be recorded to hand
  it over.
- **An agent never makes this move.** Every other status on this board is an
  agent's to write. This one is a decision about people outside the team, so an
  agent that thinks a ticket is blocked says so to the engineer and stops.

## 5 · Aging, then stale

Going quiet is not a third way out. It is a condition, and it is the one nobody
in the three lanes is watching for. Every in-flight ticket has an owner; nothing
guarantees the owner is moving it.

The rules are in [`ticket-stalled-clock.md`](ticket-stalled-clock.md):
thresholds, how the days are counted, and the exemptions. This is the shape of
them.

**Figure:** a claimed ticket picks up the aging label after three working days
without a status change and the stale label after seven, whether it is moving or
sitting in Blocked, and leaves both by moving again or by one of the two exits.
Source: [`ticket-lifecycle-aging.mmd`](ticket-lifecycle-aging.mmd).

- **Aging and stale are states on the normal path, not a side process.** A
  ticket does not leave the flow to be one of them. It picks up a label where
  it already sits, and carries on from there.
- **Every path leads out.** A ticket in either labeled state has to end up
  moving again or gone. The label is what makes someone decide which.
- **The two labels call on different people, and that is why there are two.**
  `aging` asks the assigned engineer for a plan. `stale` asks the team to look.
- **`Blocked` is a state on this picture, not an exemption from it.** A ticket
  waiting on another team or a partner company ages like any other, on the same
  3 and 7 working days. It leaves by the block being removed, or by aging.
- **Every blocked ticket is counted, owned or not.** The clock elsewhere runs
  only on claimed work, to keep the untouched backlog out of it. A blocked
  ticket is not backlog, and one blocked straight out of `To Do` has no assignee
  to filter on, so the filter does not apply here.
- **The label goes on where the ticket sits.** A blocked ticket that ages is
  still blocked. It keeps the status and picks up the label. Whatever surfaces
  the board shows it in the blocked panel with that mark on it, and does not
  move it into the aging and stale list. One ticket, one row.
- **Aging asks a blocked ticket for a different thing.** `aging` is the lead's
  cue to go back to the outside party, not the engineer's cue to re-plan the
  work. `stale` asks the team to escalate, or to accept that the wait is
  open-ended and take one of the two exits in section 3.
- **The counting is a thing your project builds.** Who stamps the labels and who
  clears them is in [`ticket-stalled-clock.md`](ticket-stalled-clock.md). Until a
  watcher exists this is a rule people follow, not a thing that happens.

## Editing the diagrams

Each diagram here is a Mermaid `.mmd` file, and it is the content record. Change
what a diagram says there first. Render a PNG from it with `mmdc`, using the
palette in [`mermaid-theme.json`](mermaid-theme.json):

```bash
mmdc -i docs/agents/ticket-lifecycle-aging.mmd \
     -o docs/agents/ticket-lifecycle-aging.png \
     -c docs/agents/mermaid-theme.json -b '#0F1622' -s 2
```

The `.mmd` is also what diffs, and what renders on a harness that reads Mermaid
natively. A diagram whose auto-layout comes out tangled may be hand-drawn as an
SVG under the rules in [`diagramming.md`](diagramming.md): hand-drawing
overrides the layout, never the content.
