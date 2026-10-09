# Slices

What a slice is, how its Epic is written, and what the Epic holds that a Story
does not. Which slice is free to start is
[`delivery-frontier.md`](delivery-frontier.md).

A **slice** is a thin cut through the whole system, touching every layer at once
while finishing none of them. It is the unit the build order is written in. A
slice is not a capability and it is not a theme. One slice touches several
capability groups, and one capability group is touched by several slices. The
two are different axes, not two words for one idea.

- **A slice is an Epic carrying the label `slice`.** Epic is the only type that
  can have children in most trackers, so a slice owns its delivery tickets
  directly. The label tells a slice apart from a capability group and from a
  `wayfinder:map`, the same way the map label already works.
- **The reasoning for a slice's position goes in its description.** Why this slice
  is third, and what it waits on, belongs on the slice itself. An order that lives
  only in a decision record is invisible to anyone reading the board.
- **Order the slices with the native Blocks link**, so the sequence shows on
  the tracker's own screens without opening anything.

Three fields carry three different facts about a delivery ticket, and they do not
overlap:

| Field | Answers |
| --- | --- |
| Fix version | Which release it ships in, written `v<major>.<minor>`. The lower version ships first, so its work is built first. |
| Parent | Which slice it ships in. |
| Related link | Which capability it serves. |

The parent slot is free for this because implementation tickets cannot be
children of a capability when capabilities sit at the same hierarchy level as
Stories; they point at their capability with a Related link instead. See
[`ticket-links.md`](ticket-links.md), "Parents". In the `local` and `github`
variants the fix version is the `fix-version:` field or a `v<major>.<minor>`
milestone, and the parent is the `parent:` field or line
([`issue-tracker.md`](issue-tracker.md)).

**A slice is not a fix version.** A fix version names a release, and a release
has one date. Putting nine slices in that field would list nine build
steps and one real release together as though they were the same kind of thing.

**A slice Epic is not a child of the wayfinder map.** Epics do not nest, and it
would be wrong if they did. The map holds decisions, and slices are what the map
hands off once those decisions are made.

# How a slice Epic is written

A slice has more to say than an Epic field should hold, so it says it in two
places. This is the one-owner rule from `AGENTS.md` applied as written: the repo
file owns the detail, and the tracker gets a gist and a link.

| Document | Holds | Length |
| --- | --- | --- |
| The Epic description, in the tracker | Six short sections, every one scannable, and a link to the spec at the top. | About 350 words. |
| The spec, in `specifications/` or `docs/specs/` | The problem statement, the user stories, the implementation decisions, the test seams, what is out of scope and why, and the warnings. | As long as it needs. |

The spec is named for its slice: `specifications/08-order-tracking.md`. It is
committed, reviewed and gated like any other prose in this repo. A spec written
into an Epic field instead is a standing reference nobody can grep, review or
read cold.

**The Epic's summary carries a two-digit number.** `08 — Order Tracking`. The
number is how the board and any viewer show priority, and two digits keep the
sort right past nine. **The number stays on the board and never enters repo
prose.** Prose that names a slice names its ticket key or the thing itself, so
that renumbering the board costs nothing.

The Epic's six sections, in this order:

1. **Summary.** What the product can do once this slice is finished. Plain
   language. No ADR numbers, no ticket keys, no module names.
2. **Why now.** What this slice unblocks, and what it costs to leave undone. Two
   or three bullets. This is the sequencing argument.
3. **Definition of done.** The bar for the whole slice.
4. **Scope boundaries.** What is in, what is out, and which slice owns what is
   out.
5. **Implementation.** The decisions that bind the work, each named as its ADR,
   plus what is still open.
6. **Testing.** Which scenarios prove the slice, and where to look.

**Definition of done is the load-bearing section.** Every line is something a
person can go and confirm: a screen to open, a scenario to plant, a value to
read. No line says "works correctly". That is what makes the bar deterministic:
an agent reads it rather than inferring it.

**Implementation names the decisions, not the design.** It shows that every
choice inside the slice is already settled somewhere, and it names what is still
open, so a reader can see where an agent has a spec and where it does not. The
design itself is in the spec.

**Summary is the only prose. Every other section is flat bullets**, one fact
each, never nested. A paragraph hides how many things are in it. A bullet list
cannot.

# What the Epic holds, and what a Story holds

The Epic bounds the work and states the bar. The Story is the work.

| The Epic holds | The Story holds |
| --- | --- |
| The bar for the whole slice | Acceptance criteria for this one piece |
| Scope boundaries | The user story, as "As a, I want, so that" |
| The decisions that bind the work | Non-functional requirements that bite here |
| Which scenarios prove it | The persona it serves, the seam, the files |

# A slice Epic, written out

This is an invented example for a generic order-management web service. Its
facts are not real.

```markdown
# 08 — Order Tracking

Full spec: `specifications/08-order-tracking.md`

# Summary

The service shows a customer where an order is and why it is late. A customer
opens an order from their list and sees its current status, the history of every
status change, and the carrier's last known location. When the carrier has sent
nothing recent, the page says so rather than guessing.

# Why now

- Until this lands, an order is a row in a list. Nobody can act on one.
- Every later slice reads what this one writes. Refund handling needs the status
  history to decide against.
- Leaving it undone keeps support staff answering "where is my order" by hand.

# Definition of done

- An order opened from the list shows its status, its status history and its
  carrier location.
- A carrier that has been silent for more than a day shows a "no recent update"
  notice instead of a stale location.
- A status change appears in the history within a minute of the carrier event.
- Every carrier event the service could not parse appears on the Unparsed events
  screen.
- Scenarios `late-delivery` and `silent-carrier` both pass at thirty runs.

# Scope boundaries

In:

- the order detail screen
- the status history
- the Unparsed events screen

Out:

- refunds and returns, owned by 10 — Refunds
- the carrier onboarding screen, owned by 09 — Carriers

# Implementation

- The tracking service owns status changes and moves an order through Placed,
  Shipped, Delayed and Delivered (ADR-0012).
- The public API serves what the screens read, and the client never reaches past
  it (ADR-0009).
- A missing carrier update is a gap, never a healthy reading (ADR-0014).
- The Unparsed events list gets its own screen (ADR-0015).
- Open: "Delayed" is a new glossary term. Its boundary with "Late" is not
  settled, and this slice cannot be written into tickets until it is.

# Testing

- Plant `late-delivery`: one order, the delay named, the history showing each
  change.
- Plant `silent-carrier`: the page shows the notice and the Unparsed events
  screen lists the carrier's malformed events.
- Both scenarios graded by the scenario runner at thirty runs.
```
