# Skills across harnesses

Claude Code reaches every skill in a repo that uses this kit through two hops of
symlinks. Codex and Cursor have no proven path to the same skills. That is the
gap this page records.

**Figure:** three harnesses read `AGENTS.md` directly, but only Claude Code has a
traced path to the skills. It resolves `.claude/skills`, every entry of which is
a symlink into `.agents/skills`, which holds our `aes-*` skills as real
directories and one symlink per borrowed skill into `vendor/mattpocock-skills`.
Codex has no proven path into `.agents/skills`, and the Codex interface metadata
file that every vendored skill ships is absent from all of ours. Cursor's
configuration directory is typically gitignored, so nothing about it is tracked
in the repo. Source: [`skills-across-harnesses.mmd`](skills-across-harnesses.mmd).

**Only the in-scope path is verified.** `AGENTS.md` genuinely reaches all three
harnesses. That is what the harness-neutral conventions file is for, and it is
why project rules go there rather than in `CLAUDE.md`. Everything marked as a
gap in the diagram is either unproven or missing.

Three things to notice.

- **The two-hop chain is enforced.** `.claude/skills/` holds symlinks and no
  real files; `.agents/skills/` holds our `aes-*` skills as real directories
  plus one symlink per borrowed skill into `vendor/`. The `skill-mirror`
  pre-commit gate refuses any commit that breaks that shape. See
  [`skill-overrides.md`](skill-overrides.md). On Windows the installer tries a
  symlink, then a junction, then a copy, and says which one it used; a copy
  gives up the one-copy guarantee, so the gate matters most there.
- **`.agents/` is a name, not a wiring.** Nothing in this repo establishes that
  Codex or Cursor read `.agents/skills/`. The directory is where the `npx
  skills` installer puts things; that other harnesses pick it up from there
  is an assumption nobody has tested.
- **Our own skills are the ones missing Codex metadata.** Every vendored skill
  ships an `agents/openai.yaml` carrying a display name and short description.
  None of ours do, including `aes-implement`, which holds the whole board
  lifecycle and is the skill a Codex engineer would most need to find.

## What this page is not

It is not a claim that Codex and Cursor are broken here. Nobody has run either
against this repo's skills. The gap-colored boxes mark what is untested and what
is absent, which is a different statement from "it fails".

The work to close the gap is not done. This page exists so the next person does
not have to rediscover the shape first.
