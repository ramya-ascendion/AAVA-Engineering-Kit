# The delivery frontier

Which delivery tickets are free to start right now, and how a skill picks the
next one. What a slice is, and how its Epic is written, is
[`slices.md`](slices.md).

The frontier is every delivery ticket free to start right now. `/aes-work-the-path`
walks it, and this section is the rule it walks by.

A ticket is on the frontier when all four hold:

- It is a Story, Task or Bug in this project, not yet `Done` and **neither
  `In Review` nor `Blocked`**, carrying `ready-for-agent` (fully specified,
  agent-drivable work). `In Review` is excluded whatever its label says: the next
  action there is a human's. Labels drift when nothing enforces them, and a
  ticket left `In Review` + `ready-for-agent` would otherwise read as
  implementable when its code has already shipped. `Blocked` is excluded
  because nobody here can move it at all, and in some trackers its status
  category is the same as `To Do`, so a plain "not Done" filter lets it straight
  through.
- It is assigned to you or assigned to nobody. **A ticket assigned to anyone
  else is never touched**, and everything blocked behind their open work drops
  out on the next rule anyway.
- Nothing open blocks it. Most query languages cannot ask "has no open blocker"
  on their own, so it takes two steps: fetch candidates with their links, then
  drop any that hold an inward *is blocked by* link at a ticket that is not
  `Done`. `In Review` is not `Done`: a blocker awaiting review still blocks.
- It is not wayfinder work. A ticket carrying a `wayfinder:*` label settles a
  question instead of shipping code, and has its own lifecycle in
  [`wayfinding-operations.md`](wayfinding-operations.md). **Drop it by label,
  not by type.** An issue type can lag behind the label that owns the fact, and
  a ticket whose type has not caught up is still a Task, which this scan
  otherwise accepts. See [`issue-types.md`](issue-types.md).

Order what is left by these keys, each one breaking ties in the one before it:

1. **Fix version, earliest first.** Every `v0.1` ticket comes before any
   `v2.0` ticket. The rules for reading a version follow this list. A project
   that does not use versions skips this key.
2. **Your own tickets before unassigned ones.** A ticket bounced back from
   review is yours and actionable; finish it before opening new work.
3. **Leverage, highest first**: how many open tickets sit behind the
   candidate through the whole chain of Blocks links, the same `blocks N` a
   board viewer's critical-path page would compute. The ticket holding up the
   most work goes first.
4. **The parent slice, earliest first**, by its position in the Blocks-ordered
   build sequence of the slices.
5. The lowest key.

A fix version is the release a ticket ships in
([`slices.md`](slices.md)). Three rules turn it into a sort key:

- **Compare versions as numbers, one part at a time.** `v0.2` comes before
  `v0.10`, which a text sort gets backwards.
- **A ticket with no fix version counts as `v0.1`** until every ticket carries
  one. A ticket with several counts as the earliest.
- **A ticket takes the earliest version of any open ticket behind it** through
  the Blocks chain. A `v2.0` ticket that blocks `v0.1` work is `v0.1` work,
  because the `v0.1` ticket cannot start until it lands. Without this rule a
  blocker would sort below the ticket it holds up.

**Claiming an unassigned pick is the first act**, before any work, planning
included. Assignee set, `To Do → In Progress`, the same rule "Claiming a
ticket" uses for wayfinder tickets in
[`wayfinding-operations.md`](wayfinding-operations.md). A plan the engineer
declines means letting the ticket go again, per "Letting go of a ticket" in
[`ticket-states.md`](ticket-states.md).

The candidate query, with the fewest fields that answer the question. In Jira:

```
project = PROJ AND issuetype in (Story, Task, Bug)
  AND statusCategory != Done
  AND status not in ("In Review", "Blocked")
  AND labels = "ready-for-agent"
  AND (assignee = currentUser() OR assignee IS EMPTY)
ORDER BY key ASC
```

On `github`, the same filter is
`gh issue list --state open --label ready-for-agent --json number,title,labels,assignees`
followed by dropping any whose status is `In Review` or `Blocked`, and any
labeled `wayfinder:*`. On `local`, filter the front matter under `.scratch/`.

That query is necessary, not sufficient. Drop any candidate that already has
an open PR the board hasn't caught up with, per the scan in
`/aes-work-the-path`.
