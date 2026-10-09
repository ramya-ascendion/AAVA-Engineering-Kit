---
name: aes-triage
description: Move issues and external PRs through a state machine of triage roles, categorize, verify, grill if needed, and write agent-ready briefs.
disable-model-invocation: true
---

# Triage, corrected for this project

Read the vendored `triage` skill first
(`vendor/mattpocock-skills/triage/SKILL.md`). It holds the whole state
machine: categorize, verify the claim, grill if needed, write the brief.
Then apply the corrections below. They win wherever the two disagree.

## The corrections

1. **Where the vendored text names a triage role, use this project's label
   string instead.** The five canonical roles map to tracker labels used
   verbatim: `needs-triage`, `needs-info`, `ready-for-agent`,
   `ready-for-human`, `wontfix`. `docs/agents/triage-labels.md` is the full
   mapping, including the other labels (`aging`, `stale`, `slice`,
   `wayfinder:*`) that sit alongside a turn label rather than replacing it.
   Set labels with the operation for the tracker `KIT_TRACKER` names
   (`docs/agents/issue-tracker.md`).
2. **Where "Grill (if needed)" calls the Skill tool for "grilling", call it
   for `aes-grilling` instead.** Bare `grilling` is not registered on this
   project (`docs/agents/skill-overrides.md` has why); `aes-grilling` is
   the same interview with the round format fixed.

## What this does not change

The state machine itself: categorizing, verifying a claim before grilling,
and writing the agent-ready brief. Take all of it as the vendored skill
states it.
