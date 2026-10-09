# Wayfinding operations

How a wayfinding map and its tickets behave on the tracker. Used by
`/aes-wayfinder`. A wayfinder ticket is not a delivery ticket and does not
follow [`ticket-states.md`](ticket-states.md).

A **map** is one big issue. Its **tickets** are smaller issues that hang under
it. Every operation below goes through the tracker `KIT_TRACKER` names, using
the operation table in [`issue-tracker.md`](issue-tracker.md).

**The map's detail lives in `docs/maps/`, one file per map, named for it.** The
tracker carries the skimmable version and links to the file; the file is the
full map, written at the depth an agent reads. Its owner is the map ticket, so
nothing in `AGENTS.md` points at it and nothing should. You reach a map from
its ticket. The template is `docs/agents/document-templates/wayfinding-map.md`.

- **The map's title starts `Map | `.** A map and a delivery Epic share an icon,
  for the reason [`issue-types.md`](issue-types.md) gives, so the prefix is what
  tells them apart at a glance and the label is what tells them apart to a
  query. A map is not a capability group and does not follow the rules for
  turning a spec into Epics in [`issue-tracker.md`](issue-tracker.md).
- **A ticket** hangs under the map Epic as its parent, and its label and type
  are picked the way [`issue-types.md`](issue-types.md) says. Never a Story: a
  wayfinder ticket settles a question rather than shipping a feature.
- **Blocking** uses the tracker's built-in **Blocks** link, the same one
  [`ticket-links.md`](ticket-links.md) requires. The blocker *blocks*
  the blocked one. This shows up on the tracker's own screens, so anyone can see
  what is ready to start without opening the map.
- **Finding what is ready to start** takes two steps, because most query
  languages cannot ask "has no open blocker" on their own. First list the map's
  open, unassigned children with their links (in Jira,
  `parent = <MAP-KEY> AND statusCategory != Done AND assignee IS EMPTY ORDER BY
  created ASC`, asking for the links field). Then drop any ticket that has an
  inward *is blocked by* link pointing at something not yet Done. The first one
  left is the one to take. Delivery tickets have their own frontier rule, see
  [`delivery-frontier.md`](delivery-frontier.md); this two-step is the same
  mechanism scoped to one map.
- **Claiming a ticket** means setting its assignee, and it is the first thing a
  session does, before any work, so two sessions never pick the same ticket.
  Look the person's account up through the tracker's own user lookup rather than
  writing an id down in a doc.
- **Finishing a ticket** means: post the answer as a comment, then add one
  line to the map's "Decisions so far" with a short summary and a link. Where
  it moves depends on whether resolving it opened a pull request:
  - **No PR** (a pure decision, nothing to review): move the ticket straight
    to **Done** (some trackers have no "close", so list the available
    transitions and pick the right one).
  - **A PR** (the resolution changed code or docs, such as an ADR): follow
    "The flow" in [`ticket-states.md`](ticket-states.md) instead. The
    ticket goes to `In Review`, not `Done`, and only reaches `Done` once the
    PR merges. Opening a pull request always means a human still has to look
    at it; closing the ticket first would say otherwise.
- **Always use names, never bare keys.** When talking to a person or writing on
  the map, call a ticket by its title. `PROJ-42` means nothing at a glance; a
  title does. Put the key inside the link, not instead of the name.
