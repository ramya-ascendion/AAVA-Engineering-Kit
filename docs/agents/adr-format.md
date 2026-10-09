# ADR format: this repo's extra rules

The base format comes from the vendored `domain-modeling` skill
(`vendor/mattpocock-skills/domain-modeling/ADR-FORMAT.md`): Context, Decision,
optional Status frontmatter, optional Considered Options and Consequences.
This file adds this repo's rules on top. Where the two disagree, this file wins.

## Two extra frontmatter fields

- **Amended-by** (`amended-by: ADR-NNNN, ADR-NNNN`) — when a later ADR strikes
  or narrows part of this one.
- **Affects** (`affects: <area>`) — this ADR binds a named area of the product,
  so a generated design brief can carry its title and path. A new ADR joins the
  brief by adding the line, and the brief generator reads nothing else to
  decide. Pick the area from the values the generator reads; if the project has
  no brief generator, the field is optional.

## Writing style

Follow the writing standard in the root `AGENTS.md`. Four extra rules for ADRs:

- The decision comes before any backstory or amendment. A reader gets the rule
  first, then how we got there.
- An amendment is quoted *after* the rule it modifies, never above it.
- Edit history lives in frontmatter (`status`, `amended-by`), not narrated in
  the body. Don't tell the reader what an earlier draft said.
- The title states the decision, not the topic. "The service runs on a job
  queue" is a decision. "How the service runs jobs" is a topic.

## ADR budget

- Rules first, as bullets. Backstory and reasoning after, if at all.
- One line per rejected option: what it was and why it lost. Not a paragraph.
- Aim under 60 lines. Measure your own set with `wc -l docs/adr/*.md` and note
  the shortest, longest and median. Under 60 is a target to notice missing,
  not a hard cap.
- A diagram lives in the ADR that owns the decision, embedded above or below
  the rules it illustrates, with its `.mmd` beside the ADR file. No companion
  page whose only job is to describe it.

## Restyling existing ADRs

- A restyle never changes meaning. This is the rule the rest of them serve.
- An ADR is restyled when it fails to communicate, and during a
  writing-standards review. A superseded ADR is restyled on the same terms as
  any other: what history needs kept is its meaning, not its sentences.
- Filenames never change, because other ADRs link by filename. One
  exception: a vocabulary ruling (a recorded decision on which word the project
  uses) may rename a file whose name uses the retired word. The rename fixes
  every inbound link in the same commit, so a `grep` over the repo for the old
  name comes back empty. Links from outside the repo, such as tracker tickets
  and pull request bodies, are not in that grep and are fixed by hand.
- A restyle keeps every claim, number, date, attribution line, cross-link, and
  table. Only sentences and ordering may change. Note the restyle in the commit
  message, never in the file.
