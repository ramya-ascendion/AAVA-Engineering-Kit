# Issue types: the label is the fact, the type is how it reads at a glance

**A `wayfinder:*` label is what a ticket is. The issue type mirrors it so the
board can be read without reading.** Where the two disagree, the label is right
and the type is stale.

`tools/issue_types.yaml` holds the types and the label each one mirrors. This
file says why it is that way round, and what follows from it.

Whether your tracker has an issue-type field at all depends on `KIT_TRACKER`.
Jira has one, and so does a GitHub organization that has turned issue types on.
The `local` variant uses the `type:` line in the ticket file. Where there is no
type field, the label alone carries the fact and everything below about a lagging
type simply does not arise.

## Why the label owns the fact

A label costs nothing to create. Anyone can put a new one on a ticket the day
the need appears. An issue type is project configuration. It may need an
administrator, it arrives when it arrives, and work does not stop while it is
pending.

So the label leads and the type follows. A new kind of settling work gets its
label immediately and its type whenever the type is provisioned. Nothing is
blocked, and nothing is untyped in the meantime: the ticket is a **Task**, and
its label still says exactly what it is.

The type earns its place by being visible. It shows as an icon, so a person
scanning a board sees what each ticket is without reading a row. That is the
whole job, and it is worth having even though the label already carries the
fact.

## What follows from it

**Setting the type never removes the label.** The label is the record. The type
is the rendering of it.

**A query that must be correct filters on the label.** The type is allowed to
lag, so a filter on type alone silently misses any ticket whose type has not
caught up, and those tickets are Tasks, which most delivery queries include.
`/aes-work-the-path`'s frontier scan is the one that matters here: its type
list is a cheap first cut, and the label drop after it is what actually makes
the result right. See [`delivery-frontier.md`](delivery-frontier.md).

**No wayfinder ticket is a delivery type.** Settling work that is not a
grilling, a research or a prototype is **Planning**, not a **Task**, so the
`wayfinder:*` label and the delivery types never overlap. Each settling type is
defined by its *method*: Grilling by conversation with a person, Research by
primary sources, Prototype by a rough artifact, Planning by working a question
through. A type named only for an outcome (such as "Decision") describes every
wayfinder ticket, because every one produces a decision, so it fits none.

**One label has no type of its own: `wayfinder:map` on an Epic.** Epic is the
only type that can have children in most trackers, so a map has to be an Epic,
and `slice` is its opposite number. Where the tracker will not let you add
another parent-capable type, the overload is permanent. What makes a map
readable on the board instead is its title prefix, in
[`wayfinding-operations.md`](wayfinding-operations.md).

## Picking one

Pick the label first, from what the ticket produces. Then set the type that
mirrors it, if that type exists yet. `tools/issue_types.yaml` says when each
type is reached for and which label it mirrors, and it owns those values. Read
them there rather than from a copy here.

A ticket whose kind has a label but no type yet is a **Task** until the type
exists. That is the lag the label is there to cover.

Delivery work carries no `wayfinder:*` label at all, so there is no label to
lead and the type is picked straight from the registry.

## Keeping the two in step

**A tracker automation on label change is what should set the type.** Setting
the label is the one action that always happens, so hanging the type off it
makes the mirror the tracker's own job rather than a rule anybody has to
remember. Whether your tracker's automation can set an issue type needs
confirming before anyone counts on it.

Until one exists the mirror is a rule people and agents follow, and a drift
between the two is invisible: the repo's gates only ever see a staged file, and
both the label and the type live in the tracker. Which is the other reason the
label is the fact. It is the half that is always right.

## What this file does not decide

- **How a ticket moves once it exists.**
  [`ticket-states.md`](ticket-states.md), and
  [`epic-lifecycle.md`](epic-lifecycle.md) for an Epic.
- **What the turn labels mean.** [`triage-labels.md`](triage-labels.md).
- **How a wayfinding map and its tickets work.**
  [`wayfinding-operations.md`](wayfinding-operations.md).
