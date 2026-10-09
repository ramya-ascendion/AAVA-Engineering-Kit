# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Apply the mapped role as a label in whichever tracker `KIT_TRACKER` names
(`issue-tracker.md` says how to set a label in each). In the `local` variant the
label goes in the ticket file's `labels:` list. If a legacy `.scratch/` tree
still holds `Status:` lines from before the tracker was chosen, preserve them as
history and do not use that convention for new work.

A ticket carries exactly one **turn** label at a time, and it moves as the
ticket does. The turn label always answers one question: **whose turn is it
next?**

- `ready-for-agent` → `ready-for-human` when the pull request opens. The
  agent's work is done and the next action is a person's review
  (`ticket-states.md`, "The flow", step 5).
- `ready-for-human` → `ready-for-agent` when that review asks for changes. The
  turn goes back to the agent, so the label does too.
- `ready-for-human` for as long as the ticket sits in the `Blocked` status.
  Someone outside this team has to act, so the next turn is a person's and not
  an agent's. When the block clears, the label goes back to whatever the
  resumed status calls for. See "Blocked: waiting on someone outside the team"
  in `ticket-states.md`.
- `ready-for-agent` again, with the assignee cleared, when a ticket is
  unclaimed and goes back to the pool of free work.
- Label removed entirely once the ticket reaches `Done` by shipping. The
  change is out, so there is no next turn to name.
- **`wontfix` is the one label that survives `Done`.** It answers the turn
  question the same way shipping does (nobody's turn is next) and adds the
  part shipping does not need to say: the ticket ended without a change being
  released. That is why it stays on the board. Reaching `Done` with no label
  means it shipped; reaching `Done` with `wontfix` means it was decided
  against.

## Labels on other axes

A turn label is not the only label a ticket can carry. Several labels answer a
different question, so a ticket carries one *alongside* its turn label rather
than instead of it. A ticket that carries `ready-for-agent` and `slice` together
is correct.

**A `wayfinder:*` label is the fact, and the issue type mirrors it.** A type
shows an icon in trackers that have one, so a person scanning the board reads it
without reading a word. But a label costs nothing to create and a type is
project configuration that can lag, so the label leads and the type follows.
Setting the type never removes the label. See [`issue-types.md`](issue-types.md).

| Label | The question it answers | Who it calls on |
| --- | --- | --- |
| `aging` | Has this ticket stopped moving? | The assigned engineer |
| `stale` | Has it stopped for much longer than that? | The whole team |
| `slice` | Is this Epic a slice? | Nobody. It is a fact. |
| `wayfinder:map` | Is this Epic a map rather than a slice? | Nobody. It is a fact. |
| `wayfinder:planning` | Is this ticket settling scope, sequence or structure? | Nobody. It is a fact. |

`aging` and `stale` say nothing about whose turn is next, so they never replace
a turn label. Neither is a mark against the engineer either. Both say what the
ticket is.

A ticket in the `Blocked` status carries them the same way. It keeps the status
and picks up the label where it sits, and whatever surfaces the board shows it
in the blocked panel with the mark on it rather than moving it to the aging and
stale list.

Work on the tools the team builds with is not on this board at all. It goes to
its own label or project, so no delivery label marks it. See
[`devx-issues.md`](devx-issues.md).

**No agent sets either by hand.** The two thresholds, how the days are counted,
who stamps the labels, who clears them and what each one asks for are all in
[`ticket-stalled-clock.md`](ticket-stalled-clock.md). That file is the one to
edit; this table is the index.

See [`ticket-states.md`](ticket-states.md) for the full flow, including the
two ways out that are not shipping. Assignee is a separate signal. It says
who is holding the ticket, not what state it is in.

Edit the right-hand column of the first table to match whatever vocabulary you
actually use.
