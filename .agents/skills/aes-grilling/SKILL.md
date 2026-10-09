---
name: aes-grilling
description: Grill the user relentlessly about a plan, decision, or idea, one tight question at a time. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

# Grilling, corrected for this project

Read the vendored `grilling` skill first
(`vendor/mattpocock-skills/grilling/SKILL.md`). It holds the design-tree
model, the frontier, and finding facts yourself instead of asking the user
for them. Then apply the corrections below. They win wherever the two
disagree.

Why this exists: `docs/agents/skill-overrides.md` has the reason. The short
version is that the vendored skill asks the whole frontier in one round, and
that round format is the failure mode, not a bug in how it was followed.

## The corrections

1. **One question per round, not the whole frontier.** Ask the single most
   settled question on the frontier, wait for the answer, then recompute.
   Slower in round count, faster in practice: a five-question round reads as
   one wall of text and gets one skimmed answer back.
2. **Question body under 3 lines.** If it needs more, the question is really
   two questions. Split it, and ask the frontier-first one.
3. **One-line recommendation, one-line runner-up.** State your pick and why
   in a sentence; name the alternative in another. No menu of options with no
   opinion attached.
4. **Facts in a table when there's more than one.** A round that reports
   several facts (found by you, per the vendored skill, never asked of the
   user) lists them as a table, not a paragraph.
5. **A scope check every round: "is this still the ticket's question?"**
   Before asking the next question, check the answer just given against the
   ticket this session is working. A decision that doesn't belong drops or
   spins off as its own ticket. It does not ride along because the
   conversation is already there.
6. **When a ticket is in play, write settled answers on it as a comment, not
   only in chat.** Use the comment operation for the tracker `KIT_TRACKER`
   names (`docs/agents/issue-tracker.md`). A round's outcome that lives only in
   chat is invisible to the next session and to anyone reviewing the ticket
   later.

## When no person is there to answer

A run with no human on the other end (a scheduled run, a subagent, a pipeline)
cannot take one question per round, and it must not stall on a question nobody
will read. Switch to **self-grill**:

1. Compute the frontier as usual, then answer each question yourself from the
   code, the docs and the research, and say which source settled it.
2. Where the facts do not settle it, pick the conservative answer (read-only,
   fails safe, smaller scope) and record it as an **assumption**, not a fact.
3. Write the questions, the answers and every assumption into the design doc
   under a heading called `Assumptions`, so a person can overturn any of them
   at review. The same applies to the seams the `tdd` skill says to agree
   before the first test: state them in the doc instead of asking.
4. Never fake a person's answer. An assumption is labelled as one.

## What this does not change

The design-tree model, computing the frontier, and finding facts yourself
rather than asking the user: take all of it as the vendored skill states
it. None of it conflicts with asking one tighter question at a time instead
of five loose ones.
