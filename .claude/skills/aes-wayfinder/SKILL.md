---
name: aes-wayfinder
description: Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.
disable-model-invocation: true
---

# Wayfinding, corrected for this project

Read the vendored `wayfinder` skill first
(`vendor/mattpocock-skills/wayfinder/SKILL.md`). It holds the whole flow:
the map, tickets, ticket types, fog of war, and the two invocation modes.
Then apply the correction below. It wins wherever the two disagree.

## The correction

**Wherever the vendored text says to call the Skill tool for "grilling", call
it for `aes-grilling` instead.** Three places: the Grilling ticket type,
naming the destination, and "if in doubt" while resolving a ticket. Bare
`grilling` is not registered on this project (`docs/agents/skill-overrides.md`
has why); `aes-grilling` is the same interview with the round format fixed.

## What this does not change

Everything else: the map's shape, ticket types, claiming, fog of war, out of
scope, and both invocation modes. Take all of it as the vendored skill
states it. See `docs/agents/wayfinding-operations.md` for how this project's
tracker expresses the map and its tickets.
