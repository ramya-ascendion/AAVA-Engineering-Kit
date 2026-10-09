# Issue tracker: three variants, one set of rules

**Where tickets live is a setting, not a rule.** `KIT_TRACKER` in
`.kit/config.env` says which of three trackers this project uses, and every
other file in `docs/agents/` talks about "the tracker" and "a ticket" so the
rules read the same whichever one it is. This file is the way in: it says what
each variant is, how each logical operation is carried out on it, and where the
rest of the rules live.

The ticket key prefix comes from `KIT_TICKET_PREFIX` in the same file. Examples
here use the neutral `PROJ-123`.

| `KIT_TRACKER` | Tickets live in | Reached with |
| --- | --- | --- |
| `github` | GitHub Issues in this repo, optionally a GitHub Project | the `gh` CLI |
| `jira` | a Jira project | the connected Atlassian tools (an MCP connector), not a local Jira CLI |
| `local` | markdown files under `.scratch/` in this repo | ordinary file edits |

Pick one per project and do not mix them. A skill reads `KIT_TRACKER` and
branches. A skill that supports only one variant is a bug in the skill.

## Ticket keys

A ticket is referred to by its key, `PROJ-123`, everywhere: branch names, commit
subjects, pull request titles, comments.

- **`github`**: the number is the issue number, so issue 123 is `PROJ-123`. In
  a commit body or pull request body you may also write the native `#123`;
  closing keywords belong in the pull request body, never in a commit message.
- **`jira`**: the key is Jira's own, and `KIT_TICKET_PREFIX` must equal the
  Jira project key.
- **`local`**: the key is the file's `id`. A new ticket takes the next unused
  number under `.scratch/`.

## The logical operations, and how each variant does them

The rules talk in terms of these operations. Read across a row to find the
mechanism for your tracker.

| Operation | `github` | `jira` | `local` |
| --- | --- | --- | --- |
| Create a ticket | `gh issue create --title ... --body-file ...` | create an issue in the project, body in the description | new file `.scratch/<feature>/issues/PROJ-123-slug.md` |
| Fetch a ticket | `gh issue view 123 --json title,body,labels,assignees,state,comments` | fetch the issue by key | read the file |
| Comment | `gh issue comment 123 --body-file ...` | add a comment | append a dated line under `## Comments` |
| Set a label | `gh issue edit 123 --add-label X --remove-label Y` | edit the issue's labels | edit the `labels:` list in the front matter |
| Set the status | the Project's `Status` field when the repo uses one, otherwise a `status:*` label; `Done` is closing the issue | transition the issue | edit `status:` in the front matter |
| Set the assignee | `gh issue edit 123 --add-assignee <login>` | assign the issue | edit `assignee:` |
| Record "blocked by" | see [`ticket-links.md`](ticket-links.md) | a `Blocks` issue link | `blocked-by:` list |
| Record a parent | a `Parent: PROJ-n` line in the body, or sub-issues where the repo has them | the native parent field | `parent:` |
| Search | `gh issue list --search ... --json number,title,labels` | a JQL search (see "Searching" below) | `grep` over `.scratch/` |

**A ticket's status is one of five names in every variant:** `To Do`,
`In Progress`, `In Review`, `Done`, and `Blocked`. [`ticket-states.md`](ticket-states.md)
owns how a ticket moves between them. A tracker whose own workflow has fewer or
different names maps onto these five and says how here, once. A `github` project
with no Status field uses the `status:*` labels so the five names still exist.

### The local variant's file shape

Tickets live at `.scratch/<feature-slug>/issues/<KEY>.md`. **`.scratch/` is
tracked state when `KIT_TRACKER` is `local`**: the tickets are the tracker, so
they are committed with the work they describe. A project that uses `.scratch/`
for throwaway notes instead keeps those in a folder of their own and ignores it.
The starting shape is `document-templates/ticket.md`.

```markdown
---
id: PROJ-123
title: <imperative summary>
type: story            # epic | story | task | bug | decision, see issue-types.md
status: To Do          # one of the five names above
labels: [ready-for-agent]
assignee:
parent:                # key of the owning epic, or empty. Work from a roadmap row has none
blocked-by: []         # keys that must be Done first
fix-version:           # optional, v<major>.<minor>
---

<The ticket body: what to build, then the acceptance criteria as a checklist.>

## Comments
```

The `local` variant gives up everything the other two do for you (notification,
search, history). Use it for a solo project or a repo with no tracker yet, and
move to `github` or `jira` when a second person starts picking up tickets.

## Issue conventions

- Pick the label and the issue type from [`issue-types.md`](issue-types.md). The
  label owns the fact and the type mirrors it. Implementation work is a **Story**
  by default.
- Put the complete spec or ticket body in the ticket description using Markdown.
- Apply the triage label from [`triage-labels.md`](triage-labels.md).
- Use comments for follow-up discussion and durable progress updates.
- Refer to work by its key, for example `PROJ-123`.
- Treat accepted ADRs as the current delivery boundary. A ticket may preserve a
  wider product outcome while naming the narrower behavior in scope now and the
  scope that is deferred.

## When a skill says "publish to the issue tracker"

Create the appropriate ticket with the operation table above. A completed
`/to-spec` creates an Epic only when it adds a capability group or a
cross-cutting concern. A single capability is a Story or a Task under an
existing Epic, not an Epic of its own. `/to-tickets` creates Story or Task
tickets and links each one to its owning Epic. Apply `ready-for-agent` to
implementation tickets after the ticket breakdown is approved.

## When a skill says "fetch the relevant ticket"

Fetch the ticket by key with the operation table above and treat its description,
links, status, labels, and comments as the tracker record.

## Searching without blowing the context

This section is about the `jira` variant, where a careless search is expensive.
`github` and `local` searches are cheap by comparison, but the habit transfers:
ask for the fewest fields that answer the question.

**Always pass `fields`, and treat about fifty tickets as the ceiling for one
search.** Omitting `fields` returns the description of every ticket, and
descriptions are specs.

Passing `fields` is necessary and not sufficient. A field that is an object
(issue type, status, assignee) comes back fully expanded on every row, so two or
three fields can still cost around a thousand bytes per ticket.

- **Needing a number, not a list, is the big saving.** A count-only search
  answers in a few hundred bytes however many tickets match.
- **Ask for the fewest fields that answer the question.** A summary is a string
  and costs almost nothing. Type, status and assignee are objects.
- **Narrow with the query rather than filtering afterward.** A label or type
  clause costs nothing and cuts the rows.
- **An overflowing result is not lost.** It is written to a file, and `jq` or
  Python reads it. That is a wasted round trip, so size the query first.

## Where each rule lives

This file is the way in. Each rule below has its own file, so that reading one
of them costs one of them.

| The question | The file |
| --- | --- |
| Which issue type does this ticket get? | [`issue-types.md`](issue-types.md) |
| How do tickets link to each other? | [`ticket-links.md`](ticket-links.md) |
| How does a Story, Task or Bug move? | [`ticket-states.md`](ticket-states.md) |
| When has a ticket sat still too long? | [`ticket-stalled-clock.md`](ticket-stalled-clock.md) |
| How does an Epic move? | [`epic-lifecycle.md`](epic-lifecycle.md) |
| What is a slice, and how is its Epic written? | [`slices.md`](slices.md) |
| Which ticket is free to start now? | [`delivery-frontier.md`](delivery-frontier.md) |
| How does a wayfinding map work here? | [`wayfinding-operations.md`](wayfinding-operations.md) |
| What do the board states look like? | [`ticket-lifecycle.md`](ticket-lifecycle.md) |
| Which triage label means what? | [`triage-labels.md`](triage-labels.md) |
| How are branches, commits and PRs named? | [`git-conventions.md`](git-conventions.md) |

**Tooling work does not live on the delivery board.** Work on the tools the team
builds with goes to its own label or project. See [`devx-issues.md`](devx-issues.md).

## Integration language

- Describe external ticketing and vendor integrations through provider-neutral
  contracts.
- Product-specific connectors are future work. Do not name a future integration
  product in current Epics, Stories, or Tasks.
