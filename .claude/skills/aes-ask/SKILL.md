---
name: aes-ask
description: "Ask which skill or flow fits your situation. A router over the skills in this repo, with the kit's board lifecycle in place of the bare implement skill."
disable-model-invocation: true
---

# Ask which skill fits

This is the project's router. It wraps the vendored `ask-matt` skill
(`vendor/mattpocock-skills/ask-matt/SKILL.md`) with the things that map is
wrong about once the kit's conventions are in place.

Read the vendored file now. It holds the whole map, the main flow, the
on-ramps, and the phase boundaries. Then apply the corrections below. They win
wherever the two disagree.

## The corrections

1. **Wherever the map says `/implement`, run `/aes-implement`.** The bare
   `implement` skill is deliberately not registered here. It knows nothing
   about the board, so running it skips the model check, the claim, the plan
   approval, the acceptance-criteria gate, and the `In Review` handoff. The map
   names `/implement` in several places; every one of them means
   `/aes-implement`.
2. **The tracker is the one `KIT_TRACKER` names, not a default `.scratch/`.**
   The map offers a local-tracker branch that keeps one file per ticket under
   `.scratch/<feature>/issues/`. This project uses that only when `KIT_TRACKER`
   in `.kit/config.env` is `local`. Otherwise tickets live in GitHub Issues or
   Jira, and blocking edges are native links or the body convention
   `docs/agents/ticket-links.md` sets. See `docs/agents/issue-tracker.md`.
3. **Wherever the map says `/writing-for-agents`, run
   `/aes-writing-for-agents`.** The bare skill is not registered here
   either. It is a fine reference on a document's shape, but it says nothing
   about this project's writing standard, and its own text is British-spelled.
   The wrapper carries both corrections. The map names it once, in the on-ramps.
4. **Wherever the map says `/grilling`, `/wayfinder`, `/grill-with-docs`,
   `/triage`, `/improve-codebase-architecture`, or `/grill-me`, run the
   `aes-` prefixed version.** None of the bare names are registered here
   (`docs/agents/skill-overrides.md` has why). The other five named bare
   `grilling` by string, so all six became wrappers together. The map names
   these skills throughout the main flow, the standalone section, and the
   glossary entry for `/grilling` itself.
5. **Wherever the map says `/implement-spec`, run `/aes-implement-spec`.**
   The bare skill is vendored and not registered. It lands the spec on one
   integration branch and opens the pull request itself, which
   `docs/agents/ticket-states.md` does not allow. The wrapper is one Epic,
   one branch and one pull request per ticket.
6. **`/pr` and `/retro` are not installed here.** The map routes both. Neither
   is vendored, because a new upstream skill is opt-in
   (`docs/agents/skill-overrides.md`, the update recipe). Until one is
   adopted, write the pull request body by hand, and put what a retrospective
   would have found into the next rule you write, using
   `docs/agents/writing-a-rule.md`.

## The project's own skills

The vendored map does not know about the skills we wrote ourselves. They are
the ones named with the `aes-` prefix (`KIT_SKILL_PREFIX` in `.kit/config.env`),
which is what the prefix is for. There is no list here, because a list goes stale
the next time we add one. Everything without the prefix is borrowed and behaves
as the vendored map describes.
