---
name: aes-implement
description: "Implement a ticket the kit's way: check the model, claim the ticket, get the plan approved, build with the vendored implement skill, check off the acceptance criteria, ask before opening the pull request, and move the ticket to In Review once it is open."
disable-model-invocation: true
---

# Implement a ticket

This is the entry point for delivery work. It wraps the vendored
`implement` skill (`vendor/mattpocock-skills/implement/SKILL.md`) with the
board rules this project adds. The rules themselves live in
`docs/agents/ticket-states.md`, and **that file is the source of truth**. Read
it now, before anything else. This file only names the stops; the doc says what
each one requires.

Every tracker operation below (read, claim, comment, move, label) is done the
way `docs/agents/issue-tracker.md` says for the tracker `KIT_TRACKER` names in
`.kit/config.env`. Never assume one tracker.

The stops, in order:

1. **Check what you are running**: the model-and-effort check, asked once at
   the start.
2. **Read the ticket, claim it, move it to `In Progress`.**
3. **Plan, and get the plan approved** before writing any code.
4. **Build**, following the vendored skill: `/tdd` where possible at
   pre-agreed seams, typechecking regularly, the full test suite once at the
   end, then `/code-review`, then commit to the current branch.
5. **Check off the acceptance criteria** in the ticket. The ticket stays
   `In Progress`, because self-review is still ahead.
6. **Ask before opening the pull request.** Never open one unprompted. On
   "go", open it.
7. **Move it to `In Review` and swap the triage label once the PR is open**
   (`ticket-states.md`, "The flow", step 5).

The bare `implement` skill is deliberately not registered on this project.
It knows nothing about the board, so running it skips every stop above.
