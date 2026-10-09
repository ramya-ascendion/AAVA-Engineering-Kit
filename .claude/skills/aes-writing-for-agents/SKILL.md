---
name: aes-writing-for-agents
description: How to structure a document an agent reads — a skill, AGENTS.md, CLAUDE.md, or a doc reached by a pointer. Use when creating or editing any of those. Carries this project's writing standard, which wins wherever the two disagree.
---

# Writing documents agents read, the project's way

Read the vendored `writing-for-agents` skill first
(`vendor/mattpocock-skills/writing-for-agents/SKILL.md`, plus
`SKILL-MECHANICS.md` beside it when the document is a skill). It holds the
whole reference: context pointers, the two loads, the information hierarchy,
progressive disclosure, completion criteria, leading words, and pruning. Then
apply the corrections below. They win wherever the two disagree.

The split is clean, and it is worth holding in mind while reading. The
vendored skill is about a document's **shape**: what sits where, and what
gets pushed behind a pointer. The project's writing standard in `AGENTS.md` is
about its **sentences**. Shape is the vendored skill's to rule. Sentences are
not.

## The corrections

1. **Write American, whatever the vendored file spells.** The vendored text
   uses `behaviour` seven times, plus `minimise` and `optimisation`. That is <!-- spelling-ok: naming the vendored tree's own spellings, which the next sentence says we do not touch -->
   correct for upstream and we do not touch it: vendored text keeps its own
   spelling, per `AGENTS.md`. But it is quoted material, not a model to copy.
   Everything you write for this project is American: `behavior`, `minimize`,
   `optimization`. The gate in `.git-hooks/american-spelling.sh` catches all
   three. A project whose `KIT_SPELLING_LOCALE` is `none` has no such gate, and
   follows whatever spelling its `AGENTS.md` sets.

2. **A leading word still gets defined once, in plain words.** The vendored
   skill's leading-word technique says to repeat a compact word as a token and
   let its definition accumulate across uses. The writing standard says to
   define a technical term once, in a few words, at first use. Do both: pick the
   leading word, then define it plainly the first time it appears, and repeat
   it as a token after that. A reader who meets `tracer bullet` in a project
   doc must not have to infer it from context.

3. **The project's guardrails stay prohibitions.** The vendored skill says to
   prompt the positive, because a ban drags the banned thing into context.
   That is good advice and it holds for most of what we write. It does not
   override the handful of hard guardrails this repo states as bans, such as
   "Never edit a vendored file" or "Do not use smart commit commands". The
   vendored skill allows exactly this exception: a prohibition earns its place
   as a hard guardrail you cannot phrase positively. These are that. Pair
   each with the positive target, which is what those rules already do.

4. **Short sentences win over dense ones.** The vendored skill's own prose
   packs several ideas into long sentences joined by semicolons and colons.
   That is upstream's voice, not a rule it is teaching. `AGENTS.md` asks for
   short sentences, one idea each, and plain everyday words. Follow
   `AGENTS.md`.

## What this does not change

Everything about shape. The hierarchy, progressive disclosure, the two loads,
completion criteria, single source of truth, no-ops, sprawl: take all of it
as written. None of it touches spelling or sentence length, so none of it
conflicts.

The bare `writing-for-agents` skill is deliberately not registered on this
project. It knows nothing about the project's writing standard, so running it
alone gets the shape right and the sentences wrong.
