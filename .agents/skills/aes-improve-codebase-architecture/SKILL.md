---
name: aes-improve-codebase-architecture
description: Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
disable-model-invocation: true
---

# Improving codebase architecture, corrected for this project

Read the vendored `improve-codebase-architecture` skill first
(`vendor/mattpocock-skills/improve-codebase-architecture/SKILL.md`). It
holds the scan, the report, and how a candidate gets walked into a design.
Then apply the correction below. It wins wherever the two disagree.

## The correction

**Where the vendored text says to call the Skill tool with "grilling" to
walk the decision tree on a picked candidate, call it with `aes-grilling`
instead.** Bare `grilling` is not registered on this project
(`docs/agents/skill-overrides.md` has why); `aes-grilling` is the same
interview with the round format fixed.

## What this does not change

The scan, the report format, and how a chosen candidate feeds into
`/codebase-design`. Take all of it as the vendored skill states it.
