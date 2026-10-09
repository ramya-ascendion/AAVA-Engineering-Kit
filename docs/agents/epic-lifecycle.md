# An Epic does not move like a delivery ticket

**An Epic's status is a statement about its children, not about anybody's work.**
Nobody claims an Epic and nobody codes one, so the delivery-ticket rules in
[`ticket-states.md`](ticket-states.md) do not apply to it. Check any new board
rule against both files before applying it to the whole board.

**Figure:** an Epic leaves To Do when its first child goes In Progress and
reaches In Review when its last child is Done, and nothing yet defines how it
reaches Done, because every move an Epic makes is driven by a child rather than
by anyone claiming the Epic. Source:
[`epic-lifecycle-states.mmd`](epic-lifecycle-states.mmd).

Every transition is driven by a child. The gap-colored state is the one with no
way in: **nothing defines how an Epic reaches `Done`**, because that needs a QA
and acceptance process this kit does not prescribe. Add it here once your team
has designed one.

- **A child moving is what moves the Epic.** `To Do` to `In Progress` when the
  **first child goes `In Progress`**. `In Progress` to `In Review` when the
  **last child reaches `Done`**. Nobody moves an Epic directly.
- **An Epic with no children cannot start,** which follows from the first rule
  rather than being a rule of its own: with no children, no child can go
  `In Progress`. `To Do` is the correct state, however long it sits there.
  Children merely existing does not start an Epic either; one of them has to
  move.
- **It stays `In Progress` for as long as its delivery tickets are active.**
  Weeks is normal and is the Epic working. Children starting and finishing
  underneath it is not a status change of its own.
- **`In Review` is where an Epic parks, and `Done` has no defined path.** Every
  child being finished is not the same as the slice being accepted. Until
  acceptance is designed, an Epic in `In Review` stays there, and that is
  correct, not stuck. How an Epic reaches `Done` is a question to revisit, not
  an oversight to repair.
- **The signal for an Epic is its children, not its own clock.** Time since the
  last status change says nothing about an Epic. If every child of an
  `In Progress` Epic is sitting still, the children are the problem to show, not
  the parent.
- **An Epic never goes `Blocked`.** The blocked child carries the block, and the
  Epic goes on reporting what its children are doing.

## Two delivery-ticket rules that break on an Epic

Both name Epics out loud rather than leaving it to be worked out.

- **The stalled-ticket watcher skips Epics.** Counting days on an Epic would
  flag a healthy slice as `stale`, and would still say nothing when a real one
  stalls. It would also never clear, because a finished slice parks in
  `In Review` and stops changing status. See
  [`ticket-stalled-clock.md`](ticket-stalled-clock.md).
- **An Epic with no assignee outside `To Do` is correct.** Assigning a slice
  Epic to one engineer would claim one person owns the whole slice, which is
  not what the board means. So the rule in
  [`ticket-states.md`](ticket-states.md) about claiming an unassigned ticket
  outside `To Do` does not reach an Epic.

## Editing the diagram

`epic-lifecycle-states.mmd` is the source. Re-render a PNG from it after
editing:

```bash
mmdc -i docs/agents/epic-lifecycle-states.mmd \
     -o docs/agents/epic-lifecycle-states.png \
     -c docs/agents/mermaid-theme.json -b '#0F1622' -s 2
```

## What this file does not decide

- **How a delivery ticket moves.** [`ticket-states.md`](ticket-states.md).
- **How an Epic's description is written.** [`slices.md`](slices.md).
- **The pictures for a delivery ticket.**
  [`ticket-lifecycle.md`](ticket-lifecycle.md).
