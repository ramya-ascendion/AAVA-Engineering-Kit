# Dependencies and relationships: how tickets link to each other

How a ticket says what it needs, what it blocks, and what it belongs to. The
tracker itself, and how to publish to it, is [`issue-tracker.md`](issue-tracker.md).

Links are how the critical path shows up on the board. A missing `Blocks` link
is a ticket an agent will start too early, so creating the links is part of
creating the ticket. It is not a tidy-up job for later.

# The link vocabulary

Three link types are ours to create.

| Type | Use it for | How it reads |
| --- | --- | --- |
| `Blocks` | Order. This cannot start until that is done. | "is blocked by" / "blocks" |
| `Related` | Same area, no order. Also a ticket to its owning capability. | "Related to" |
| `Duplicate` | The work is already tracked somewhere else. | "Duplicates" |

How each is written depends on `KIT_TRACKER`:

| `KIT_TRACKER` | `Blocks` | `Related` | `Duplicate` |
| --- | --- | --- | --- |
| `jira` | a `Blocks` issue link | the project's `Related` link type, spelled exactly as the site spells it | a `Duplicate` issue link |
| `github` | a `Blocked by: PROJ-217` line per blocker at the top of the body, or the native issue-dependency feature if the repo uses it | a `Related: PROJ-n` line | a `Duplicate of: PROJ-n` line |
| `local` | the `blocked-by:` list in the ticket file's front matter | a `Related:` line in the body | a `Duplicate of:` line in the body |

Pick one spelling per project and use it everywhere, because the frontier scan
([`delivery-frontier.md`](delivery-frontier.md)) reads exactly that spelling.

Some trackers ship more link types than these three. Do not use the rest:

- **A type whose labels read backwards is banned by name.** If a type's inward
  label says "blocks" where the real `Blocks` link says "is blocked by", an
  agent that picks a link by reading its labels gets the direction wrong every
  time. Check the label wording on your tracker before using any type you did
  not set up yourself.
- **A type the tracker writes itself is never created by hand.** A clone link
  is created when someone uses the clone action.
- **A type owned by another product** (a product-discovery add-on, say) means
  nothing on this board.

**The `Blocks` link is not the `Blocked` status.** The link orders two tickets
here against each other. The status says someone outside this team has to
act. A ticket can carry both, and neither one implies the other. See "Blocked:
waiting on someone outside the team" in [`ticket-states.md`](ticket-states.md).

# Getting the direction right

Say the relationship in the tracker's own words before you touch the tool:

```
PROJ-217 blocks PROJ-218
PROJ-218 is blocked by PROJ-217
```

Those are one link, not two, read from its two ends. What it means is
**PROJ-217 must be done before PROJ-218 can start.** If that sentence is not the
one you meant, stop and swap the keys.

Only then translate it into the call. In trackers with an API that takes an
inward and an outward end, the field names never say "blocker":

| In words | In the call |
| --- | --- |
| the one that must finish first | `inwardIssue` |
| the one that has to wait | `outwardIssue` |

```
type:         Blocks
inwardIssue:  PROJ-217   # blocks
outwardIssue: PROJ-218   # is blocked by
```

**The link states the order. It does not enforce it.** The tracker will happily
let anyone move PROJ-218 to `In Progress` with PROJ-217 still open, and no
automation here says otherwise. What obeys the link is the frontier scan, which
drops any ticket holding an inward *is blocked by* link to something not yet
Done, and the agent that runs it. A `Blocks` link is a fact on the board that
the process reads, not a lock.

Read one back before you trust a batch of them. Fetch the ticket that should be
waiting and look at its links. Each entry names the *other* ticket, so the one
you want reads as "this ticket is blocked by PROJ-217". If it comes back the
other way round, the keys were swapped and every link in the batch is backwards.

# The link pass, at creation

**Every new Story, Task, or Bug gets a link pass before the agent reports it as
created.** Not afterwards, and not only when asked. A ticket published with no
links is a ticket with no stated order, and the frontier scan will hand it to an
agent as ready when it is not.

Four steps.

**1. Search the board for candidates.** Use the domain nouns from the ticket's
own title, not the whole title. In Jira that is a query like:

```
project = PROJ AND statusCategory != Done
  AND issuetype in (Story, Task, Bug)
  AND (summary ~ "invoice export" OR summary ~ "pagination")
ORDER BY created DESC
```

On `github` it is `gh issue list --state open --search "invoice export" --json
number,title,labels`, and on `local` a `grep` over `.scratch/`.

Then the siblings under the same Epic, which the keyword search will miss when
they are worded differently. You are reading them for **order** only: they
already share a parent, so relatedness needs no link between them.

```
parent = <EPIC-KEY> AND statusCategory != Done ORDER BY created ASC
```

**Ask for few fields and this search is cheap.** Summaries, labels and links with
a page of about 25 results is a few kilobytes. Leave the fields off and a Jira
search returns every full description, which is what makes the search feel
unusable.

**2. Classify each candidate.**

| What is true | Link | Which way round |
| --- | --- | --- |
| The new ticket cannot start until the candidate is done | `Blocks` | the candidate blocks the new ticket |
| The candidate cannot start until the new ticket is done | `Blocks` | the new ticket blocks the candidate |
| Same code or same test, either order is fine | `Related` | either side |
| The candidate is the capability this ticket serves, and the hierarchy cannot hold it | `Related` | either side |
| The candidate already tracks this work | `Duplicate` | stop, and do not create the ticket |

**When the duplicate already exists,** the table's "do not create the ticket"
has nothing to say, and closing one is not the agent's call. Link the two with
`Duplicate`, then report both keys and which one you would keep and why. A human
decides, and the one that loses closes as `wontfix` (see "Letting go of a
ticket" in [`ticket-states.md`](ticket-states.md)). Two open tickets for one
piece of work is worth interrupting someone over: it is how the same thing gets
built twice.

**3. Create the links,** in that same session, before the report.

**4. Say what you found,** including finding nothing.

# Keeping the critical path readable

- **`Blocks` is the only link that carries order.** `Related` never stands in
  for it. Two tickets that must land in sequence, joined by `Related`, read on
  the board as parallel work that either agent can pick up first.
- **Order is always recorded, parent or no parent.** Two children of the same
  Epic that must land in sequence get a `Blocks` link like any other pair. A
  shared parent says they belong together. It never says which one goes first,
  and the crossing test below is about `Related` only.
- **The test for `Related` is whether the tie crosses a parent.** Two tickets
  under the same Epic need no link between them, because the parent already says
  it. A tie to work under a *different* Epic is the one nobody browsing either
  Epic can see, so link it. There is no cap: eight honest links beat three and a
  guess.
- **Nothing shared and no order still means no link.**
- **Say "no blockers found" out loud** in the report. Silence cannot be read: it
  looks the same whether the ticket is genuinely free to start or nobody
  checked.
- **Skip a blocker that is already Done.** It cannot gate anything. If the
  history matters, put it in the description instead of the link panel.
- **Link late if you learn late.** An order that only shows up during
  implementation or review gets its link then. Same rule, later moment.

# A ticket that touches a whole family

Some tickets are not one edge but a fan of them: a rename across every test
scenario, a convention applied everywhere. A change like "rename the fixtures
for what they test" can touch a dozen open tickets across several Epics.

Link them where they cross a parent, by the rule above. What you must not do is
stop there and call the critical path stated. `Related` carries no order, and a
change landing across a dozen tickets has plenty. So either name the tickets it
genuinely gates with `Blocks`, or sequence it the way `/to-tickets` sequences a
**wide refactor**: expand, migrate in batches, contract. A dozen unordered edges
look like a plan and are not one.

# Parents

**A parent is not a link, and never needs one.** A slice Epic owns its delivery
tickets as children, and that parent-child relationship already says everything
a `Related` link between them would say. Never create one. Where the tracker's
own hierarchy fits the relationship, use the hierarchy.

**That covers relatedness, not order.** A parent tells you nothing about
sequence, so two children that must land in a given order still get a `Blocks`
link between them.

`Related` is for the relationships the hierarchy cannot hold. Where a capability
sits at the same hierarchy level as a Story, it cannot be a parent, which is the
whole reason that one edge is a link instead.

- Parent capabilities to their Epic using the tracker's native parent
  relationship.
- Where the hierarchy places capability, Story, and Task at the same level,
  implementation tickets cannot be children of capabilities. Associate each
  implementation ticket with its owning capability using a **Related** link.
- A test-seam spike blocks tickets whose test strategy depends on its result.
- Do not encode dependency order only in prose when a link can represent it.
