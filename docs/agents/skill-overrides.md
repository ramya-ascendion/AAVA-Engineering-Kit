# Vendored skills: the rule, the overrides, the update recipe

This kit borrows 23 skills from `mattpocock/skills` (MIT). They live under
`vendor/mattpocock-skills/`, pristine. This file is what keeps them pristine:
the rule, the list of everything we changed about how they run, and the recipe
for pulling upstream updates. Walk this file on every update.


## Link layout or copy layout

`KIT_SKILL_LAYOUT` in `.kit/config.env` picks how a skill reaches `.claude/skills/`
and, for a borrowed skill, `.agents/skills/`. Everything below is written for the
`link` layout. In the `copy` layout, which is the default, read each "symlink"
below as "a byte-identical copy made by `bin/sync-skills`":

- The pristine tree under `vendor/` is still never edited.
- After any change to `vendor/` or to one of our skills, run `bin/sync-skills`.
  The update recipe's "restore the symlink" step becomes that one command.
- The `skill-mirror` gate refuses a copy that differs from its source, so a
  hand edit to a copy is caught at the next commit.
- A wrapped skill is removed from `.agents/skills/` and `.claude/skills/` by
  deleting both directories, then running `bin/sync-skills`.

## The rule

**Never edit a vendored file.** A local edit is a fork: the next update either
overwrites it silently or conflicts on it forever. Every locally edited vendored
file is a standing merge conflict, and most such edits turn out to be spelling
fixes that were never worth it.

When the project needs a vendored skill to behave differently, there are two
moves, in order of preference:

1. **Config.** Most of these skills read per-repo config by design. They say
   "the issue tracker should have been provided to you" and read
   `docs/agents/*.md`. Write the rule there. This is almost always enough.
2. **Wrap.** Only when the skill reaches no config at all and upstream is
   silent on something the project requires. The wrapper is our own skill, named
   with the project's skill prefix (`KIT_SKILL_PREFIX` in `.kit/config.env`,
   `aes` by default), and the wrapped skill's symlink is removed from
   `.agents/skills/` and `.claude/skills/` so its bare name cannot be run by
   accident.

A wrapper is always the same shape: "read the vendored skill under
`vendor/mattpocock-skills/` first, then apply these corrections, which win
wherever the two disagree."

## Layout

- `vendor/mattpocock-skills/`: pristine upstream copies plus upstream's MIT
  `LICENSE`. The only thing that writes here is the update recipe below.
- `.agents/skills/`: our own `aes-*` skills as real directories (they live in
  `.agents/skills/` in the kit and are installed here), plus one symlink into
  `vendor/` per unwrapped upstream skill. Non-Claude harnesses read this
  directory.
- `.claude/skills/`: symlinks into `.agents/skills/`, for Claude Code.
- `skills-lock.json` (repo root): the `npx skills` installer's file. We do
  not edit it, with one exception the update recipe names (an entry for a
  skill upstream deleted). It moves only if a future dry run shows the
  installer accepts a new location.

### Companion files

A skill we wrote may put a step in its own file beside its `SKILL.md`, so that
a run which skips the step never loads it. `aes-work-the-path` is the worked
example. Two rules, both decided by the `skill-mirror` gate:

- **Every companion is named from its `SKILL.md`, in backticks.** A file nothing
  points at is a file no run reaches, and a shorter name contained in a longer
  one is not a pointer. The split is only worth its pointer if the pointer is
  there.
- **A companion carries no YAML frontmatter.** Only a `SKILL.md` gets `name:`
  and `description:`, because those are what a harness lists a skill by, and a
  second file carrying them is a second skill the harness may try to run.

A companion only pays when the step is conditional. Splitting a step every run
reaches makes the common path cost more, not less: it adds a header and a
pointer and saves nothing. `tools/document_types.yaml` holds the type.

## Current overrides

### Shipped with the kit

These wrappers and readers ship with the kit, and each is generic to any project
that runs the kit's ticket lifecycle.

| Upstream skill | What the kit changes | Where it lives | How it reaches |
| --- | --- | --- | --- |
| `implement` | The whole board lifecycle: model check, claim, plan approval, acceptance-criteria gate, ask before the PR, `In Review` + label swap once it is open | Wrapper `aes-implement`; rules in `docs/agents/ticket-states.md`. Bare name unregistered. | Wrapper: `aes-implement` names the file |
| `implement-spec` | One Epic, in parallel: one branch and one pull request per ticket, a fix-version ceiling, stacked branches inside the run, and the same plan and pull-request stops as `aes-implement` | Wrapper `aes-implement-spec`. Bare name unregistered. | Wrapper: `aes-implement-spec` names the file |
| `ask-matt` | Routes to `aes-implement` and `aes-implement-spec`, since the bare names it uses are unregistered here; the tracker is whatever `KIT_TRACKER` says, not `.scratch/` by default; `pr` and `retro` are routed but not installed | Wrapper `aes-ask`. Bare name unregistered. | Wrapper: `aes-ask` names the file |
| `writing-for-agents` | American spelling over the vendored file's British; a leading word still gets defined once, plainly; hard guardrails stay prohibitions; short sentences over dense ones | Wrapper `aes-writing-for-agents`. Bare name unregistered. | Wrapper: `aes-writing-for-agents` names the file |
| `grilling` | One question per round instead of the whole frontier; question under 3 lines; one-line recommendation and runner-up; facts in a table; a scope check every round; findings recorded on the ticket | Wrapper `aes-grilling`. Bare name unregistered. | Wrapper: `aes-grilling` names the file |
| `wayfinder` | Its three calls to bare `grilling` become `aes-grilling` | Wrapper `aes-wayfinder`. Bare name unregistered. | Wrapper: `aes-wayfinder` names the file |
| `grill-with-docs` | Its one call to bare `grilling` becomes `aes-grilling` | Wrapper `aes-grill-with-docs`. Bare name unregistered. | Wrapper: `aes-grill-with-docs` names the file |
| `triage` | Turn labels are one axis, labels answering other questions sit alongside; its one call to bare `grilling` becomes `aes-grilling` | Wrapper `aes-triage`; label mapping in `docs/agents/triage-labels.md`, "Labels on other axes". Bare name unregistered. | Wrapper: `aes-triage` names the file |
| `improve-codebase-architecture` | Its one call to bare `grilling` becomes `aes-grilling` | Wrapper `aes-improve-codebase-architecture`. Bare name unregistered. | Wrapper: `aes-improve-codebase-architecture` names the file |
| `grill-me` | Its one call to bare `grilling` becomes `aes-grilling` | Wrapper `aes-grill-me`. Bare name unregistered. | Wrapper: `aes-grill-me` names the file |
| `code-review` | Runs twice per ticket: once inside `aes-implement`, once by the reviewer against the PR. That second run fixes on the branch the PR merges into, and reads the diff without the first run's report | `docs/agents/ticket-states.md`, "The flow", step 6 | **Reader only** |
| `to-tickets` | New tickets get a link pass against existing board work before they are reported | `docs/agents/ticket-links.md`, "The link pass, at creation" | **Reader only** |
| `to-tickets` | A second model reviews the drafted breakdown until it gives a thumbs-up, before the user is asked to approve it | Skill `aes-second-opinion-to-tickets` | **Skill description**: the agent running `/to-tickets` sees it in the skill list |
| `domain-modeling` | Extra ADR rules: `amended-by` frontmatter, writing style, restyling limits | `docs/agents/adr-format.md`, pointed at from `docs/agents/domain.md` | **Reader only** |

### Your project's rows

Empty until the project overrides something. Copy the shape of a row above.

| Upstream skill | What the project changes | Where it lives | How it reaches |
| --- | --- | --- | --- |
| | | | |

**To add a row:** first try config (move 1 above). Only if the skill reaches no
config, write the wrapper skill under `.agents/skills/`, make its `name:` equal its
directory, point it at the vendored file with "read it first, then these
corrections win", remove the bare skill's symlink from `.agents/skills/` and
`.claude/skills/`, add the bare name to the update recipe's step 3 list, and add
the row here. "How it reaches" is one of: **Wrapper** (the wrapper names the
file), **Skill description** (the agent sees it in the skill list), or
**Reader only** (see below).

Several rows share one call site: bare `grilling`'s round format asked the whole
frontier at once, and let a real seam ticket drift into several decisions nobody
asked for. `wayfinder`, `grill-with-docs`, `triage`, `improve-codebase-architecture`,
and `grill-me` all named it by string, so unregistering it meant wrapping all of
them, not just the ones that had a documented reason.

Config the skills were designed to take (issue tracker choice, triage label
strings, domain doc layout) is not an override and is not listed here. That
is `docs/agents/issue-tracker.md`, `triage-labels.md`, and `domain.md` doing
their job. Note that "designed to take" is not the same as "goes and reads":
see the note below on how far a row actually reaches.

**Some rows do not reach their skill, and that is on purpose.** "Reader only"
means the vendored skill never opens the file that row names. `to-tickets`
and `domain-modeling` name no `docs/agents/` path at all. `code-review` names
`docs/agents/issue-tracker.md` twice (once to check the file exists, once to
fetch the issue under review) and never to look up how to run itself.

Vendored `code-review` expects its config to arrive some other way and says
so: it tells the agent the mapping "should have been provided to you" and to
run `/setup-matt-pocock-skills` if it was not. That is a check on context,
not a file read. Whether the right file is in context is not something the
skill can tell.

So these rules land with the person running the skill, not with the
skill. That is the right place for them: each is written where a human is
already reading at the moment they need it. Step 6 for the reviewer flow,
the link pass at ticket creation, the ADR rules while writing an ADR.

But do not read a "reader only" row as config an agent picks up on its own.
An agent handed `/code-review` with no fixed point will ask for one, exactly
as the vendored step 1 says. `triage` had this same gap (an agent running it
had no way to know the label axes unless told), which is why it is a wrapper
instead of a reader-only row: `aes-triage` tells the agent directly.

## Pinned upstream version

**`4588b32e`, captured 2026-10-06.** That is `mattpocock/skills` HEAD at the
moment the kit's vendored tree was captured. The next update diffs against it,
and captures a fresh one the same way:

```
git ls-remote https://github.com/mattpocock/skills HEAD
```

The kit vendors 23 of the skills upstream listed that day. Upstream's 1.3.0
release deleted `resolving-merge-conflicts` with nothing in its place, and
graduated `implement-spec`, `pr` and `retro`: `implement-spec` is vendored and
wrapped, while `pr` and `retro` stay opt-in under step 8 below. The overrides
table above was walked against this ref. The glossary file is `GLOSSARY.md`, the
name those skills already use, so the rename is not an override.

`skills-lock.json` records no ref of its own. It names the source repo and a
per-skill hash, and those hashes are not a plain sha256 of the files, so they
cannot be checked by hand either. The ref above is the only one we have.

To prove the vendored tree is pristine, diff the working tree against `HEAD`:
`git diff HEAD -- vendor/` on a clean checkout must be empty.

## The update recipe

The installer does not know about `vendor/`. Measured with `npx skills update
-p -y` (the `skills` CLI via npx): it treats `.agents/skills/` as its store,
**replaces each symlink there with a real directory** of fresh upstream files,
**recreates skills we deliberately unregistered** (untracked, which the
index-reading `skill-mirror` gate cannot see; check both skills directories),
and rewrites the hashes in `skills-lock.json`.

**A skill upstream has deleted is the one thing it cannot handle.** It prints
"Failed to update" for it, leaves the old files and the old lock entry in
place, and `npx skills remove <name>` does not see it either, because the
installer only counts skills it found as real directories.

So the recipe is: let it write, then put everything back where it lives.

1. Run `npx skills update -p -y`. Each vendored skill's symlink in
   `.agents/skills/` is now a real directory of new upstream files.
2. For each one: remove the directory it left, move the new files into
   `vendor/mattpocock-skills/<name>/`, and restore the symlink
   `../../vendor/mattpocock-skills/<name>`.
3. Delete anything it resurrected that we keep unregistered, currently
   `implement`, `implement-spec`, `ask-matt`, `writing-for-agents`,
   `grilling`, `wayfinder`, `grill-with-docs`, `triage`,
   `improve-codebase-architecture`, and `grill-me` in both skills
   directories, plus any bare name your project's rows add.
4. Keep the rewritten `skills-lock.json`; it is the installer's own record of
   what it fetched.
5. Read the diff of the vendor tree. Read what changed. A skill the installer
   reported as "Failed to update" has usually been deleted upstream; confirm
   with the upstream history on a clone. Then remove its `vendor/` directory and
   both symlinks, and remove its entry from `skills-lock.json` by hand. That is
   the only edit this file ever asks for in `skills-lock.json`, and only because
   the installer leaves no other way. Keeping the copy is not an option: a skill
   with no upstream can never be updated, so it is a fork from the day it is
   orphaned.
6. Walk the overrides tables above. For each row, re-read the new upstream text
   and ask: does the override still make sense? Did upstream adopt it, making
   it redundant? Did upstream change in a way that breaks the wrapper's
   assumptions?
7. **Record the upstream ref**, so the next update can diff against it rather
   than guess. `npx skills` does not write one, so capture it by hand at update
   time with `git ls-remote https://github.com/mattpocock/skills HEAD` and
   replace the "Pinned upstream version" section above with that SHA and the
   date. Then update the tables if anything moved.
8. New upstream skills are opt-in: add a symlink in `.agents/skills/` only
   when we decide to adopt one. Adopting through the installer takes the same
   let-it-write-then-relocate shape as above:
   `npx skills add mattpocock/skills -s <name> -a '*' -y`, then move the new
   directory into `vendor/` and symlink it back. **`-a '*'` means every harness
   the installer knows, not ours**, so it also drops a stray
   `agent/skills/<name>` at the repo root. Delete it: a third copy is the
   thing the layout exists to prevent. The narrower flag has not been measured;
   `-a '*'` at least writes the two directories we want.

The `skill-mirror` pre-commit gate checks the committed shape at every step,
so a half-done update cannot land quietly.
