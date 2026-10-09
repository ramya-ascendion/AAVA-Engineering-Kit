# Ranking the frontier, and the look-ahead

Read this at "Rank what is left" in `SKILL.md`, once the candidates are in
hand and the blocked ones are dropped. A `report` run needs it. A run handed
an explicit ticket key does not. The pick is already made, and nothing here
would change it.

The order is `docs/agents/delivery-frontier.md`, "The delivery frontier". This
file says how to apply it, and what the announcement owes the engineer.

1. Build the Blocks graph: fetch the open delivery tickets with the links and
   fix-version fields (paginate if needed). Walk the whole chain behind each
   candidate once, and take two numbers from the walk: its leverage (how many
   open tickets sit behind it, the same `blocks N` a board viewer's
   critical-path page would compute) and its fix version (the earliest across
   the candidate and everything behind it, by the rules in
   `docs/agents/delivery-frontier.md`).
2. **Flag a pick that already has commits on the default branch, but do not
   drop it.** Excluding `In Review` does not catch everything: a merged ticket
   left `In Progress` + `ready-for-agent` looks coherent and passes the query.
   Say so at the announcement: "PROJ-152 has commits on the default branch under
   its own subject, so it may need closing out rather than building". Then let
   gate 0 settle it. The plan for such a ticket is often "close this out", which
   is exactly the kind of thing the plan gate exists to put to a person.

   **Do not turn this into a filter.** Whether a ticket's work is already
   merged is not reliably decidable from git, and a wrong guess hides ready
   work, which is worse than offering it. Two failure modes to expect: a
   `git log --grep=PROJ-142` that returns commits whose subjects name *other*
   tickets and merely mention PROJ-142 in the body as a blocker, and a ticket
   whose matching commits are all research docs while its implementation has not
   started. Match the key in the **commit subject or a merged PR title** rather
   than anywhere in the message, treat the result as evidence for a person, and
   never as a verdict.
3. Pick in the order `docs/agents/delivery-frontier.md` sets. Read the slice
   positions from the cached build order.

**Announce the look-ahead, then the pick.** Name the top three frontier
tickets, always with names and the key inside the link, never bare keys, with
one line on why they lead the path. Then the pick itself: its fix version, its
leverage count and what it unblocks, plus any offers from the scans. When a
pick's version came from a ticket behind it rather than its own field, name
that ticket, so the engineer can see why a `v2.0` ticket leads. In `report`
mode, also list every write that would happen: the claim, the PR and the move to
`In Review`, the branch name, the PR title. Then stop. Write every ticket the
way `SKILL.md` Arguments says a report writes one, in the look-ahead, the
pick, the scan, and the blocked list.
