# Ticket template (local tracker)

Copy the block below to `.scratch/<feature-slug>/issues/<KEY>.md`, where `<KEY>`
is the next unused key (`docs/agents/issue-tracker.md`, the local variant). A
ticket needs no Epic: leave `parent:` empty when the work comes from a roadmap
row or a design doc, and name that source in the body instead.

Template starts below the line.

---
id: PROJ-1
title: <imperative summary>
type: task             # epic | story | task | bug | decision
status: To Do          # To Do | In Progress | In Review | Done | Won't Do
labels: [ready-for-agent]
assignee:
parent:                # key of the owning epic, or empty
blocked-by: []
source:                # the roadmap row, design doc or issue this came from
---

<What to build, in a paragraph. Then the acceptance criteria as a checklist.>

- [ ] <one observable outcome>

## Comments
