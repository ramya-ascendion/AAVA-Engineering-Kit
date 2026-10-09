# A ticket that stops moving

When a claimed ticket has sat still long enough to be worth showing, how the
days are counted, and who clears it. The lifecycle these thresholds sit inside
is [`ticket-states.md`](ticket-states.md), and Epics are exempt from all of it.
See [`epic-lifecycle.md`](epic-lifecycle.md).

Sitting still is the one thing a claimed ticket may not do. A ticket nobody is
moving takes one of the two exits in [`ticket-states.md`](ticket-states.md),
"Letting go of a ticket". It is closed as `wontfix`, or returned to `To Do` and
unassigned so it re-enters the pool, or it starts moving again. This rule forces
that choice. It does not add a third way out.

**Blocked counts as sitting still.** Neither kind of blocked is exempt: not
the `Blocked` status, and not a ticket held up by an *is blocked by* link.
Blocked-and-parked is where a forgotten ticket hides, and a wait on an outside
party is the easiest one to forget, because nobody here has to do anything for
it to keep going.

# The two thresholds

Counted in working days since the last status change. Both are defaults for the
team to tune.

| Working days | Label | Who it calls on |
| --- | --- | --- |
| 3 | `aging` | The assigned engineer |
| 7 | `stale` | The whole team |

Both words are borrowed rather than invented. `aging` is Kanban flow-metrics
vocabulary: work item age is one of the standard flow metrics. `stale` is what
most trackers call an issue that has gone quiet. A ticket ages, then it goes
stale.

**Neither label is a mark against the engineer.** A label that reads as blame is
a label people learn to dodge, so both say what the ticket is, and neither says
anything about the person holding it.

- **`aging` is the assigned engineer's cue** to check the default branch for
  changes that affect the work, and to have a plan for getting the ticket moving.
  Asking a peer may well be that plan.
- **`stale` is the team's cue to look at it.** What the look finds is open: a
  blocker to remove, work to redistribute from someone overloaded, or just a
  ticket everyone had stopped seeing. By the time a ticket is stale it is no
  longer one person's problem to notice alone.
- **Neither label means `Blocked`.** Blocked means nobody here can move until
  someone outside acts. A `stale` ticket may have nothing blocking it at all.
  The labels say the ticket has not moved, and nothing more.
- **On a blocked ticket the two labels ask for something different, and they
  ask the lead.** `aging` is the lead's cue to go back to the outside party, not
  the assigned engineer's cue to re-plan work nobody can start. `stale` widens it
  to the team: escalate it, or admit the wait is open-ended and take one of the
  two exits.

# Which tickets the clock runs on

**Claimed work in flight, plus everything blocked.** A ticket is a candidate
when it sits in `Blocked`, or when it has an assignee and sits in `In Progress`
or `In Review`.

**`Blocked` is in that list on purpose.** A ticket waiting on another company is
still a ticket nobody has moved, and it is the one that can sit for weeks
without anybody here noticing how long, because nothing on our side has to
happen for the wait to continue. The thresholds are the same 3 and 7 working
days; blocked work does not get a longer leash for being blocked.

**The assignee filter does not apply to `Blocked`.** Every blocked ticket is
counted, owned or not. The filter exists to keep the untouched backlog out of
the count, and a blocked ticket is not backlog. It is a wait somebody started
on purpose. A ticket blocked straight out of `To Do` has no assignee to filter
on, and it is exactly the one that would otherwise sit unseen.

**An unassigned `To Do` ticket is never `aging` or `stale`.** It is the pool of
free work, and a ticket nobody has taken has not stopped moving. It never
started. Counting the backlog would stamp every untouched ticket and bury the
few that are genuinely stuck. `Blocked` is not that pool: nobody can pick it up,
so sitting there is not the same as sitting in the backlog.

This filter runs before the count, not after. It is the difference between a
list someone reads and a list everyone learns to ignore.

# Counting the days

**Count full working days elapsed since the last status change, per your team
calendar.** A change on Friday afternoon is 1 working day old on Monday
afternoon, not 3. Weekends and the days your team calendar marks as non-working
do not count.

Changing the unit from calendar days to working days only ever makes a ticket
look fresher, never staler. So nothing is flagged sooner than it would have
been under a calendar count.

**Read the status history, not the `updated` field.** `updated` is edit time,
and the two come apart exactly when it matters. A comment, a label, an edit to
the description: each one bumps `updated` and moves no status at all. So on a
board sorted by "recently updated", the tickets people are still talking about
look the freshest, and those are the ones this rule exists to find.

# Two exemptions

- **Epics are exempt.** An Epic holds `In Progress` on purpose while its
  children move. See "An Epic does not move like a delivery ticket" in
  [`epic-lifecycle.md`](epic-lifecycle.md) for why.
- **Time off is deliberately not modeled.** Long-running work should not start
  before a vacation without a handoff plan. The handoff is the fix, not an
  exemption.

# Who counts, and who clears

A board watcher reads each ticket's status history, counts working days, and
stamps `aging` or `stale`. The kit ships no watcher; it is a scheduled job or a
board viewer the project builds. Tracker automation does exactly one job: clear
both labels on any status change. No agent sets either label by hand.

**The counting cannot live in a tracker rule.** Query languages count calendar
days and know no holidays, which would put back the Friday-to-Monday error the
working-day rule exists to remove. The watcher has to count `Blocked` tickets
along with the other two statuses.

**The labels exist for agents, not for color.** An agent managing the board
finds every ticket that has stopped moving in one query, instead of walking
every status history itself. Colored label chips and board quick filters were
rejected as the human-facing half: a viewer can color its own rows, so no
label color is needed.

**Whatever surfaces this has to show the lane.** When most of the tickets sitting
still are in `In Review`, that is a review queue backing up, which is a different
problem from work nobody is doing. One table with no lane column tells one story
for two problems.

**A blocked ticket is marked where it sits, not moved.** It is stamped like any
other, but it shows in the blocked panel carrying its `aging` or `stale` mark.
It does not also appear in the aging and stale panel. One ticket, one row.

**The blocked panel is the lead's list.** It is what tells them which blocks are
theirs to clear, so a ticket landing there is the whole handoff. Nothing else
gets written down to give it to them. That is also why the age belongs on the
row: without it the panel says what is blocked and not which wait has gone
unanswered longest, which is the only thing that sorts one call ahead of another.

The blocked panel is the list someone takes into a conversation with the other
team or the partner, and how long each wait has run is the strongest thing on
it. Move those rows to the aging panel and that list is split in half: the
blocked panel stops saying which wait is the old one, and the aging panel fills
with tickets whose fix is a phone call to another company, not a plan from the
assigned engineer.
